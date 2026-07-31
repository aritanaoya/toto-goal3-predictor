"""リポジトリモジュール"""

from .match_repository import MatchRepository
from .team_stats_repository import TeamStatsRepository

__all__ = [
    "MatchRepository",
    "TeamStatsRepository",
]
