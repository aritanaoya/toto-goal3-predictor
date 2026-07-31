# 予測改善計画: 「1点集中」解消 + チケット戦略 + Playwright投票率取得

## Context

### 現状の問題

**問題1: 全チームの予測が「1点」に集中**
- J1全チーム・全試合が「1点(33-38%)」に予測される
- 原因: 特徴量がチーム固有のローリング平均のみ（`feature_engine.py` L44-178）
- `calculate_opponent_features()` (L218-246) が存在するが**学習・予測で未使用**
- Poisson λ ≈ 1.2 に全チーム集中し、確率分布が同質化

**問題2: 投票率を活かした狙い定めができていない**
- `value_score = model_prob / vote_rate` は単純すぎる（`strategy_engine.py` L245-255）
- チーム×カテゴリごとの独立評価 → toto GOAL3の組合せ性を無視
- 「どのチケットを買うか」の回答がない
- パリミュチュエルの払戻構造（人気=低配当）を未考慮

**問題3: 投票率データが取得できない**
- totoONEがSPA構造でBeautifulSoupでは取得不可（improvement-plan振り返りより）
- 投票率なしでは戦略計算が機能しない

### 改善の狙い

1. 対戦相手の守備力を考慮し、チームごとに予測を分散させる
2. 期待値(EV)ベースの評価で「本命・対抗・穴」チケット戦略を提示
3. Playwrightで投票率を自動取得し、戦略パイプラインを完結させる

---

## ステージ1: 対戦相手考慮型の予測（予測の分散化）

### 1-1. MatchupFeatures データモデル作成
**新規**: `src/toto_predictor/models/matchup_features.py`

既存`TeamFeatures`(23特徴量)を拡張し、対戦固有の特徴量を持つデータクラス:
- チーム攻撃指標（TeamFeaturesから: goals_mean, xg_mean, shots系など）
- 相手守備指標（opp_conceded_mean, opp_xg_against_mean, opp_ppda_mean等）
- 交互作用特徴量:
  - `attack_vs_defense` = team_xg_mean - opp_xg_against_mean
  - `xg_diff` = team_xg_mean - opp_xg_mean
  - `possession_diff` = team_possession - (100 - opp_possession)
- ホーム/アウェイ調整済みゴール平均
- `to_dict()`, `to_feature_vector()`, `get_feature_names()` メソッド
- 合計約35特徴量 → **同じチームでも相手が違えば異なる予測になる**

### 1-2. FeatureEngine に `calculate_matchup_features()` 追加
**変更**: `src/toto_predictor/services/feature_engine.py`

- 既存の `calculate_opponent_features()` (L218-246) を拡張した新メソッド
- 内部で `calculate_features(team)` + `calculate_features(opponent)` を呼び、交互作用特徴量を算出
- `MatchupFeatures` データクラスを返す
- 既存メソッドは後方互換のため残す

### 1-3. `prepare_training_data()` を対戦カード対応に変更
**変更**: `src/toto_predictor/services/feature_engine.py` (L248-324)

- 現在: `calculate_features(team)` のみ → チーム単体の特徴量
- 変更後: `calculate_matchup_features(team, opponent, is_home)` を使用
- matchのhome_team/away_teamペアから相手を特定
- **モデル再学習が必要**（特徴量の形状が24→35に変更）

### 1-4. XGBoostを4クラス直接分類に変更
**変更**: `src/toto_predictor/services/model_ensemble.py`

- 現在: 6クラス(0-5点) → 4カテゴリ集約で情報ロス（L87-103, L285-299）
- 変更後: `num_class=4`、targets を `clip(upper=3)` に変更
- `_xgb_to_toto_probs()` を4クラス直接マッピングに簡略化

### 1-5. ModelEnsemble で MatchupFeatures を受付
**変更**: `src/toto_predictor/services/model_ensemble.py` (L137)

- `predict()` の型に `MatchupFeatures` を追加
- MatchupFeatures → DataFrame変換ロジックを追加

### 1-6. predict コマンドに `--matches` オプション追加
**変更**: `src/toto_predictor/cli/commands/predict_cmd.py`

- `--matches "横浜FM:町田,長崎:広島,..."` で対戦カード指定
- 指定時は `calculate_matchup_features()` を使用
- 未指定時は従来の `calculate_features()` にフォールバック

---

## ステージ2: 戦略エンジンの刷新（EV・チケット戦略）

### 2-1. Ticket データモデル作成
**新規**: `src/toto_predictor/models/ticket.py`

```
TeamPick: 1チームの選択
  - team, category, model_prob, vote_rate, ev_contribution, is_contrarian

TicketRecommendation: 1枚のチケット全体
  - ticket_type: "本命" | "対抗" | "穴"
  - picks: list[TeamPick]（12チーム分）
  - ticket_prob: Π(model_prob) — 全チーム的中確率の積
  - ticket_vote_share: Π(vote_rate) — 投票率の積
  - estimated_payout: 0.49 / ticket_vote_share × ¥200
  - estimated_ev: ticket_prob × estimated_payout - ¥200
  - cost: ¥200
```

### 2-2. Recommendation に EV・逆張りスコア追加
**変更**: `src/toto_predictor/models/recommendation.py`

デフォルト値付きで後方互換:
- `ev: float = 0.0` — model_prob × (0.49 / vote_rate) - 1
- `contrarian_score: float = 0.0` — (model_prob - vote_rate) / vote_rate
- `is_best_ev_for_team: bool = False`

### 2-3. StrategyEngine に新メソッド群を追加
**変更**: `src/toto_predictor/services/strategy_engine.py`

既存の `calculate_value_scores()` と `generate_report()` は**そのまま残す**（テスト互換）。

**新定数**: `PAYOUT_RATE = 0.49`

**新メソッド `calculate_ev_scores()`**:
- EV = model_prob × (PAYOUT_RATE / vote_rate) - 1
- contrarian_score = (model_prob - vote_rate) / vote_rate
- 各チームの**最高EVカテゴリ**を特定（最頻カテゴリとは異なりうる）

**新メソッド `generate_tickets()`**（コア改善）:
1. 各チームのカテゴリ別EV分析テーブル構築
2. **本命（1-2枚）**: 各チーム最頻カテゴリ
3. **対抗（1-2枚）**: EV最大カテゴリが最頻と異なるチーム1-2を差替
4. **穴（1-2枚）**: contrarian_score上位3-4チームを逆張りカテゴリに差替

**新メソッド `generate_enhanced_report()`**:
- 推奨チケット表（本命/対抗/穴ごとに全チームの選択表示）
- チーム別EV分析（全4カテゴリのモデル vs 投票 vs EV比較）
- 逆張り機会ハイライト
- 投資サマリー（合計購入額、推定EV）

### 2-4. CLI strategy/pipeline コマンド拡張
**変更**: `src/toto_predictor/cli/commands/strategy_cmd.py`
- `--tickets` フラグ追加 → チケット戦略モード
- `--num-tickets` で生成枚数を指定（デフォルト5）

**変更**: `src/toto_predictor/cli/commands/pipeline_cmd.py`
- ステップ5で `generate_tickets()` + `generate_enhanced_report()` を実行
- `--matches` オプション追加

---

## ステージ3: Playwright による投票率自動取得

### 3-1. Playwright 依存追加
**変更**: `pyproject.toml`

```toml
dependencies = [
    # ... 既存 ...
    "playwright>=1.40",
]

[project.optional-dependencies]
dev = [
    # ... 既存 ...
    "pytest-playwright>=0.4",
]
```

インストール後に `playwright install chromium` を実行。

### 3-2. VoteScraper を Playwright 対応に書き換え
**変更**: `src/toto_predictor/services/vote_scraper.py`

- 既存の `requests` + `BeautifulSoup` ベースの `_retry_fetch()` + `_parse_html()` を **Playwright ベースに置換**
- `fetch()` メソッドのシグネチャは変更なし（後方互換）
- 新しい内部フロー:
  1. `playwright.sync_api` で Chromium をヘッドレス起動
  2. totoONE の GOAL3 ページにアクセス
  3. JavaScript レンダリング完了を待機（`page.wait_for_selector()`）
  4. レンダリング済みHTMLからBeautifulSoupで解析
  5. 既存の `_parse_html()` を再利用（セレクタの調整は必要）
- `requests` / `beautifulsoup4` は他でも使われる可能性があるため依存は残す
- キャッシュ機能（`get_cached()`, `_save_cache()`）はそのまま活用

### 3-3. scrape コマンド更新
**変更**: `src/toto_predictor/cli/commands/scrape_cmd.py`

- Playwrightの初期化メッセージ追加
- ブラウザ起動中のスピナー表示
- `--headless` / `--no-headless` オプション（デバッグ用にブラウザ表示可能に）

### 3-4. VoteScraper テスト更新
**変更**: `tests/unit/services/test_vote_scraper.py`

- Playwright のモック（`unittest.mock.patch` で `playwright.sync_api` をモック）
- レンダリング済みHTMLのフィクスチャでパース結果テスト
- キャッシュ読み書きテストは既存のまま

---

## テスト

### 新規テスト
| ファイル | テスト内容 |
|---------|-----------|
| `tests/unit/models/test_matchup_features.py` | 作成・変換・交互作用特徴量の正しさ |
| `tests/unit/models/test_ticket.py` | TeamPick/TicketRecommendation作成・シリアライズ |
| `tests/unit/services/test_feature_engine_matchup.py` | 対戦カード特徴量、**同チーム異相手で特徴量が変わること** |
| `tests/unit/services/test_strategy_engine_enhanced.py` | EV計算式、チケット生成、レポート |

### 既存テストへの影響
| ファイル | 影響 |
|---------|------|
| `tests/unit/services/test_strategy_engine.py` | 変更なし（後方互換） |
| `tests/unit/services/test_model_ensemble.py` | `test_xgb_to_toto_probs` のみ修正（6→4クラス） |
| `tests/unit/services/test_vote_scraper.py` | Playwright対応に修正 |
| `tests/conftest.py` | 新フィクスチャ追加 |

---

## 実装順序

| 順 | 内容 | 後方互換 | 再学習 |
|----|------|---------|--------|
| 1 | MatchupFeatures モデル + テスト | ○ | 不要 |
| 2 | Ticket モデル + テスト | ○ | 不要 |
| 3 | Recommendation にEV/contrarian追加 | ○ | 不要 |
| 4 | FeatureEngine matchup対応 + テスト | ○ | 不要 |
| 5 | ModelEnsemble 4クラス化 + matchup対応 + テスト | △ | **必要** |
| 6 | prepare_training_data matchup対応 | △ | **必要** |
| 7 | StrategyEngine EV・チケット追加 + テスト | ○ | 不要 |
| 8 | Playwright VoteScraper + テスト | △ | 不要 |
| 9 | CLI拡張（predict/strategy/pipeline/scrape） | ○ | 不要 |
| 10 | 再学習 + 予測実行 + 結果確認 | - | **実行** |

---

## 変更対象ファイル一覧

### 新規作成（6ファイル）
- `src/toto_predictor/models/matchup_features.py`
- `src/toto_predictor/models/ticket.py`
- `tests/unit/models/test_matchup_features.py`
- `tests/unit/models/test_ticket.py`
- `tests/unit/services/test_feature_engine_matchup.py`
- `tests/unit/services/test_strategy_engine_enhanced.py`

### 変更（12ファイル）
- `pyproject.toml` — playwright依存追加
- `src/toto_predictor/models/__init__.py` — 新モデルのエクスポート
- `src/toto_predictor/models/recommendation.py` — ev, contrarian_score追加
- `src/toto_predictor/services/feature_engine.py` — matchup特徴量, training data変更
- `src/toto_predictor/services/model_ensemble.py` — 4クラス化, MatchupFeatures対応
- `src/toto_predictor/services/strategy_engine.py` — EV計算, チケット生成, 拡張レポート
- `src/toto_predictor/services/vote_scraper.py` — Playwright対応
- `src/toto_predictor/cli/commands/predict_cmd.py` — --matches追加
- `src/toto_predictor/cli/commands/strategy_cmd.py` — --tickets追加
- `src/toto_predictor/cli/commands/pipeline_cmd.py` — 新戦略統合
- `tests/conftest.py` — 新フィクスチャ追加
- `tests/unit/services/test_model_ensemble.py` — XGB 4クラスのテスト修正

---

## 検証方法

1. `pytest` — 全テスト通過（既存250件 + 新規）
2. `ruff check . && mypy src/toto_predictor` — lint/型チェック通過
3. `playwright install chromium` — ブラウザインストール確認
4. `toto-predictor train --seasons 2024,2025 --cv 5` — 再学習、Brier Score < 0.20確認
5. `toto-predictor predict --round 1607 --matches "横浜FM:町田,長崎:広島"` — **予測が「1点」に集中せず分散**することを確認
6. `toto-predictor scrape --round 1607` — Playwrightで投票率取得を確認
7. `toto-predictor strategy --round 1607 --tickets` — 本命/対抗/穴チケットが生成されることを確認
8. レポートでEV比較テーブル・逆張り機会が表示されることを確認
