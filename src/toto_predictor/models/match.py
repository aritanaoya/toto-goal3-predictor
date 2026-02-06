"""試合データモデル

このモジュールは、試合データを表すデータクラスを定義します。
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Self
from uuid import uuid4

from .exceptions import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class Match:
    """試合データを表すデータクラス

    Attributes:
        id: 試合の一意識別子（UUID）
        date: 試合日
        season: シーズン年（例: 2024, 2025）
        competition: 大会名（例: Japan. J1 League）
        home_team: ホームチーム名
        away_team: アウェイチーム名
        home_goals: ホームチーム得点（試合前はNone）
        away_goals: アウェイチーム得点（試合前はNone）
        duration: 試合時間（分）
        created_at: レコード作成日時
    """

    date: datetime
    season: int
    competition: str
    home_team: str
    away_team: str
    home_goals: int | None = None
    away_goals: int | None = None
    duration: int = 90
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """データクラス生成後のバリデーション"""
        self._validate()

    def _validate(self) -> None:
        """フィールドのバリデーションを実行

        Raises:
            ValidationError: バリデーションに失敗した場合
        """
        # 日付バリデーション（未来の試合も予測対象として許可）
        if self.date > datetime.now():
            logger.debug(f"未来の試合が登録されました: {self.date.isoformat()}")

        # シーズンバリデーション
        if not (2020 <= self.season <= 2030):
            raise ValidationError(
                "season", self.season, "シーズンは2020-2030の範囲で指定してください"
            )

        # 得点バリデーション
        if self.home_goals is not None and self.home_goals < 0:
            raise ValidationError(
                "home_goals", self.home_goals, "得点は0以上の整数で指定してください"
            )
        if self.away_goals is not None and self.away_goals < 0:
            raise ValidationError(
                "away_goals", self.away_goals, "得点は0以上の整数で指定してください"
            )

        # チーム名バリデーション
        if not self.home_team or not self.home_team.strip():
            raise ValidationError("home_team", self.home_team, "ホームチーム名は必須です")
        if not self.away_team or not self.away_team.strip():
            raise ValidationError("away_team", self.away_team, "アウェイチーム名は必須です")

        # 試合時間バリデーション
        if self.duration < 0:
            raise ValidationError("duration", self.duration, "試合時間は0以上で指定してください")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """辞書からMatchオブジェクトを生成

        Args:
            data: 試合データを含む辞書

        Returns:
            Matchオブジェクト
        """
        # 日付の変換
        date_val = data.get("date")
        if isinstance(date_val, str):
            date_parsed = datetime.fromisoformat(date_val)
        elif isinstance(date_val, datetime):
            date_parsed = date_val
        else:
            date_parsed = datetime.now()

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            id=data.get("id", str(uuid4())),
            date=date_parsed,
            season=data["season"],
            competition=data["competition"],
            home_team=data["home_team"],
            away_team=data["away_team"],
            home_goals=data.get("home_goals"),
            away_goals=data.get("away_goals"),
            duration=data.get("duration", 90),
            created_at=created_at or datetime.now(),
        )

    def to_dict(self) -> dict:
        """Matchオブジェクトを辞書に変換

        Returns:
            試合データを含む辞書
        """
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "season": self.season,
            "competition": self.competition,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "duration": self.duration,
            "created_at": self.created_at.isoformat(),
        }

    def is_finished(self) -> bool:
        """試合が終了しているかどうかを判定

        Returns:
            試合が終了していればTrue
        """
        return self.home_goals is not None and self.away_goals is not None

    def get_toto_category(self, team: str) -> str | None:
        """指定チームのtotoカテゴリを取得

        Args:
            team: チーム名

        Returns:
            totoカテゴリ（"0", "1", "2", "3+"）、試合未終了または該当チームなしの場合はNone
        """
        if not self.is_finished():
            return None

        goals: int | None = None
        if team == self.home_team:
            goals = self.home_goals
        elif team == self.away_team:
            goals = self.away_goals

        if goals is None:
            return None

        if goals == 0:
            return "0"
        elif goals == 1:
            return "1"
        elif goals == 2:
            return "2"
        else:
            return "3+"
