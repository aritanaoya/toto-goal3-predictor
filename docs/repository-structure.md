# リポジトリ構造定義書 (Repository Structure Document)

## 実装状況サマリー

**最終更新**: 2026-02-06

| カテゴリ | 実装済み | 未実装 | 進捗率 |
|---------|---------|--------|-------|
| CLIコマンド | 7 | 0 | 100% |
| サービス | 5 | 0 | 100% |
| データモデル | 6 | 0 | 100% |
| DBレイヤー | 1 | 0 | 100% |
| リポジトリ | 2 | 0 | 100% |
| ユニットテスト | 13 | 0 | 100% |
| 統合テスト | 1 | 2 | 33% |
| CI/CD | 0 | 2 | 0% |

**凡例**:
- `[実装済み]`: 完全に実装されたファイル
- `[未実装]`: 設計済みだが実装されていないファイル
- `[空]`: ディレクトリは存在するが中身がない（.gitkeepのみ）
- `[データあり]`: 実データが配置済み

**データ状況**:
- Wyscout 2024: [空]
- Wyscout 2025: [データあり] 10チーム分のExcelファイル
- 処理済みデータ: なし
- 学習済みモデル: なし

---

## プロジェクト構造

```
toto-goal3-predictor/
├── src/                          # ソースコード
│   └── toto_predictor/           # メインパッケージ
│       ├── cli/                  # CLIレイヤー [実装済み]
│       │   ├── main.py           # [実装済み] Typerアプリ
│       │   └── commands/         # [実装済み] サブコマンド（7コマンド）
│       ├── services/             # サービスレイヤー [実装済み]
│       ├── models/               # データモデル [実装済み]
│       └── db/                   # データレイヤー [実装済み]
│           └── repositories/     # [実装済み] リポジトリ
├── tests/                        # テストコード
│   ├── unit/                     # ユニットテスト [実装済み]
│   ├── integration/              # 統合テスト [一部実装]
│   └── fixtures/                 # テスト用データ [空]
├── data/                         # データファイル
│   ├── wyscout/                  # Wyscout生データ
│   │   ├── 2024/                 # [空]
│   │   └── 2025/                 # [データあり]
│   ├── processed/                # 処理済みデータ [空]
│   ├── predictions/              # 予測結果 [空]
│   └── votes/                    # 投票率データ [空]
├── models/                       # 学習済みモデル [空]
├── reports/                      # 出力レポート [空]
├── docs/                         # プロジェクトドキュメント
├── scripts/                      # ユーティリティスクリプト [空]
├── .github/                      # GitHub設定 [未作成]
│   └── workflows/                # CI/CDワークフロー [未作成]
│       └── ci.yml                # [未作成]
├── pyproject.toml                # パッケージ設定（ruff設定含む）
└── .pre-commit-config.yaml       # pre-commit設定 [未作成]
```

## ディレクトリ詳細

### src/toto_predictor/ (ソースコードディレクトリ)

#### cli/

**役割**: コマンドラインインターフェースの実装

**配置ファイル**:
- `main.py`: Typerアプリのエントリーポイント
- `commands/*.py`: 各サブコマンドの実装

**命名規則**:
- ファイル名: snake_case
- コマンドファイル: `{command_name}_cmd.py`

**依存関係**:
- 依存可能: services/
- 依存禁止: db/（直接アクセス禁止）

**例**:
```
cli/
├── __init__.py
├── main.py
└── commands/
    ├── __init__.py
    ├── import_cmd.py
    ├── train_cmd.py
    ├── predict_cmd.py
    ├── scrape_cmd.py
    ├── strategy_cmd.py
    ├── pipeline_cmd.py
    └── features_cmd.py
```

#### services/

**役割**: ビジネスロジックの実装

**配置ファイル**:
- `data_loader.py`: データ読み込み・保存
- `feature_engine.py`: 特徴量エンジニアリング
- `model_ensemble.py`: 機械学習モデル
- `vote_scraper.py`: 投票率スクレイピング
- `strategy_engine.py`: 戦略計算

**命名規則**:
- ファイル名: snake_case
- クラス名: PascalCase

**依存関係**:
- 依存可能: models/, db/
- 依存禁止: cli/

**例**:
```
services/
├── __init__.py
├── data_loader.py
├── feature_engine.py
├── model_ensemble.py
├── vote_scraper.py
└── strategy_engine.py
```

#### models/

**役割**: データモデル（dataclass）の定義

**配置ファイル**:
- `match.py`: 試合データモデル
- `team_stats.py`: チーム統計モデル
- `prediction.py`: 予測結果モデル
- `vote_rate.py`: 投票率モデル
- `recommendation.py`: 購入推奨モデル

**命名規則**:
- ファイル名: snake_case（単数形）
- クラス名: PascalCase

**依存関係**:
- 依存可能: なし（純粋なデータ定義）
- 依存禁止: services/, cli/, db/

**例**:
```
models/
├── __init__.py
├── match.py
├── team_stats.py
├── prediction.py
├── vote_rate.py
└── recommendation.py
```

#### db/

**役割**: データベース操作、永続化処理

**配置ファイル**:
- `database.py`: SQLite接続・操作
- `repositories/*.py`: 各エンティティのリポジトリ

**命名規則**:
- ファイル名: snake_case
- リポジトリ: `{entity}_repository.py`

**依存関係**:
- 依存可能: models/
- 依存禁止: services/, cli/

**例**:
```
db/
├── __init__.py
├── database.py
└── repositories/
    ├── __init__.py
    ├── match_repository.py
    └── team_stats_repository.py
```

### tests/ (テストディレクトリ)

#### unit/

**役割**: ユニットテストの配置

**構造**:
```
tests/unit/
├── services/
│   ├── test_data_loader.py
│   ├── test_feature_engine.py
│   ├── test_model_ensemble.py
│   ├── test_vote_scraper.py
│   └── test_strategy_engine.py
├── models/
│   └── test_models.py
├── db/
│   ├── test_database.py
│   ├── test_match_repository.py
│   └── test_team_stats_repository.py
└── cli/
    ├── test_main.py
    └── commands/
        ├── test_import_cmd.py
        ├── test_train_cmd.py
        ├── test_predict_cmd.py
        ├── test_scrape_cmd.py
        ├── test_strategy_cmd.py
        └── test_pipeline_cmd.py
```

**命名規則**:
- パターン: `test_{テスト対象ファイル名}.py`
- 例: `data_loader.py` → `test_data_loader.py`

#### integration/

**役割**: 統合テストの配置

**構造**:
```
tests/integration/
├── test_data_pipeline.py
├── test_prediction_flow.py
└── test_strategy_flow.py
```

#### fixtures/

**役割**: テスト用データの配置

**構造**:
```
tests/fixtures/
├── sample_excel/
│   └── Team Stats Sample.xlsx
├── sample_html/
│   └── totoone_mock.html
└── expected_outputs/
    ├── features.json
    └── predictions.json
```

### data/ (データディレクトリ)

#### wyscout/

**役割**: Wyscoutからダウンロードした生データ

**構造**:
```
data/wyscout/
├── 2024/
│   └── Team Stats *.xlsx
└── 2025/
    └── Team Stats *.xlsx
```

**命名規則**:
- ディレクトリ: シーズン年（YYYY）
- ファイル: Wyscoutのデフォルト形式を維持

#### processed/

**役割**: 処理済みデータ（SQLite等）

**配置ファイル**:
- `toto_predictor.db`: SQLiteデータベース

#### predictions/

**役割**: モデル予測結果の保存

**命名規則**:
- パターン: `round_{回号}.json`
- 例: `round_1607.json`

#### votes/

**役割**: スクレイピングした投票率データ

**命名規則**:
- パターン: `round_{回号}.json`
- 例: `round_1607.json`

### models/ (学習済みモデルディレクトリ)

**役割**: 学習済み機械学習モデルの保存

**配置ファイル**:
- `poisson_model.joblib`: Poissonモデル
- `xgb_model.joblib`: XGBoostモデル
- `calibrator.joblib`: キャリブレーター
- `metadata.json`: モデルのメタデータ（学習日時、精度等）

### reports/ (レポートディレクトリ)

**役割**: 生成された購入推奨レポート

**命名規則**:
- パターン: `round_{回号}_strategy.md`
- 例: `round_1607_strategy.md`

### docs/ (ドキュメントディレクトリ)

**配置ドキュメント**:
- `product-requirements.md`: プロダクト要求定義書
- `functional-design.md`: 機能設計書
- `architecture.md`: アーキテクチャ設計書
- `repository-structure.md`: リポジトリ構造定義書（本ドキュメント）
- `development-guidelines.md`: 開発ガイドライン
- `glossary.md`: 用語集

### scripts/ (スクリプトディレクトリ)

**役割**: 開発・運用補助スクリプト

**配置ファイル**:
- `setup_db.py`: データベース初期化
- `backup.py`: バックアップ実行

## ファイル配置規則

### ソースファイル

| ファイル種別 | 配置先 | 命名規則 | 例 |
|------------|--------|---------|-----|
| CLIコマンド | src/toto_predictor/cli/commands/ | {command}_cmd.py | import_cmd.py |
| サービス | src/toto_predictor/services/ | {service_name}.py | data_loader.py |
| データモデル | src/toto_predictor/models/ | {entity}.py | match.py |
| リポジトリ | src/toto_predictor/db/repositories/ | {entity}_repository.py | match_repository.py |

### テストファイル

| テスト種別 | 配置先 | 命名規則 | 例 |
|-----------|--------|---------|-----|
| ユニットテスト | tests/unit/{layer}/ | test_{filename}.py | test_data_loader.py |
| 統合テスト | tests/integration/ | test_{feature}.py | test_data_pipeline.py |

### 設定ファイル

| ファイル種別 | 配置先 | 命名規則 | 状態 |
|------------|--------|---------|------|
| パッケージ設定 | プロジェクトルート | pyproject.toml | 実装済み（ruff, pytest, mypy設定含む） |
| 環境変数テンプレート | プロジェクトルート | .env.example | [未作成] |
| 環境変数 | プロジェクトルート | .env | [未作成]（.gitignoreに追加済み） |
| pre-commit設定 | プロジェクトルート | .pre-commit-config.yaml | [未作成] |

> **Note**: Linter設定（ruff）は `pyproject.toml` の `[tool.ruff]` セクションに統合されています。

## 命名規則

### ディレクトリ名

- **レイヤーディレクトリ**: 複数形、snake_case
  - 例: `services/`, `models/`, `commands/`
- **データディレクトリ**: 単数形または複数形、snake_case
  - 例: `wyscout/`, `predictions/`

### ファイル名

- **Pythonファイル**: snake_case
  - 例: `data_loader.py`, `feature_engine.py`
- **クラス名**: PascalCase
  - 例: `DataLoader`, `FeatureEngine`
- **関数名**: snake_case
  - 例: `calculate_features()`, `load_excel()`
- **定数**: UPPER_SNAKE_CASE
  - 例: `BASE_URL`, `DEFAULT_WINDOW_SIZE`

### テストファイル名

- パターン: `test_{テスト対象}.py`
- 例: `test_data_loader.py`, `test_strategy_engine.py`

## 依存関係のルール

### レイヤー間の依存

```
cli/
  ↓ (OK)
services/
  ↓ (OK)
db/
  ↓ (OK)
models/  (全レイヤーから参照可能)
```

**禁止される依存**:
- db/ → services/ (❌)
- db/ → cli/ (❌)
- services/ → cli/ (❌)
- models/ → 他のレイヤー (❌)

### モジュール間の依存

**循環依存の禁止**:
```python
# ❌ 悪い例: 循環依存
# data_loader.py
from .feature_engine import FeatureEngine

# feature_engine.py
from .data_loader import DataLoader  # 循環依存
```

**解決策**:
```python
# ✅ 良い例: インターフェース経由
# data_loader.py
class DataLoader:
    def get_matches(self, team: str) -> list[Match]:
        ...

# feature_engine.py
class FeatureEngine:
    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader
```

## スケーリング戦略

### 機能の追加

新しい機能を追加する際の配置方針:

1. **新しいデータソース**: `services/`に新しいローダーを追加
2. **新しいモデル**: `services/model_ensemble.py`にモデルを追加
3. **新しい出力形式**: `services/strategy_engine.py`にフォーマッターを追加

**例: 新しいスクレイピング先の追加**:
```
services/
├── vote_scraper.py           # 既存
└── scrapers/                 # 新規ディレクトリ
    ├── __init__.py
    ├── totoone_scraper.py    # 分離
    └── rakuten_scraper.py    # 新規追加
```

### ファイルサイズの管理

**ファイル分割の目安**:
- 1ファイル: 300行以下を推奨
- 300-500行: リファクタリングを検討
- 500行以上: 分割を強く推奨

## 特殊ディレクトリ

### .steering/ (ステアリングファイル)

**役割**: 特定の開発作業における「今回何をするか」を定義

**構造**:
```
.steering/
└── [YYYYMMDD]-[task-name]/
    ├── requirements.md      # 今回の作業の要求内容
    ├── design.md            # 変更内容の設計
    └── tasklist.md          # タスクリスト
```

**命名規則**: `20250204-add-new-model` 形式

### .claude/ (Claude Code設定)

**役割**: Claude Code設定とカスタマイズ

**構造**:
```
.claude/
├── commands/                # スラッシュコマンド
├── skills/                  # タスクモード別スキル
└── agents/                  # サブエージェント定義
```

## 除外設定

### .gitignore

プロジェクトで除外すべきファイル:
```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/

# データ（大きいファイル）
data/wyscout/**/*.xlsx
data/processed/*.db
models/*.joblib

# 環境設定
.env

# IDE
.vscode/
.idea/

# OS
.DS_Store

# 一時ファイル
*.log
.steering/

# Claude
.claude/
```

### 追跡すべきファイル

```
# 空ディレクトリの維持
data/wyscout/2024/.gitkeep
data/wyscout/2025/.gitkeep
data/processed/.gitkeep
data/predictions/.gitkeep
data/votes/.gitkeep
models/.gitkeep
reports/.gitkeep
```
