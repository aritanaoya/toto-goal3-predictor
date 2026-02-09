# 設計書

## アーキテクチャ概要

既存のレイヤードアーキテクチャを維持しつつ、品質向上に必要なコンポーネントを追加・改善する。

```
cli/       → Entry point (Typer + Rich)
    ↓
services/  → Business logic (改善対象)
    ↓
db/        → Persistence (SQLite + repositories)
    ↓
models/    → Pure data structures (バリデーション強化)
```

## コンポーネント設計

### 1. VoteScraper（改善）

**責務**:
- totoONEサイトからGOAL3投票率を取得
- HTMLパースによるデータ抽出
- キャッシュ管理

**実装の要点**:
- 実際のtotoONEサイト構造に合わせたセレクタ修正
- モックデータへの自動フォールバックを削除
- `ParseError` の明示的な発生

**対象ファイル**: `src/toto_predictor/services/vote_scraper.py`

### 2. FeatureEngine（改善）

**責務**:
- 特徴量計算
- 欠損値処理
- リーク防止

**実装の要点**:
- `calculate_features` で NaN をハンドリング
- `prepare_training_data` で警告ログ出力
- 比率計算時の分母ゼロガード

**対象ファイル**: `src/toto_predictor/services/feature_engine.py`

### 3. TeamStats（バリデーション強化）

**責務**:
- チーム統計データの格納
- データ整合性の保証

**実装の要点**:
- `shots_on_target <= shots` の検証
- `possession` は 0-100 の範囲
- `ppda > 0` の検証

**対象ファイル**: `src/toto_predictor/models/stats.py`

### 4. CI/CDパイプライン（新規）

**責務**:
- 自動テスト実行
- コード品質チェック

**実装の要点**:
- GitHub Actionsで実装
- pytest + coverage
- ruff lint
- mypy type check

**対象ファイル**: `.github/workflows/ci.yml`

## データフロー

### リーク防止の仕組み
```
1. FeatureEngine.calculate_features(team, as_of_date)
2. TeamStatsRepository.find_by_team(team, before_date=as_of_date)
3. SQL: WHERE m.date < as_of_date（「未満」で試合当日を除外）
4. 特徴量計算（試合当日のデータは含まれない）
```

### 欠損値処理フロー
```
1. calculate_features() で統計量計算
2. NaN が発生した場合は 0 で補完
3. 警告ログを出力
4. 学習データ準備時に再度チェック
```

## エラーハンドリング戦略

### カスタムエラークラス（既存）

```python
TotoPredictorError
├── DataError (DataNotFoundError, DataFormatError, DatabaseError)
├── ModelError (ModelNotTrainedError, PredictionError)
├── ScrapingError (NetworkError, ParseError)
└── ValidationError
```

### エラーハンドリングパターン

- VoteScraper: HTML解析失敗時は `ParseError` を発生（モックフォールバック削除）
- FeatureEngine: データ不足時は `DataNotFoundError` を発生
- TeamStats: 不正データ時は `ValidationError` を発生

## テスト戦略

### ユニットテスト
- VoteScraper: 実サイト構造のモックHTMLでテスト
- FeatureEngine: NaN処理、リーク防止のテスト
- TeamStats: バリデーションエラーのテスト

### 統合テスト
- E2Eパイプライン: `import` → `train` → `predict` → `strategy`
- リーク防止検証: 試合当日データの除外確認

## 依存ライブラリ

既存のライブラリを使用（追加なし）

```toml
[project.dependencies]
# 既存のまま
pandas
numpy
scikit-learn
xgboost
requests
beautifulsoup4
typer
rich
```

## ディレクトリ構造

```
追加・変更されるファイル:
├── .github/
│   └── workflows/
│       └── ci.yml（新規）
├── docs/
│   └── preprocessing.md（新規）
├── src/toto_predictor/
│   ├── models/
│   │   └── stats.py（バリデーション追加）
│   └── services/
│       ├── vote_scraper.py（HTML解析修正）
│       └── feature_engine.py（欠損値処理追加）
└── tests/
    └── unit/services/
        ├── test_vote_scraper.py（テスト追加）
        └── test_feature_engine.py（リーク防止テスト追加）
```

## 実装の順序

1. フェーズ1: 基盤整備（テスト実行、CI/CD、前処理設計書）
2. フェーズ2: VoteScraper改善（サイト調査、HTML解析修正）
3. フェーズ3: 前処理とデータ品質改善（欠損値、外れ値、リーク防止テスト）
4. フェーズ4: データバリデーション強化（TeamStats）
5. フェーズ5: テストカバレッジ向上
6. フェーズ6: ログシステム強化（P2、時間があれば）

## セキュリティ考慮事項

- VoteScraper: totoONEの利用規約とrobots.txtを確認
- スクレイピング間隔: 1秒以上のインターバル

## パフォーマンス考慮事項

- 今回のフェーズではパフォーマンス最適化はスコープ外
- 将来的にキャッシングを検討

## 将来の拡張性

- 前処理パイプラインのドキュメント化により、特徴量追加が容易に
- リーク防止テストにより、新特徴量追加時の安全性を保証
