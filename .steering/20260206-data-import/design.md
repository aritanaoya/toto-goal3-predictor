# 設計書: Wyscoutデータインポート

## 実装アプローチ

### 使用コマンド
```bash
toto-predictor import --dir data/wyscout/[年] --season [年]
```

### データフロー
```
Wyscout Excel → DataLoader → SQLite (data/processed/toto_predictor.db)
```

### 処理内容
1. 指定ディレクトリ内のExcelファイルを検索
2. 各ファイルを読み込み、試合データを抽出
3. チーム情報と試合統計をデータベースに保存

## 技術的考慮事項

### 警告の扱い
- PK戦や延長戦の試合（`(P)`, `(E)`表記）は解析スキップ
- リーグ戦のみ対象とするため、カップ戦データは除外される

### データベース
- SQLite: `data/processed/toto_predictor.db`
- 既存データとの重複は自動スキップ
