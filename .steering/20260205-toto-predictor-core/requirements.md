# 要求仕様書: toto GOAL3 Predictor コア機能実装

## 概要

本作業では、docs/に定義されたプロダクト要求定義書、機能設計書、アーキテクチャ設計書に基づき、toto GOAL3 Predictorのコア機能を完全実装する。

## 実装対象

### 1. データモデル (models/)
- `exceptions.py`: カスタム例外クラス群
- `match.py`: 試合データモデル
- `team_stats.py`: チーム統計モデル
- `prediction.py`: 予測結果モデル
- `vote_rate.py`: 投票率モデル
- `recommendation.py`: 購入推奨モデル

### 2. データレイヤー (db/)
- `database.py`: SQLite接続・テーブル作成
- `repositories/match_repository.py`: 試合データリポジトリ
- `repositories/team_stats_repository.py`: チーム統計リポジトリ

### 3. サービスレイヤー (services/)
- `data_loader.py`: Excelファイル読み込み・DB保存
- `feature_engine.py`: 特徴量計算エンジン
- `model_ensemble.py`: 機械学習モデル（Poisson + XGBoost）
- `vote_scraper.py`: 投票率スクレイピング
- `strategy_engine.py`: バリュースコア計算・推奨生成

### 4. CLIレイヤー (cli/)
- `main.py`: Typerアプリエントリーポイント
- `commands/import_cmd.py`: データインポートコマンド
- `commands/train_cmd.py`: モデル学習コマンド
- `commands/predict_cmd.py`: 予測実行コマンド
- `commands/scrape_cmd.py`: 投票率取得コマンド
- `commands/strategy_cmd.py`: 戦略計算コマンド
- `commands/pipeline_cmd.py`: パイプライン全体実行コマンド

### 5. テスト (tests/)
- ユニットテスト: 各サービスのテスト
- 統合テスト: データパイプラインテスト
- フィクスチャ: サンプルExcel、モックHTML

## 技術要件

- Python 3.11+
- 型ヒント必須
- Googleスタイルdocstring
- ruff/mypyでエラーなし
- テストカバレッジ80%以上

## 参照ドキュメント

- docs/product-requirements.md
- docs/functional-design.md
- docs/architecture.md
- docs/development-guidelines.md
- docs/repository-structure.md
