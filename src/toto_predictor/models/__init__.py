"""データモデルモジュール"""

from .exceptions import (
    DatabaseError,
    DataError,
    DataFormatError,
    DataNotFoundError,
    ModelError,
    ModelNotTrainedError,
    NetworkError,
    ParseError,
    PredictionError,
    ScrapingError,
    TotoPredictorError,
    ValidationError,
)
from .match import Match
from .prediction import Prediction
from .recommendation import Recommendation
from .team_features import TeamFeatures
from .team_stats import TeamStats
from .vote_rate import VoteRate

__all__ = [
    # 例外クラス
    "TotoPredictorError",
    "DataError",
    "DataNotFoundError",
    "DataFormatError",
    "DatabaseError",
    "ModelError",
    "ModelNotTrainedError",
    "PredictionError",
    "ScrapingError",
    "NetworkError",
    "ParseError",
    "ValidationError",
    # データモデル
    "Match",
    "TeamStats",
    "TeamFeatures",
    "Prediction",
    "VoteRate",
    "Recommendation",
]
