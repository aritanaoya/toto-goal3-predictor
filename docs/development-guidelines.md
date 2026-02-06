# 開発ガイドライン (Development Guidelines)

## コーディング規約

### 命名規則

#### 変数・関数

**Python**:
```python
# ✅ 良い例
user_profile_data = fetch_user_profile()
def calculate_total_goals(matches: list[Match]) -> int:
    pass

# ❌ 悪い例
data = fetch()
def calc(arr):
    pass
```

**原則**:
- 変数: snake_case、名詞または名詞句
- 関数: snake_case、動詞で始める
- 定数: UPPER_SNAKE_CASE
- Boolean: `is_`, `has_`, `should_`で始める

#### クラス・データクラス

```python
# クラス: PascalCase、名詞
class DataLoader:
    pass

class FeatureEngine:
    pass

# データクラス: PascalCase
@dataclass
class Match:
    id: str
    date: datetime
    home_team: str

# 型エイリアス: PascalCase
TotoCategory = Literal["0", "1", "2", "3+"]
```

### コードフォーマット

**インデント**: 4スペース

**行の長さ**: 最大100文字

**フォーマッター**: ruff format

**例**:
```python
# 長い関数呼び出し
result = calculate_features(
    team=team_name,
    as_of_date=prediction_date,
    window_sizes=[5, 10, 20],
)

# 長いリスト
feature_columns = [
    "goals_mean",
    "goals_std",
    "xg_mean",
    "xg_std",
    "possession_mean",
]
```

### 型ヒント

**必須**: すべての関数に型ヒントを付ける

```python
# ✅ 良い例
def calculate_value_score(
    model_prob: float,
    vote_rate: float,
    min_rate: float = 0.01
) -> float:
    """バリュースコアを計算する"""
    return model_prob / max(vote_rate, min_rate)

# ❌ 悪い例
def calculate_value_score(model_prob, vote_rate, min_rate=0.01):
    return model_prob / max(vote_rate, min_rate)
```

### コメント規約

**関数・クラスのドキュメント**:
```python
def calculate_features(
    team: str,
    as_of_date: datetime,
    window_sizes: list[int] | None = None
) -> TeamFeatures:
    """指定日時点でのチームの特徴量を計算する

    Args:
        team: チーム名
        as_of_date: 特徴量を計算する基準日時
        window_sizes: 計算に使用するウィンドウサイズのリスト（デフォルト: [5, 10, 20]）

    Returns:
        計算された特徴量を含むTeamFeaturesオブジェクト

    Raises:
        ValueError: 指定されたチームのデータが不足している場合
    """
    pass
```

**インラインコメント**:
```python
# ✅ 良い例: なぜそうするかを説明
# ゼロ除算を防ぐため、最小値を設定
return model_prob / max(vote_rate, MIN_RATE)

# ❌ 悪い例: 何をしているか（コードを見れば分かる）
# vote_rateとMIN_RATEの大きい方で割る
return model_prob / max(vote_rate, MIN_RATE)
```

### エラーハンドリング

**原則**:
- 予期されるエラー: カスタム例外クラスを定義
- 予期しないエラー: 上位に伝播
- エラーを無視しない

**例**:
```python
# カスタム例外クラス
class DataNotFoundError(Exception):
    """データが見つからない場合の例外"""
    def __init__(self, team: str, message: str = ""):
        self.team = team
        self.message = message or f"チーム '{team}' のデータが見つかりません"
        super().__init__(self.message)


class ValidationError(Exception):
    """バリデーションエラー"""
    def __init__(self, field: str, value: any, message: str = ""):
        self.field = field
        self.value = value
        self.message = message or f"フィールド '{field}' の値 '{value}' が不正です"
        super().__init__(self.message)


# エラーハンドリング
try:
    features = feature_engine.calculate_features(team)
except DataNotFoundError as e:
    logger.warning(f"データ不足: {e.message}")
    # 代替処理またはスキップ
except Exception as e:
    logger.error(f"予期しないエラー: {e}")
    raise  # 上位に伝播
```

### ロギング

**ログレベルの使い分け**:
```python
import logging

logger = logging.getLogger(__name__)

# DEBUG: デバッグ情報（開発時のみ）
logger.debug(f"特徴量計算開始: {team}")

# INFO: 正常な処理の記録
logger.info(f"データインポート完了: {count}件")

# WARNING: 注意が必要だが処理は継続
logger.warning(f"データ不足のためスキップ: {team}")

# ERROR: エラー発生（処理は継続可能）
logger.error(f"スクレイピング失敗: {url}")

# CRITICAL: 致命的エラー（処理継続不可）
logger.critical(f"データベース接続エラー")
```

## Git運用ルール

### ブランチ戦略

**ブランチ種別**:
- `main`: 本番環境にデプロイ可能な状態
- `develop`: 開発の最新状態
- `feature/[機能名]`: 新機能開発
- `fix/[修正内容]`: バグ修正
- `refactor/[対象]`: リファクタリング

**フロー**:
```
main
  └─ develop
      ├─ feature/add-xgboost-model
      ├─ feature/vote-scraper
      └─ fix/excel-parsing-error
```

### コミットメッセージ規約

**フォーマット**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**:
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント
- `style`: コードフォーマット
- `refactor`: リファクタリング
- `test`: テスト追加・修正
- `chore`: ビルド、補助ツール等

**例**:
```
feat(model): XGBoostモデルを追加

- XGBClassifierによる得点分類モデルを実装
- Poissonモデルとのアンサンブルを構築
- キャリブレーション機能を追加

Closes #15
```

### プルリクエストプロセス

**作成前のチェック**:
- [ ] 全てのテストがパス (`pytest`)
- [ ] Lintエラーがない (`ruff check .`)
- [ ] 型チェックがパス (`mypy .`)
- [ ] 競合が解決されている

**PRテンプレート**:
```markdown
## 概要
[変更内容の簡潔な説明]

## 変更理由
[なぜこの変更が必要か]

## 変更内容
- [変更点1]
- [変更点2]

## テスト
- [ ] ユニットテスト追加
- [ ] 手動テスト実施

## 関連Issue
Closes #[Issue番号]
```

**レビュープロセス**:
1. セルフレビュー
2. 自動テスト実行（CI）
3. レビュアーアサイン
4. レビューフィードバック対応
5. 承認後マージ

---

## CI/CD設定

### GitHub Actions ワークフロー

#### テスト・リント実行 (.github/workflows/ci.yml)

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run ruff (lint)
        run: ruff check .

      - name: Run ruff (format check)
        run: ruff format --check .

      - name: Run mypy
        run: mypy src/toto_predictor

      - name: Run tests
        run: pytest --cov=src/toto_predictor --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
```

#### PRタイトルチェック (.github/workflows/pr-check.yml)

```yaml
name: PR Check

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  check-title:
    runs-on: ubuntu-latest
    steps:
      - name: Check PR title format
        run: |
          PR_TITLE="${{ github.event.pull_request.title }}"
          if ! echo "$PR_TITLE" | grep -qE "^(feat|fix|docs|style|refactor|test|chore)\(.+\): .+$"; then
            echo "PR title must follow format: type(scope): description"
            exit 1
          fi
```

### ブランチ保護ルール

| ルール | main | develop |
|--------|------|---------|
| 直接push禁止 | ✅ | ✅ |
| PR承認必須 | ✅（1名以上） | ✅（1名以上） |
| CIチェック必須 | ✅ | ✅ |
| 強制pushを禁止 | ✅ | - |

### CI/CDステータスバッジ

README.mdに以下のバッジを追加:

```markdown
[![CI](https://github.com/[user]/toto-goal3-predictor/actions/workflows/ci.yml/badge.svg)](https://github.com/[user]/toto-goal3-predictor/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/[user]/toto-goal3-predictor/branch/main/graph/badge.svg)](https://codecov.io/gh/[user]/toto-goal3-predictor)
```

---

## データベースマイグレーション戦略

### マイグレーション方針

本プロジェクトでは、SQLiteのシンプルさを活かし、軽量なマイグレーション方式を採用します。

### マイグレーションファイル構造

```
src/toto_predictor/db/
├── migrations/
│   ├── __init__.py
│   ├── migration_manager.py
│   └── versions/
│       ├── 001_initial_schema.py
│       ├── 002_add_team_features_cache.py
│       └── 003_add_prediction_history.py
```

### マイグレーションファイルフォーマット

```python
# migrations/versions/001_initial_schema.py
"""
Migration: Initial Schema
Version: 001
Created: 2025-02-04
"""

VERSION = 1
DESCRIPTION = "Create initial database schema"

def upgrade(conn):
    """Apply migration"""
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS matches (
            id TEXT PRIMARY KEY,
            date DATE NOT NULL,
            season INTEGER NOT NULL,
            ...
        );

        CREATE TABLE IF NOT EXISTS team_stats (
            ...
        );

        CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
    ''')

def downgrade(conn):
    """Rollback migration"""
    conn.executescript('''
        DROP TABLE IF EXISTS team_stats;
        DROP TABLE IF EXISTS matches;
    ''')
```

### マイグレーション管理

```python
# migration_manager.py
class MigrationManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_current_version(self) -> int:
        """現在のDBバージョンを取得"""
        ...

    def migrate(self, target_version: int | None = None) -> None:
        """指定バージョンまでマイグレーション実行"""
        ...

    def rollback(self, steps: int = 1) -> None:
        """指定ステップ数ロールバック"""
        ...
```

### CLIコマンド

```bash
# 最新バージョンまでマイグレーション
toto-predictor db migrate

# 特定バージョンまでマイグレーション
toto-predictor db migrate --version 2

# 1ステップロールバック
toto-predictor db rollback

# 現在のバージョン確認
toto-predictor db status
```

### バックアップとリカバリ

```bash
# マイグレーション前に自動バックアップ
# data/processed/toto_predictor.db.backup.{timestamp}

# 手動バックアップ
toto-predictor db backup

# リカバリ
toto-predictor db restore --file data/processed/toto_predictor.db.backup.20250204
```

---

## テスト戦略

### テストの種類

#### ユニットテスト

**対象**: 個別の関数・クラス

**カバレッジ目標**: 80%

**例**:
```python
import pytest
from toto_predictor.services.strategy_engine import StrategyEngine


class TestStrategyEngine:
    def test_calculate_value_score_normal(self):
        """正常なデータでバリュースコアを計算できる"""
        engine = StrategyEngine(db_path=":memory:")
        score = engine._calculate_value_score(
            model_prob=0.30,
            vote_rate=0.20
        )
        assert score == pytest.approx(1.5)

    def test_calculate_value_score_zero_vote_rate(self):
        """投票率が0の場合、最小値で計算される"""
        engine = StrategyEngine(db_path=":memory:")
        score = engine._calculate_value_score(
            model_prob=0.30,
            vote_rate=0.0
        )
        assert score == pytest.approx(30.0)  # 0.30 / 0.01

    def test_determine_action_high_value_high_prob(self):
        """高バリュー・高確率の場合「必買」を返す"""
        engine = StrategyEngine(db_path=":memory:")
        action = engine._determine_action(
            model_prob=0.35,
            value_score=1.6
        )
        assert action == "必買"
```

#### 統合テスト

**対象**: 複数コンポーネントの連携

**例**:
```python
class TestDataPipeline:
    def test_import_and_calculate_features(self, tmp_path):
        """データインポートから特徴量計算までの連携"""
        # セットアップ
        db_path = tmp_path / "test.db"
        loader = DataLoader(str(db_path))
        engine = FeatureEngine(str(db_path))

        # データインポート
        count = loader.load_excel("tests/fixtures/sample.xlsx", season=2024)
        assert count > 0

        # 特徴量計算
        features = engine.calculate_features(
            team="Yokohama F. Marinos",
            as_of_date=datetime(2024, 12, 1)
        )
        assert features.goals_mean > 0
        assert features.xg_mean > 0
```

#### E2Eテスト

**対象**: CLIコマンドの実行フロー

**例**:
```python
import subprocess


class TestCLI:
    def test_pipeline_command(self, tmp_path):
        """パイプラインコマンドが正常に実行される"""
        result = subprocess.run(
            ["toto-predictor", "pipeline", "--round", "1607"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "購入推奨" in result.stdout
```

### テスト命名規則

**パターン**: `test_[対象]_[条件]_[期待結果]`

**例**:
```python
# ✅ 良い例
def test_calculate_features_insufficient_data_raises_error(self):
    pass

def test_predict_valid_team_returns_probabilities(self):
    pass

def test_scrape_invalid_url_retries_three_times(self):
    pass

# ❌ 悪い例
def test1(self):
    pass

def test_works(self):
    pass
```

### モック・フィクスチャの使用

**原則**:
- 外部依存（Web API、ファイル）はモック化
- データベースはテスト用の一時DBを使用
- ビジネスロジックは実装を使用

**例**:
```python
import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def mock_scraper():
    """VoteScraperのモック"""
    scraper = Mock()
    scraper.fetch.return_value = [
        VoteRate(team="横浜FM", vote_0=0.22, vote_1=0.35, vote_2=0.25, vote_3plus=0.16)
    ]
    return scraper


@pytest.fixture
def temp_database(tmp_path):
    """テスト用一時データベース"""
    db_path = tmp_path / "test.db"
    return str(db_path)


def test_strategy_with_mock(mock_scraper, temp_database):
    """モックを使用した戦略テスト"""
    engine = StrategyEngine(db_path=temp_database)
    engine.scraper = mock_scraper
    # テスト実行
```

## コードレビュー基準

### レビューポイント

**機能性**:
- [ ] 要件を満たしているか
- [ ] エッジケースが考慮されているか
- [ ] エラーハンドリングが適切か

**可読性**:
- [ ] 命名が明確か
- [ ] 型ヒントが付いているか
- [ ] 複雑なロジックにコメントがあるか

**保守性**:
- [ ] 重複コードがないか
- [ ] 責務が明確に分離されているか
- [ ] テストが追加されているか

**パフォーマンス**:
- [ ] 不要な計算がないか
- [ ] N+1クエリがないか
- [ ] 大量データでも動作するか

### レビューコメントの書き方

**建設的なフィードバック**:
```markdown
## ✅ 良い例
この実装だと、試合数が増えた時にメモリ使用量が増大する可能性があります。
ジェネレータを使って逐次処理することを検討してはどうでしょうか？

## ❌ 悪い例
この書き方は良くないです。
```

**優先度の明示**:
- `[必須]`: 修正必須
- `[推奨]`: 修正推奨
- `[提案]`: 検討してほしい
- `[質問]`: 理解のための質問

---

## セキュリティプラクティス

### 機密情報管理

#### 禁止事項

- ソースコードへのAPIキー・パスワードのハードコーディング
- 認証情報を含むファイルのコミット
- ログへの機密情報出力

#### 推奨事項

```python
# ❌ 悪い例
API_KEY = "sk-1234567890abcdef"

# ✅ 良い例
import os
API_KEY = os.environ.get("TOTO_API_KEY")
if not API_KEY:
    raise EnvironmentError("TOTO_API_KEY environment variable is not set")
```

### 環境変数管理

```bash
# .env.example（コミット可）
TOTO_API_KEY=
LOG_LEVEL=INFO
DB_PATH=data/processed/toto_predictor.db

# .env（.gitignoreに追加、コミット不可）
TOTO_API_KEY=sk-actual-key-here
```

### 依存関係の脆弱性チェック

```bash
# pip-auditで脆弱性チェック
pip install pip-audit
pip-audit

# GitHub Dependabotの有効化（推奨）
# .github/dependabot.yml
```

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
```

### 入力検証

```python
from pathlib import Path

def validate_file_path(path: str) -> Path:
    """ファイルパスのセキュリティ検証"""
    resolved = Path(path).resolve()

    # ディレクトリトラバーサル防止
    allowed_dirs = [Path("data").resolve(), Path("tests/fixtures").resolve()]
    if not any(resolved.is_relative_to(d) for d in allowed_dirs):
        raise ValidationError("path", path, "許可されていないディレクトリへのアクセスです")

    return resolved
```

### SQLインジェクション対策

```python
# ❌ 危険: 文字列連結
team_name = "横浜FM'; DROP TABLE matches; --"
query = f"SELECT * FROM matches WHERE home_team='{team_name}'"

# ✅ 安全: パラメータ化クエリ
query = "SELECT * FROM matches WHERE home_team=?"
cursor.execute(query, (team_name,))
```

### スクレイピング倫理

| 項目 | ルール |
|------|-------|
| robots.txt | 必ず遵守 |
| リクエスト間隔 | 最低1秒 |
| User-Agent | 適切な識別子を設定 |
| 負荷 | 同時接続数1、連続アクセス制限 |

---

## 開発環境セットアップ

### 必要なツール

| ツール | バージョン | インストール方法 |
|--------|-----------|-----------------|
| Python | 3.11+ | pyenv または公式インストーラー |
| pip | 最新 | Python に同梱 |
| Git | 最新 | OS のパッケージマネージャー |

### セットアップ手順

```bash
# 1. リポジトリのクローン
git clone https://github.com/[user]/toto-goal3-predictor.git
cd toto-goal3-predictor

# 2. 仮想環境の作成・有効化
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 依存関係のインストール
pip install -e ".[dev]"

# 4. データベース初期化
python scripts/setup_db.py

# 5. テスト実行（動作確認）
pytest

# 6. Linter実行
ruff check .
ruff format .
```

### 推奨開発ツール

- **VS Code**: Python拡張機能、Pylance
- **Jupyter**: データ探索・モデル実験用
- **DB Browser for SQLite**: データ確認用

---

## pre-commit設定

### インストール

```bash
pip install pre-commit
pre-commit install
```

### 設定ファイル (.pre-commit-config.yaml)

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.2.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pandas-stubs
          - types-requests

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-merge-conflict

  - repo: https://github.com/commitizen-tools/commitizen
    rev: v3.13.0
    hooks:
      - id: commitizen
        stages: [commit-msg]
```

### フック実行タイミング

| フック | 実行タイミング | 説明 |
|--------|--------------|------|
| ruff | pre-commit | コードリント・自動修正 |
| ruff-format | pre-commit | コードフォーマット |
| mypy | pre-commit | 型チェック |
| commitizen | commit-msg | コミットメッセージ検証 |

### スキップ方法（緊急時のみ）

```bash
# 全てのフックをスキップ
git commit --no-verify -m "emergency fix"

# 特定のフックのみスキップ
SKIP=mypy git commit -m "fix: ..."
```

### VS Code設定

```json
// .vscode/settings.json
{
  "python.formatting.provider": "none",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  }
}
```
