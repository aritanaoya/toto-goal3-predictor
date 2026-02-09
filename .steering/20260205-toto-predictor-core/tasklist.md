# タスクリスト: toto GOAL3 Predictor コア機能実装

## Phase 1: 基盤層

- [x] 1.1 models/__init__.py を作成
- [x] 1.2 models/exceptions.py を実装（TotoPredictorError, DataError, ModelError, ScrapingError, ValidationError）
- [x] 1.3 models/match.py を実装（Matchデータクラス、バリデーション付き）
- [x] 1.4 models/team_stats.py を実装（TeamStatsデータクラス、バリデーション付き）
- [x] 1.5 db/__init__.py を作成
- [x] 1.6 db/database.py を実装（SQLite接続管理、テーブル作成）
- [x] 1.7 db/repositories/__init__.py を作成
- [x] 1.8 db/repositories/match_repository.py を実装（CRUD操作）
- [x] 1.9 db/repositories/team_stats_repository.py を実装（CRUD操作）

## Phase 2: サービス層（データ処理）

- [x] 2.1 services/__init__.py を作成
- [x] 2.2 services/data_loader.py を実装（Excel読み込み、DB保存）
- [x] 2.3 models/team_features.py を実装（TeamFeaturesデータクラス）
- [x] 2.4 services/feature_engine.py を実装（特徴量計算）

## Phase 3: サービス層（予測・戦略）

- [x] 3.1 models/prediction.py を実装（Predictionデータクラス）
- [x] 3.2 models/vote_rate.py を実装（VoteRateデータクラス）
- [x] 3.3 models/recommendation.py を実装（Recommendationデータクラス）
- [x] 3.4 services/model_ensemble.py を実装（Poisson + XGBoost）
- [x] 3.5 services/vote_scraper.py を実装（totoONEスクレイピング）
- [x] 3.6 services/strategy_engine.py を実装（バリュースコア計算、レポート生成）

## Phase 4: CLI層

- [x] 4.1 cli/__init__.py を作成
- [x] 4.2 cli/main.py を実装（Typerアプリエントリーポイント）
- [x] 4.3 cli/commands/__init__.py を作成
- [x] 4.4 cli/commands/import_cmd.py を実装
- [x] 4.5 cli/commands/train_cmd.py を実装
- [x] 4.6 cli/commands/predict_cmd.py を実装
- [x] 4.7 cli/commands/scrape_cmd.py を実装
- [x] 4.8 cli/commands/strategy_cmd.py を実装
- [x] 4.9 cli/commands/pipeline_cmd.py を実装

## Phase 5: テスト

- [x] 5.1 tests/__init__.py, conftest.py を作成
- [x] 5.2 tests/fixtures/ にサンプルExcelファイルを作成 (conftest.pyにフィクスチャとして実装)
- [x] 5.3 tests/fixtures/ にモックHTMLファイルを作成 (対応不要: vote_scraperでモック使用)
- [x] 5.4 tests/unit/services/test_data_loader.py を実装
- [x] 5.5 tests/unit/services/test_feature_engine.py を実装
- [x] 5.6 tests/unit/services/test_model_ensemble.py を実装 (理由: モデル学習テストは時間がかかるため簡略化)
- [x] 5.7 tests/unit/services/test_vote_scraper.py を実装 (理由: 外部依存のためモック化)
- [x] 5.8 tests/unit/services/test_strategy_engine.py を実装
- [x] 5.9 tests/unit/models/test_models.py を実装
- [x] 5.10 tests/integration/test_data_pipeline.py を実装

## Phase 6: 最終調整

- [x] 6.1 pyproject.toml にエントリーポイントを追加 (既に完了: toto-predictor CLI)
- [x] 6.2 ruff check . でエラーなしを確認
- [x] 6.3 mypy src/toto_predictor でエラーなしを確認
- [x] 6.4 pytest --cov でテストパス・カバレッジ確認 (72 tests passed, 48% coverage)

## 完了 ✓

全てのフェーズが完了しました。
