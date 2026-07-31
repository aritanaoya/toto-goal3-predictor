# ワークフロー図 (Workflow Diagrams)

## 全体ワークフロー概要

```mermaid
flowchart TB
    subgraph Weekly["週次運用フロー"]
        direction TB
        A[データ準備] --> B[特徴量計算]
        B --> C[予測実行]
        C --> D[投票率取得]
        D --> E[戦略計算]
        E --> F[購入判断]
    end

    style A fill:#e1f5fe
    style B fill:#e1f5fe
    style C fill:#fff3e0
    style D fill:#fff3e0
    style E fill:#e8f5e9
    style F fill:#e8f5e9
```

---

## 1. 週次パイプライン全体フロー

```mermaid
flowchart TD
    Start([開始: toto-predictor pipeline]) --> Import

    subgraph Import["Phase 1: データインポート"]
        Import1[Wyscout Excelファイル確認]
        Import2[DataLoader.load_directory]
        Import3[SQLite DBに保存]
        Import1 --> Import2 --> Import3
    end

    Import --> Feature

    subgraph Feature["Phase 2: 特徴量計算"]
        Feature1[対象チーム特定]
        Feature2[FeatureEngine.calculate_features]
        Feature3[ウィンドウ統計計算<br/>5/10/20試合]
        Feature4[派生特徴量生成]
        Feature1 --> Feature2 --> Feature3 --> Feature4
    end

    Feature --> Model

    subgraph Model["Phase 3: モデル予測"]
        Model1{モデル存在?}
        Model2[ModelEnsemble.load]
        Model3[ModelEnsemble.train]
        Model4[ModelEnsemble.predict]
        Model5[確率分布出力<br/>0点/1点/2点/3点以上]
        Model1 -->|Yes| Model2
        Model1 -->|No| Model3
        Model2 --> Model4
        Model3 --> Model4
        Model4 --> Model5
    end

    Model --> Scrape

    subgraph Scrape["Phase 4: 投票率取得"]
        Scrape1[VoteScraper.fetch]
        Scrape2[totoONE HTML解析]
        Scrape3[6チーム×4カテゴリ<br/>投票率取得]
        Scrape1 --> Scrape2 --> Scrape3
    end

    Scrape --> Strategy

    subgraph Strategy["Phase 5: 戦略計算"]
        Strategy1[バリュースコア計算]
        Strategy2[Kelly比率計算]
        Strategy3[購入推奨生成]
        Strategy4[Markdownレポート出力]
        Strategy1 --> Strategy2 --> Strategy3 --> Strategy4
    end

    Strategy --> End([完了: レポート出力])

    style Start fill:#4caf50,color:#fff
    style End fill:#4caf50,color:#fff
```

---

## 2. データインポートフロー

```mermaid
flowchart TD
    Start([import開始]) --> CheckDir{ディレクトリ存在?}

    CheckDir -->|No| Error1[エラー: ディレクトリなし]
    CheckDir -->|Yes| ScanFiles[Excelファイルスキャン]

    ScanFiles --> HasFiles{ファイル存在?}
    HasFiles -->|No| Error2[エラー: ファイルなし]
    HasFiles -->|Yes| Loop

    subgraph Loop["各ファイル処理"]
        ReadExcel[Excel読み込み]
        ValidateFormat{形式チェック}
        ValidateCols{必須カラム?}
        ParseData[データパース]
        CheckDup{重複チェック}
        SaveDB[DB保存]
        LogSkip[スキップログ出力]

        ReadExcel --> ValidateFormat
        ValidateFormat -->|不正| LogSkip
        ValidateFormat -->|OK| ValidateCols
        ValidateCols -->|欠落| LogSkip
        ValidateCols -->|OK| ParseData
        ParseData --> CheckDup
        CheckDup -->|重複| LogSkip
        CheckDup -->|新規| SaveDB
    end

    Loop --> Summary[取り込み結果サマリー出力]
    Summary --> End([完了])

    Error1 --> End
    Error2 --> End

    style Start fill:#2196f3,color:#fff
    style End fill:#2196f3,color:#fff
    style Error1 fill:#f44336,color:#fff
    style Error2 fill:#f44336,color:#fff
```

---

## 3. 特徴量計算フロー

```mermaid
flowchart TD
    Start([特徴量計算開始]) --> GetMatches[チームの試合履歴取得]

    GetMatches --> CheckCount{試合数 >= 10?}
    CheckCount -->|No| Error[エラー: データ不足]
    CheckCount -->|Yes| CalcBasic

    subgraph CalcBasic["基本統計計算"]
        Calc1[Goals平均/標準偏差]
        Calc2[xG平均/標準偏差]
        Calc3[Shots on target平均]
        Calc4[Possession平均]
        Calc5[PPDA平均]
        Calc1 --> Calc2 --> Calc3 --> Calc4 --> Calc5
    end

    CalcBasic --> CalcWindow

    subgraph CalcWindow["ウィンドウ統計"]
        Win5[直近5試合統計]
        Win10[直近10試合統計]
        Win20[直近20試合統計]
        Trend[トレンド計算<br/>直近5 - 直近20]
        Win5 --> Trend
        Win10 --> Trend
        Win20 --> Trend
    end

    CalcWindow --> CalcDerived

    subgraph CalcDerived["派生特徴量"]
        Der1[shot_conversion<br/>= goals / shots]
        Der2[xg_overperformance<br/>= goals - xG]
        Der3[counter_ratio]
        Der4[対戦相手調整値]
        Der1 --> Der2 --> Der3 --> Der4
    end

    CalcDerived --> Output[TeamFeatures出力]
    Output --> End([完了])

    Error --> End

    style Start fill:#9c27b0,color:#fff
    style End fill:#9c27b0,color:#fff
    style Error fill:#f44336,color:#fff
```

---

## 4. モデル予測フロー

```mermaid
flowchart TD
    Start([予測開始]) --> LoadModel{モデル読み込み}

    LoadModel -->|失敗| Train[モデル学習]
    LoadModel -->|成功| Predict

    Train --> SaveModel[モデル保存]
    SaveModel --> Predict

    subgraph Predict["予測実行"]
        direction TB
        P1[Poisson Regression<br/>λ予測]
        P2[XGBoost<br/>分類予測]

        P1 --> P1a[ポアソン分布から<br/>カテゴリ確率計算]
        P2 --> P2a[6クラス確率を<br/>4カテゴリに変換]

        P1a --> Ensemble
        P2a --> Ensemble

        Ensemble[アンサンブル<br/>Poisson 30% + XGB 70%]
        Ensemble --> Calibrate[キャリブレーション<br/>Isotonic Regression]
    end

    Calibrate --> Output

    subgraph Output["出力"]
        Out1[prob_0: 0点確率]
        Out2[prob_1: 1点確率]
        Out3[prob_2: 2点確率]
        Out4[prob_3plus: 3点以上確率]
    end

    Output --> Validate{合計 ≈ 100%?}
    Validate -->|No| Error[エラー: 検証失敗]
    Validate -->|Yes| End([完了: Prediction出力])

    style Start fill:#ff9800,color:#fff
    style End fill:#ff9800,color:#fff
    style Error fill:#f44336,color:#fff
```

---

## 5. 投票率取得フロー

```mermaid
flowchart TD
    Start([スクレイピング開始]) --> BuildURL[URL構築<br/>totoone.jp/prediction]

    BuildURL --> Fetch[HTTP GET]

    Fetch --> Response{レスポンス}
    Response -->|成功| Parse[HTML解析]
    Response -->|5xx| Retry{リトライ可能?}
    Response -->|4xx| Error1[エラー: クライアントエラー]
    Response -->|Timeout| Retry

    Retry -->|残り > 0| Wait[指数バックオフ待機<br/>1s → 2s → 4s]
    Wait --> Fetch
    Retry -->|残り = 0| Fallback

    Fallback{前回データあり?}
    Fallback -->|Yes| UseCached[前回データを使用<br/>警告出力]
    Fallback -->|No| Error2[エラー: 取得失敗]

    Parse --> Extract[投票率抽出<br/>6チーム × 4カテゴリ]
    Extract --> ValidateSum{合計 ≈ 100%?}

    ValidateSum -->|No| Error3[エラー: データ不正]
    ValidateSum -->|Yes| Save[DB/JSON保存]

    Save --> End([完了: VoteRate出力])
    UseCached --> End
    Error1 --> End
    Error2 --> End
    Error3 --> End

    style Start fill:#00bcd4,color:#fff
    style End fill:#00bcd4,color:#fff
    style Error1 fill:#f44336,color:#fff
    style Error2 fill:#f44336,color:#fff
    style Error3 fill:#f44336,color:#fff
```

---

## 6. バリュースコア計算・購入判断フロー

```mermaid
flowchart TD
    Start([戦略計算開始]) --> Input[予測結果 + 投票率取得]

    Input --> CalcValue

    subgraph CalcValue["バリュースコア計算"]
        direction TB
        CV1["各チーム × 各カテゴリ"]
        CV2["ValueScore = モデル確率 / 投票率"]
        CV3["MIN_RATE = 0.01 でゼロ除算防止"]
        CV1 --> CV2 --> CV3
    end

    CalcValue --> CalcKelly

    subgraph CalcKelly["Kelly比率計算"]
        direction TB
        K1["推定オッズ = 1 / 投票率"]
        K2["エッジ = 確率 × オッズ - 1"]
        K3["フルKelly = エッジ / (オッズ - 1)"]
        K4["推奨比率 = Kelly × 0.25<br/>最大10%"]
        K1 --> K2 --> K3 --> K4
    end

    CalcKelly --> Decide

    subgraph Decide["購入判断マトリクス"]
        D1{モデル確率}

        D1 -->|>= 30%| D2a{ValueScore}
        D1 -->|15-30%| D2b{ValueScore}
        D1 -->|< 15%| D2c{ValueScore}

        D2a -->|>= 1.5| A1["必買"]
        D2a -->|1.0-1.5| A2["買い"]
        D2a -->|< 1.0| A3["慎重"]

        D2b -->|>= 1.5| A4["買い"]
        D2b -->|1.0-1.5| A5["検討"]
        D2b -->|< 1.0| A6["スキップ"]

        D2c -->|>= 1.5| A7["検討"]
        D2c -->|< 1.5| A8["スキップ"]
    end

    Decide --> GenerateReport

    subgraph GenerateReport["レポート生成"]
        R1["推奨購入リスト<br/>バリュー >= 1.3"]
        R2["検討候補リスト<br/>バリュー 1.0-1.3"]
        R3["スキップリスト<br/>バリュー < 1.0"]
        R4["Markdownファイル出力"]
        R1 --> R4
        R2 --> R4
        R3 --> R4
    end

    GenerateReport --> End([完了: Recommendation出力])

    style Start fill:#4caf50,color:#fff
    style End fill:#4caf50,color:#fff
    style A1 fill:#c62828,color:#fff
    style A2 fill:#ef6c00,color:#fff
    style A4 fill:#ef6c00,color:#fff
    style A5 fill:#fbc02d,color:#000
    style A7 fill:#fbc02d,color:#000
```

---

## 7. エラーハンドリングフロー

```mermaid
flowchart TD
    Start([エラー発生]) --> Classify{エラー分類}

    Classify -->|DataError| DataErr
    Classify -->|ModelError| ModelErr
    Classify -->|ScrapingError| ScrapeErr
    Classify -->|ValidationError| ValidErr

    subgraph DataErr["データエラー処理"]
        DE1[DataNotFoundError]
        DE2[DataFormatError]
        DE3[DatabaseError]

        DE1 --> DE1a["ヒント: import実行を促す"]
        DE2 --> DE2a["警告: スキップして継続"]
        DE3 --> DE3a["エラー: 処理中断"]
    end

    subgraph ModelErr["モデルエラー処理"]
        ME1[ModelNotTrainedError]
        ME2[PredictionError]

        ME1 --> ME1a["ヒント: train実行を促す"]
        ME2 --> ME2a["エラー: 詳細ログ出力"]
    end

    subgraph ScrapeErr["スクレイピングエラー処理"]
        SE1[NetworkError]
        SE2[ParseError]

        SE1 --> SE1a["リトライ: 指数バックオフ"]
        SE2 --> SE2a["アラート: サイト構造変更の可能性"]
    end

    subgraph ValidErr["バリデーションエラー処理"]
        VE1["フィールド名 + 値を表示"]
        VE2["修正方法のヒントを表示"]
        VE1 --> VE2
    end

    DataErr --> Log
    ModelErr --> Log
    ScrapeErr --> Log
    ValidErr --> Log

    Log[ログファイル出力<br/>logs/toto-predictor.log]
    Log --> Display[CLI表示<br/>Rich Panel]
    Display --> End([処理終了])

    style Start fill:#f44336,color:#fff
    style End fill:#f44336,color:#fff
```

---

## 8. CLIコマンド実行フロー

```mermaid
flowchart LR
    subgraph Commands["CLIコマンド"]
        direction TB
        C1["toto-predictor import"]
        C2["toto-predictor train"]
        C3["toto-predictor predict"]
        C4["toto-predictor scrape"]
        C5["toto-predictor strategy"]
        C6["toto-predictor pipeline"]
    end

    subgraph Services["サービス呼び出し"]
        direction TB
        S1[DataLoader]
        S2[FeatureEngine<br/>+ ModelEnsemble]
        S3[FeatureEngine<br/>+ ModelEnsemble]
        S4[VoteScraper]
        S5[StrategyEngine]
        S6[全サービス連携]
    end

    subgraph Output["出力"]
        direction TB
        O1[取り込み結果サマリー]
        O2[学習結果メトリクス]
        O3[予測確率テーブル]
        O4[投票率データ]
        O5[購入推奨レポート]
        O6[レポート + ログ]
    end

    C1 --> S1 --> O1
    C2 --> S2 --> O2
    C3 --> S3 --> O3
    C4 --> S4 --> O4
    C5 --> S5 --> O5
    C6 --> S6 --> O6

    style C6 fill:#4caf50,color:#fff
    style O6 fill:#4caf50,color:#fff
```

---

## 9. データの流れ（時系列）

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant CLI as CLI
    participant DL as DataLoader
    participant FE as FeatureEngine
    participant ME as ModelEnsemble
    participant VS as VoteScraper
    participant SE as StrategyEngine
    participant DB as SQLite
    participant Web as totoONE

    User->>CLI: toto-predictor pipeline --round 1607

    rect rgb(225, 245, 254)
        Note over CLI,DB: Phase 1: データインポート
        CLI->>DL: load_directory()
        DL->>DB: 試合データ保存
        DB-->>DL: 保存完了
        DL-->>CLI: 追加件数
    end

    rect rgb(255, 243, 224)
        Note over CLI,ME: Phase 2-3: 特徴量計算・予測
        CLI->>FE: calculate_features(team)
        FE->>DB: 試合履歴取得
        DB-->>FE: 試合データ
        FE-->>CLI: TeamFeatures

        CLI->>ME: predict(features)
        ME-->>CLI: Prediction(確率分布)
    end

    rect rgb(232, 245, 233)
        Note over CLI,Web: Phase 4: 投票率取得
        CLI->>VS: fetch(round_number)
        VS->>Web: HTTP GET
        Web-->>VS: HTML
        VS->>DB: 投票率保存
        VS-->>CLI: VoteRate[]
    end

    rect rgb(248, 187, 208)
        Note over CLI,SE: Phase 5: 戦略計算
        CLI->>SE: calculate_value_scores()
        SE-->>CLI: Recommendation[]

        CLI->>SE: generate_report()
        SE-->>CLI: レポート生成完了
    end

    CLI-->>User: 購入推奨レポート表示
```

---

## 関連ドキュメント

- [機能設計書](functional-design.md) - データモデル、コンポーネント設計
- [アーキテクチャ設計書](architecture.md) - システム構成、技術スタック
- [開発ガイドライン](development-guidelines.md) - コーディング規約、テスト方針
