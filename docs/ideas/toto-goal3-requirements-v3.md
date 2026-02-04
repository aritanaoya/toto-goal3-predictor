# toto Goal 3 購入戦略システム 要件定義書 v3（プロ仕様）

## 1. 概要

Wyscoutの高度な統計データと機械学習を活用し、各チームの得点分布を予測。公衆投票率とのギャップからバリューベットを自動選択する。

---

## 2. データソース

### 2.1 Wyscoutデータ（確認済み）

**サンプル: 横浜F.マリノス** - 94試合分、109カラム

| カテゴリ | 主要指標 | 説明 |
|---------|---------|------|
| **得点力** | `xG` | 期待得点（最重要） |
| | `Goals` | 実得点 |
| | `Shots on target` | 枠内シュート数 |
| | `Penalty area entries` | PA侵入回数 |
| | `Touches in penalty area` | PA内タッチ数 |
| **チャンス創出** | `Positional attacks with shots` | ポゼッション攻撃→シュート |
| | `Counterattacks with shots` | カウンター→シュート |
| | `Set pieces with shots` | セットプレー→シュート |
| | `Deep completed passes` | 深い位置へのパス成功 |
| | `Crosses accurate` | クロス成功数 |
| **守備力** | `Conceded goals` | 失点 |
| | `Shots against on target` | 被枠内シュート |
| | `PPDA` | プレス強度（低い=ハイプレス） |
| | `Defensive duels won %` | 守備デュエル勝率 |
| | `Interceptions` | インターセプト数 |
| **試合支配** | `Possession %` | ボール支配率 |
| | `Match tempo` | 試合テンポ |
| | `Passes accurate %` | パス成功率 |

### 2.2 投票率データ（確認済み）

| ソース | URL | 形式 | 取得可否 |
|--------|-----|------|---------|
| **totoONE** | https://www.totoone.jp/prediction | HTML（購入割合%） | ✅ 確認済み |
| 楽天toto | https://toto.rakuten.co.jp/toto/schedule/ | 試合情報のみ | ⚠️ 投票率なし |

**totoONEデータ例（第1607回）:**
```
横浜FM: 0点=22%, 1点=35%, 2点=25%, 3+=16%
町田:   0点=25%, 1点=37%, 2点=25%, 3+=12%
京都:   0点=22%, 1点=38%, 2点=26%, 3+=11%
```

---

## 3. 予測モデル（機械学習）

### 3.1 アーキテクチャ

```
[Wyscout Raw Data]
       ↓
[Feature Engineering] → 50+ features
       ↓
[Model Ensemble]
   ├── Poisson Regression (λ予測)
   ├── XGBoost (得点分布予測)
   └── Neural Network (オプション)
       ↓
[Calibration Layer]
       ↓
[P(0), P(1), P(2), P(3+)] per team
```

### 3.2 特徴量エンジニアリング

#### 基本統計（直近N試合の平均・分散）

```python
# N = 5, 10, 20 試合のウィンドウ
basic_features = [
    # 攻撃
    'xG_mean', 'xG_std', 'xG_trend',  # トレンド = 直近5試合 - 直近20試合
    'goals_mean', 'goals_std',
    'shots_on_target_mean',
    'pen_area_entries_mean',

    # 守備
    'xGA_mean', 'xGA_std',  # 相手のxG = 自分の被xG
    'conceded_mean',
    'ppda_mean',

    # 支配
    'possession_mean',
    'pass_accuracy_mean',
]
```

#### 高度な派生特徴量

```python
advanced_features = [
    # 効率性
    'shot_conversion': goals / shots,
    'xG_overperformance': goals - xG,  # 決定力
    'chance_creation_rate': (pos_attacks_shots + counter_shots) / possession,

    # スタイル指標
    'counter_ratio': counter_shots / total_shots,  # カウンター依存度
    'set_piece_ratio': set_piece_shots / total_shots,
    'crossing_tendency': crosses / attacks,

    # 守備スタイル
    'press_intensity': 1 / ppda,  # PPDA逆数
    'defensive_solidity': 1 - (conceded / xGA),  # 守備効率

    # 対戦相手調整
    'opponent_xGA_mean',  # 相手の被xG（相手守備力）
    'opponent_ppda_mean',  # 相手のプレス強度
    'style_matchup': own_counter_ratio * opponent_high_line,  # スタイル相性
]
```

#### コンテキスト特徴量

```python
context_features = [
    'is_home': 1 or 0,
    'days_since_last_match',
    'match_importance',  # リーグ順位差、残り試合数等
    'h2h_goal_avg',  # 過去対戦の平均得点
]
```

### 3.3 モデル構成

#### Model 1: Poisson Regression（ベースライン）

```python
from sklearn.linear_model import PoissonRegressor

# λを直接予測
poisson_model = PoissonRegressor(alpha=0.1)
poisson_model.fit(X_train, y_goals)

lambda_pred = poisson_model.predict(X_test)
```

#### Model 2: XGBoost（メイン）

```python
import xgboost as xgb

# 得点数を直接予測（0, 1, 2, 3, 4, 5+）
xgb_model = xgb.XGBClassifier(
    objective='multi:softprob',
    num_class=6,
    max_depth=6,
    learning_rate=0.05,
    n_estimators=500,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=0.1,
    reg_lambda=1.0,
)

# 確率分布を出力
probs = xgb_model.predict_proba(X_test)  # shape: (n_samples, 6)

# totoカテゴリに変換
p_0 = probs[:, 0]
p_1 = probs[:, 1]
p_2 = probs[:, 2]
p_3plus = probs[:, 3:].sum(axis=1)
```

#### Model 3: Ensemble

```python
# 重み付きアンサンブル
ensemble_weights = {
    'poisson': 0.3,
    'xgboost': 0.5,
    'neural_net': 0.2,  # オプション
}

final_probs = (
    w_poisson * poisson_probs +
    w_xgboost * xgboost_probs +
    w_nn * nn_probs
)
```

### 3.4 キャリブレーション

```python
from sklearn.calibration import CalibratedClassifierCV

# Platt Scaling or Isotonic Regression
calibrated_model = CalibratedClassifierCV(
    base_estimator=xgb_model,
    method='isotonic',
    cv=5
)

# 予測確率が実際の発生確率と一致するよう調整
```

### 3.5 学習データ

| 項目 | 仕様 |
|------|------|
| 期間 | 過去3シーズン（J1リーグ） |
| サンプル数 | 約1,000試合 × 2チーム = 2,000サンプル |
| 検証方法 | 時系列CV（未来漏洩防止） |
| 更新頻度 | 週次（各節終了後） |

---

## 4. 戦略エンジン

### 4.1 バリュースコア計算

```python
def calculate_value(model_prob, public_vote_rate, min_rate=0.01):
    """
    バリュースコア = モデル確率 / 公衆投票率
    """
    return model_prob / max(public_vote_rate, min_rate)

# 例
model = {'0': 0.18, '1': 0.32, '2': 0.28, '3+': 0.22}
public = {'0': 0.22, '1': 0.35, '2': 0.25, '3+': 0.16}

value_scores = {
    '0': 0.18 / 0.22,  # 0.82 → やや過大評価
    '1': 0.32 / 0.35,  # 0.91 → フェア
    '2': 0.28 / 0.25,  # 1.12 → 軽度バリュー
    '3+': 0.22 / 0.16, # 1.38 → バリュー発見！
}
```

### 4.2 購入判断マトリクス

| モデル確率 | バリュー≥1.5 | バリュー1.0-1.5 | バリュー<1.0 |
|-----------|-------------|----------------|-------------|
| ≥30% | **必買** | 買い | 慎重 |
| 15-30% | 買い | 検討 | スキップ |
| <15% | 検討 | スキップ | スキップ |

### 4.3 Kelly Criterion（資金管理）

```python
def kelly_fraction(p_win, odds, fraction=0.25):
    """
    ケリー基準でベットサイズを計算
    fraction: フルケリーは危険なので1/4ケリーを推奨
    """
    # totoはパリミュチュエルなのでオッズ推定が必要
    estimated_odds = 1 / public_vote_rate  # 簡易推定

    edge = p_win * estimated_odds - 1
    if edge <= 0:
        return 0

    kelly = edge / (estimated_odds - 1)
    return kelly * fraction
```

---

## 5. 投票率スクレイピング

### 5.1 totoONE スクレイパー

```python
import requests
from bs4 import BeautifulSoup
import re

def scrape_totoone_votes(round_number: int = None) -> dict:
    """
    totoONEから投票率を取得
    """
    url = "https://www.totoone.jp/prediction"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    # GOAL3セクションを探す
    # 購入割合の数値を抽出
    # 例: "22% | 35% | 25% | 16%"

    votes = {}
    # パース処理...

    return votes

# 出力形式
{
    'round': 1607,
    'teams': [
        {'name': '横浜FM', 'votes': {0: 0.22, 1: 0.35, 2: 0.25, 3: 0.16}},
        {'name': '町田', 'votes': {0: 0.25, 1: 0.37, 2: 0.25, 3: 0.12}},
        # ...
    ]
}
```

---

## 6. パイプライン全体

```
┌─────────────────────────────────────────────────────────────┐
│                    Weekly Pipeline                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [1] Data Collection (自動)                                 │
│      ├── Wyscout API → 直近試合データ取得                   │
│      └── 特徴量DB更新                                       │
│                                                             │
│  [2] Model Update (週次)                                    │
│      ├── 新データで再学習                                   │
│      └── バックテスト実行                                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                    Match Day Pipeline                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [3] Prediction (試合2日前)                                 │
│      ├── 対象6チームの特徴量抽出                            │
│      ├── モデル推論 → 得点分布予測                          │
│      └── 予測結果保存                                       │
│                                                             │
│  [4] Voting Rate Fetch (締切6-24時間前)                     │
│      └── totoONEスクレイピング                              │
│                                                             │
│  [5] Strategy Execution (締切前)                            │
│      ├── バリュースコア計算                                 │
│      ├── 購入チケット生成                                   │
│      └── 購入推奨出力                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. 評価指標

### 7.1 モデル精度

| 指標 | 説明 | 目標 |
|------|------|------|
| **Brier Score** | 確率予測の精度 | < 0.20 |
| **Log Loss** | 確率分布の品質 | < 1.2 |
| **カテゴリ的中率** | 最頻カテゴリの的中 | > 40% |
| **キャリブレーション** | 予測確率と実績の一致 | ±5%以内 |

### 7.2 戦略パフォーマンス

| 指標 | 説明 | 目標 |
|------|------|------|
| **ROI** | (払戻 - 投資) / 投資 | > 0% (長期) |
| **的中率** | 1等的中 / 購入回数 | > 1/500 |
| **シャープレシオ** | リターン / リスク | > 0.5 |

---

## 8. 実装ロードマップ

| Phase | 内容 | 期間 |
|-------|------|------|
| **P1** | データパイプライン構築（Wyscout読み込み、特徴量生成） | 1週間 |
| **P2** | ベースラインモデル（Poisson + XGBoost） | 1週間 |
| **P3** | 投票率スクレイパー + バリュー計算 | 3日 |
| **P4** | バックテスト環境構築 | 3日 |
| **P5** | 本番運用 + モニタリング | 継続 |

---

## 9. リスクと対策

| リスク | 対策 |
|--------|------|
| Wyscout APIアクセス制限 | ローカルDBにキャッシュ |
| totoONE構造変更 | 複数ソース対応、アラート設定 |
| モデルドリフト | 週次再学習、パフォーマンス監視 |
| 過学習 | 時系列CV、正則化強化 |

---

## Sources

- 投票率: [totoONE](https://www.totoone.jp/prediction) ✅確認済み
- 試合情報: [楽天toto](https://toto.rakuten.co.jp/toto/schedule/)
