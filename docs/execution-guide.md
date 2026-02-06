# 実行手順書 (Execution Guide)

## 概要

本ドキュメントでは、toto GOAL3 Predictor の週次運用フローについて説明します。

### 運用フロー全体像

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        週次運用フロー                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ① データ準備        ② モデル学習        ③ 週次予測                    │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐     │
│  │ Wyscout     │    │ train       │    │ import → predict →     │     │
│  │ Excel取得   │ → │ コマンド    │ → │ scrape → strategy      │     │
│  └─────────────┘    └─────────────┘    └─────────────────────────┘     │
│        ↓                  ↓                       ↓                    │
│  data/wyscout/      models/*.joblib      reports/round_XXXX.md         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. 事前準備（初回のみ）

### 1.1 環境構築

```bash
# リポジトリのクローン
git clone https://github.com/[user]/toto-goal3-predictor.git
cd toto-goal3-predictor

# 仮想環境の作成・有効化
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係のインストール
pip install -e ".[dev]"

# 動作確認
toto-predictor --help
```

### 1.2 ディレクトリ構成の確認

```bash
# 必要なディレクトリが存在することを確認
ls -la data/wyscout/
ls -la data/processed/
ls -la models/
ls -la reports/
```

---

## 2. データ準備

### 2.1 Wyscoutデータの取得

1. Wyscout Platform にログイン
2. 対象リーグ（J1 League）のチーム統計をダウンロード
3. ダウンロードした Excel ファイルを `data/wyscout/{シーズン年}/` に配置

```
data/wyscout/
├── 2024/
│   ├── Team Stats Yokohama F. Marinos.xlsx
│   ├── Team Stats Kawasaki Frontale.xlsx
│   └── ...
└── 2025/
    ├── Team Stats Yokohama F. Marinos.xlsx
    ├── Team Stats Kawasaki Frontale.xlsx
    └── ...
```

### 2.2 データインポート

```bash
# シーズン単位でインポート
toto-predictor import --dir data/wyscout/2024 --season 2024
toto-predictor import --dir data/wyscout/2025 --season 2025
```

**出力例**:
```
データインポート開始...
├── Team Stats Yokohama F. Marinos.xlsx ... ✓ 38試合
├── Team Stats Kawasaki Frontale.xlsx ... ✓ 38試合
└── 完了

インポート結果
================================================================================
対象ファイル数:     20
成功:              20
取り込み試合数:    380
```

---

## 3. モデル学習（初回または再学習時）

### 3.1 モデルの学習

十分なデータがインポートされた後、モデルを学習します。

```bash
# 5-fold クロスバリデーションで学習
toto-predictor train --cv 5
```

**出力例**:
```
モデル学習開始...

[1/3] Poisson Regression
      学習中... ━━━━━━━━━━━━━━━━━━━━ 100%
      CV Brier Score: 0.187 (±0.012)

[2/3] XGBoost Classifier
      学習中... ━━━━━━━━━━━━━━━━━━━━ 100%
      CV Brier Score: 0.172 (±0.015)

[3/3] Ensemble + Calibration
      キャリブレーション中... ━━━━━━━━━━━━━━━━━━━━ 100%
      CV Brier Score: 0.168 (±0.011)

================================================================================
学習結果
================================================================================
最終モデル:         Ensemble (Poisson 30% + XGBoost 70%)
Brier Score:       0.168 ✓ (目標: < 0.20)
保存先:            models/
```

### 3.2 学習済みモデルの確認

```bash
ls -la models/
# poisson_model.joblib
# xgb_model.joblib
# calibrator.joblib
# metadata.json
```

---

## 4. 週次運用手順

毎週の toto GOAL3 購入戦略を生成する手順です。

### 4.1 最新データのインポート

直近の試合データがある場合は先にインポートします。

```bash
toto-predictor import --dir data/wyscout/2025 --season 2025
```

### 4.2 パイプライン一括実行（推奨）

すべての処理を一括で実行する場合:

```bash
# 回号を指定してパイプライン実行
toto-predictor pipeline --round 1607
```

**処理内容**:
1. 対象チームの特徴量計算
2. モデルによる得点分布予測
3. totoONE から投票率取得
4. バリュースコア計算・購入推奨生成
5. レポート出力

### 4.3 個別コマンド実行（詳細制御が必要な場合）

各ステップを個別に実行することも可能です。

```bash
# ① 予測実行
toto-predictor predict --round 1607

# ② 投票率取得
toto-predictor scrape --round 1607

# ③ 戦略計算・レポート生成
toto-predictor strategy --round 1607
```

---

## 5. 出力結果の確認

### 5.1 レポートファイル

購入推奨レポートは `reports/` ディレクトリに出力されます。

```bash
cat reports/round_1607_strategy.md
```

### 5.2 レポート内容

```
第1607回 GOAL3 購入戦略
================================================================================

■ 推奨購入（バリュースコア 1.3以上）

┌────────────────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│ チーム              │ カテゴリ │ モデル予測 │ 投票率    │ バリュー  │ アクション │
├────────────────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ 横浜F・マリノス     │ 3点以上  │   21.4%  │   16.0%  │   1.34   │ ★ 買い   │
│ 川崎フロンターレ     │ 2点      │   31.2%  │   24.0%  │   1.30   │ ★ 買い   │
└────────────────────┴──────────┴──────────┴──────────┴──────────┴──────────┘

■ 検討候補（バリュースコア 1.0-1.3）
...
```

### 5.3 予測データの確認

```bash
# 予測結果 JSON
cat data/predictions/round_1607.json

# 投票率データ JSON
cat data/votes/round_1607.json
```

---

## 6. 補助コマンド

### 6.1 特徴量の確認

特定チームの現在の特徴量を確認できます。

```bash
toto-predictor features --team "Yokohama F. Marinos" --window 10
```

### 6.2 データベースの確認

```bash
# データベースの状態確認
toto-predictor db status

# マイグレーション実行（スキーマ更新時）
toto-predictor db migrate
```

---

## 7. トラブルシューティング

### 7.1 よくあるエラーと対処

| エラーメッセージ | 原因 | 対処法 |
|-----------------|------|--------|
| "モデルが学習されていません" | models/ にモデルファイルがない | `toto-predictor train` を実行 |
| "データ不足でスキップ" | チームの試合データが10試合未満 | 追加データをインポート |
| "totoONEからの取得に失敗" | ネットワークエラーまたはサイト変更 | しばらく待って再試行 |
| "必須カラムが不足" | Excel形式の不一致 | Wyscoutからの再ダウンロード |

### 7.2 ログの確認

詳細なエラー情報はログファイルで確認できます。

```bash
# ログファイルの確認
cat logs/toto-predictor.log

# 直近のエラーのみ表示
grep ERROR logs/toto-predictor.log | tail -20
```

### 7.3 データベースのリセット（最終手段）

問題が解決しない場合、データベースをリセットできます。

```bash
# バックアップを取得
cp data/processed/toto_predictor.db data/processed/toto_predictor.db.backup

# データベースを削除して再作成
rm data/processed/toto_predictor.db
toto-predictor db migrate

# データを再インポート
toto-predictor import --dir data/wyscout/2024 --season 2024
toto-predictor import --dir data/wyscout/2025 --season 2025
```

---

## 8. 運用スケジュール例

### 週次運用カレンダー

| 曜日 | 作業内容 |
|------|---------|
| 月曜 | 前週の試合結果を反映した Excel を取得・インポート |
| 火曜 | 必要に応じてモデル再学習 |
| 金曜 | 週末開催分の予測・戦略レポート生成 |
| 土曜 | toto 購入締切前に投票率を再取得し最終判断 |

### 推奨運用フロー

```bash
# 月曜: データ更新
toto-predictor import --dir data/wyscout/2025 --season 2025

# 金曜: 週末開催分の予測
toto-predictor pipeline --round 1607

# 土曜（締切前）: 投票率の再取得と最終確認
toto-predictor scrape --round 1607
toto-predictor strategy --round 1607
```

---

## 9. CLI コマンドリファレンス

| コマンド | 説明 | 主なオプション |
|---------|------|---------------|
| `import` | Wyscout Excel をインポート | `--dir`, `--season` |
| `train` | モデルを学習 | `--cv` |
| `predict` | 得点分布を予測 | `--round`, `--teams` |
| `scrape` | 投票率を取得 | `--round` |
| `strategy` | 購入戦略を計算 | `--round`, `--output` |
| `pipeline` | 全処理を一括実行 | `--round` |
| `features` | 特徴量を確認 | `--team`, `--window` |
| `db migrate` | DBマイグレーション | `--version` |
| `db status` | DB状態確認 | - |
| `db backup` | DBバックアップ | - |

詳細なオプションは `toto-predictor <command> --help` で確認できます。
