# toto GOAL3 Predictor

機械学習ベースのtoto GOAL3購入戦略システム

## 概要

Wyscoutの高度なサッカー統計データと機械学習モデルを組み合わせ、各チームの得点分布を科学的に予測します。モデル予測確率と公衆投票率のギャップを分析し、期待値がプラスとなるバリューベットを自動特定します。

## インストール

```bash
# 依存関係のインストール
pip install -e ".[dev]"
```

## 使用方法

```bash
# データインポート
toto-predictor import --dir data/wyscout/2025 --season 2025

# モデル学習
toto-predictor train --seasons 2025 --cv 5

# 予測実行
toto-predictor predict --round 1607

# 投票率取得
toto-predictor scrape --round 1607

# 戦略計算
toto-predictor strategy --round 1607

# パイプライン全体実行
toto-predictor pipeline --round 1607
```

## 技術スタック

- Python 3.11+
- pandas / numpy - データ処理
- scikit-learn / XGBoost - 機械学習
- Typer - CLI
- SQLite - データストレージ

## ライセンス

MIT
