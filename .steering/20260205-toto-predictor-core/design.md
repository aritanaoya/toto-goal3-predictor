# 設計書: toto GOAL3 Predictor コア機能実装

## アーキテクチャ概要

```
┌─────────────────────────────────────────────────────┐
│   CLIレイヤー (cli/)                                  │
│   - main.py: Typerエントリーポイント                   │
│   - commands/: 各サブコマンド実装                      │
├─────────────────────────────────────────────────────┤
│   サービスレイヤー (services/)                         │
│   - DataLoader: Excel→DB取り込み                      │
│   - FeatureEngine: 特徴量計算                         │
│   - ModelEnsemble: 予測モデル                         │
│   - VoteScraper: 投票率取得                           │
│   - StrategyEngine: バリュー計算・推奨生成             │
├─────────────────────────────────────────────────────┤
│   データレイヤー (db/)                                 │
│   - database.py: SQLite接続管理                       │
│   - repositories/: CRUD操作                          │
├─────────────────────────────────────────────────────┤
│   モデルレイヤー (models/)                             │
│   - データクラス定義（Match, TeamStats等）              │
│   - カスタム例外クラス                                 │
└─────────────────────────────────────────────────────┘
```

## 実装順序

### Phase 1: 基盤層
1. models/exceptions.py - 例外クラス
2. models/match.py - 試合モデル
3. models/team_stats.py - チーム統計モデル
4. db/database.py - DB接続・スキーマ
5. db/repositories/ - リポジトリ

### Phase 2: サービス層（データ処理）
6. services/data_loader.py - データ取り込み
7. services/feature_engine.py - 特徴量計算

### Phase 3: サービス層（予測・戦略）
8. models/prediction.py - 予測モデル
9. models/vote_rate.py - 投票率モデル
10. models/recommendation.py - 推奨モデル
11. services/model_ensemble.py - ML予測
12. services/vote_scraper.py - スクレイピング
13. services/strategy_engine.py - 戦略計算

### Phase 4: CLI層
14. cli/main.py - エントリーポイント
15. cli/commands/ - 各コマンド

### Phase 5: テスト
16. tests/fixtures/ - テストデータ
17. tests/unit/ - ユニットテスト
18. tests/integration/ - 統合テスト

## データフロー

```
Wyscout Excel → DataLoader → SQLite DB
                    ↓
              FeatureEngine → 特徴量
                    ↓
              ModelEnsemble → 予測確率
                    ↓
              VoteScraper → 投票率
                    ↓
              StrategyEngine → 購入推奨 → Markdownレポート
```

## 主要クラス設計

### DataLoader
- load_excel(file_path, season) → int
- load_directory(dir_path, season) → int
- get_team_matches(team, limit) → list[Match]

### FeatureEngine
- calculate_features(team, as_of_date, window_sizes) → TeamFeatures
- prepare_training_data(seasons) → (X, y)

### ModelEnsemble
- train(X, y, cv_folds) → metrics
- predict(features) → Prediction
- save/load()

### VoteScraper
- fetch(round_number) → list[VoteRate]
- _parse_html(html) → dict
- _retry_fetch(url, max_retries) → str

### StrategyEngine
- calculate_value_scores(predictions, votes) → list[Recommendation]
- generate_report(recommendations, output_path) → None

## SQLiteスキーマ

```sql
CREATE TABLE matches (
    id TEXT PRIMARY KEY,
    date DATE NOT NULL,
    season INTEGER NOT NULL,
    competition TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_goals INTEGER,
    away_goals INTEGER,
    duration INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE team_stats (
    id TEXT PRIMARY KEY,
    match_id TEXT NOT NULL REFERENCES matches(id),
    team TEXT NOT NULL,
    is_home BOOLEAN NOT NULL,
    goals INTEGER,
    xg REAL,
    shots INTEGER,
    shots_on_target INTEGER,
    possession REAL,
    passes INTEGER,
    passes_accurate INTEGER,
    ppda REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
