# 前処理設計書

## 概要

本ドキュメントでは、toto GOAL3 Predictor における機械学習モデル用データの前処理方針を記載します。データの品質を保証し、データリークを防止するための仕組みを定義します。

## 1. データリーク防止

### 1.1 基本原則

**予測時点で利用できない情報を学習・予測に使用しない**

機械学習モデルで予測を行う際、予測時点（試合前）では知り得ない情報が学習データに混入すると、モデルが実運用時に使えなくなります。これを「データリーク」と呼びます。

### 1.2 リーク防止の実装

#### 1.2.1 `before_date` パラメータによる試合当日除外

特徴量計算時に `before_date` パラメータを使用し、基準日以前のデータのみを使用します。

```python
# feature_engine.py での実装
stats_list = self.stats_repo.find_by_team(
    team,
    limit=max(window_sizes),
    before_date=as_of_date  # この日付以前のデータのみ取得
)
```

データベースクエリ（`team_stats_repository.py`）では以下のように実装:

```sql
SELECT * FROM team_stats ts
JOIN matches m ON ts.match_id = m.id
WHERE ts.team = ?
AND m.date < ?  -- 指定日より前の試合のみ
ORDER BY m.date DESC
LIMIT ?
```

#### 1.2.2 学習データ準備時の適用

`prepare_training_data()` では、各試合について **試合日を基準日** として特徴量を計算:

```python
features = self.calculate_features(
    team,
    as_of_date=match.date,  # 試合日を指定
    window_sizes=[5, 10, 20],
)
```

これにより:
- 2025年12月1日の試合の特徴量は、2025年11月30日以前のデータで計算
- 当該試合の結果（得点、スタッツ）は特徴量計算に含まれない

### 1.3 リーク防止チェックリスト

- [x] 特徴量計算で `before_date` を使用
- [x] 試合結果（得点）を特徴量に含めない
- [x] 試合後の評価指標（MoM、レーティング等）を使用しない
- [x] 未来の対戦相手情報を使用しない

## 2. 欠損値処理

### 2.1 欠損値の発生パターン

| 発生パターン | 原因 | 対処方針 |
|------------|------|---------|
| 新チーム | データ不足（昇格チーム等） | 最小試合数チェックで除外 |
| 統計項目欠損 | Wyscoutデータの欠損 | 0で補完 + 警告ログ |
| 計算不能 | 分母ゼロ（例: シュート0本） | 0で補完 |

### 2.2 処理方針

#### 2.2.1 最小試合数チェック

```python
# feature_engine.py
MIN_MATCHES = 5  # 特徴量計算に必要な最小試合数

if len(stats_list) < self.MIN_MATCHES:
    raise DataNotFoundError(
        f"チーム {team} の試合データが不足しています "
        f"（必要: {self.MIN_MATCHES}試合、現在: {len(stats_list)}試合）"
    )
```

#### 2.2.2 数値欠損の補完

統計値が欠損している場合は0で補完し、警告ログを出力:

```python
# 補完処理の方針
# - 平均値補完は使用しない（リーク防止のため）
# - 中央値補完は使用しない（同上）
# - 0補完を採用（保守的な推定）

if pd.isna(value):
    logger.warning(f"欠損値を検出: {column_name} for {team}")
    value = 0.0
```

#### 2.2.3 比率計算時のゼロガード

分母がゼロになる可能性がある計算では、ゼロガードを実施:

```python
# シュート決定率
if features.shots_mean > 0:
    features.shot_conversion = features.goals_mean / features.shots_mean
else:
    features.shot_conversion = 0.0
```

### 2.3 欠損値の監視

学習データ準備時に欠損値の状況をログ出力:

```python
logger.info(f"学習データ: {len(features_df)}サンプル, 欠損率: {missing_rate:.2%}")
```

## 3. 外れ値処理

### 3.1 外れ値の定義

サッカー統計において、以下を外れ値の目安とします:

| 統計項目 | 正常範囲 | 外れ値閾値 |
|---------|---------|----------|
| 1試合得点 | 0-5 | 6以上 |
| xG | 0.0-4.0 | 5.0以上 |
| ボール支配率 | 25%-75% | 20%未満 or 80%超 |
| シュート数 | 0-25 | 30以上 |
| PPDA | 5.0-15.0 | 20.0以上 |

### 3.2 処理方針

#### 3.2.1 学習時の処理

外れ値は **クリッピングなし** で学習に使用:

- 理由1: 実際のサッカー試合では大量得点が発生する
- 理由2: toto GOAL3 は「3点以上」カテゴリがあり、大量得点の予測が重要
- 理由3: 外れ値のクリッピングは情報損失につながる

#### 3.2.2 予測時の処理

外れ値的な入力があった場合は **ログ出力のみ** :

```python
if features.goals_mean > 3.0:
    logger.warning(f"高得点傾向を検出: {team} (平均{features.goals_mean:.2f}点)")
```

### 3.3 今後の検討事項

1. **ロバスト推定**: 外れ値に強い統計量（中央値、トリム平均）の導入検討
2. **Winsorization**: 極端な値を閾値でクリップする手法の検討
3. **外れ値フラグ**: 外れ値の存在を特徴量として利用する検討

## 4. データバリデーション

### 4.1 入力データの検証

`TeamStats` モデルで以下のバリデーションを実施:

```python
@dataclass
class TeamStats:
    def __post_init__(self):
        if self.shots_on_target > self.shots:
            raise ValidationError("枠内シュート数がシュート数を超えています")
        if not (0 <= self.possession <= 100):
            raise ValidationError("ボール支配率は0-100の範囲である必要があります")
        if self.ppda <= 0:
            raise ValidationError("PPDAは正の値である必要があります")
```

### 4.2 特徴量の検証

計算された特徴量に対する検証:

| 特徴量 | 検証ルール |
|-------|----------|
| goals_mean | >= 0 |
| shots_mean | >= 0 |
| possession_mean | 0-100 |
| shot_conversion | 0-1 |

## 5. 変更履歴

| 日付 | 内容 |
|-----|------|
| 2026-02-06 | 初版作成 |
