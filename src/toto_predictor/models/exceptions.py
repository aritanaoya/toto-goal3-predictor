"""カスタム例外クラス群

このモジュールは、toto-predictorアプリケーション全体で使用される
カスタム例外クラスを定義します。
"""

from typing import Any


class TotoPredictorError(Exception):
    """基底例外クラス

    すべてのアプリケーション固有の例外はこのクラスを継承します。

    Attributes:
        message: エラーメッセージ
        details: エラーの詳細情報を含む辞書
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (詳細: {self.details})"
        return self.message


class DataError(TotoPredictorError):
    """データ関連エラーの基底クラス"""

    pass


class DataNotFoundError(DataError):
    """データが見つからない場合の例外

    指定されたファイル、チーム、または試合データが存在しない場合に発生します。
    """

    pass


class DataFormatError(DataError):
    """データ形式が不正な場合の例外

    Excelファイルの形式エラー、必須カラム欠落、データ型エラーなどで発生します。
    """

    pass


class DatabaseError(DataError):
    """データベース操作エラー

    SQLite接続エラー、クエリエラー、トランザクションエラーなどで発生します。
    """

    pass


class ModelError(TotoPredictorError):
    """モデル関連エラーの基底クラス"""

    pass


class ModelNotTrainedError(ModelError):
    """モデルが学習されていない場合の例外

    予測実行時にモデルファイルが存在しない場合に発生します。
    """

    pass


class PredictionError(ModelError):
    """予測実行エラー

    予測処理中に発生したエラーを表します。
    """

    pass


class ScrapingError(TotoPredictorError):
    """スクレイピング関連エラーの基底クラス"""

    pass


class NetworkError(ScrapingError):
    """ネットワークエラー

    タイムアウト、接続エラー、HTTPエラーなどで発生します。
    """

    pass


class ParseError(ScrapingError):
    """HTML解析エラー

    サイト構造変更、予期しないHTML形式などで発生します。
    """

    pass


class ValidationError(TotoPredictorError):
    """入力検証エラー

    データモデルのバリデーション失敗時に発生します。

    Attributes:
        field: バリデーションに失敗したフィールド名
        value: バリデーションに失敗した値
    """

    def __init__(self, field: str, value: Any, message: str) -> None:
        self.field = field
        self.value = value
        super().__init__(message, {"field": field, "value": value})
