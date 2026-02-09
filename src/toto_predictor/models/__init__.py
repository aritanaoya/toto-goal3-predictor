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
from .match_schedule import MatchPair, MatchSchedule
from .matchup_features import MatchupFeatures
from .prediction import Prediction
from .recommendation import Recommendation
from .team_features import TeamFeatures
from .team_names import get_japanese_name
from .team_stats import TeamStats
from .ticket import TeamPick, TicketRecommendation
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
    "MatchPair",
    "MatchSchedule",
    "TeamStats",
    "TeamFeatures",
    "MatchupFeatures",
    "Prediction",
    "VoteRate",
    "Recommendation",
    "TeamPick",
    "TicketRecommendation",
    "get_japanese_name",
]
