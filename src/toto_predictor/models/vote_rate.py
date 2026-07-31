"""投票率データモデル

このモジュールは、totoONEから取得した投票率データを表すデータクラスを定義します。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Self
from uuid import uuid4

from .exceptions import ValidationError


@dataclass
class VoteRate:
    """投票率データを表すデータクラス

    totoONEから取得した公衆投票率を格納します。

    Attributes:
        id: 投票率データの一意識別子（UUID）
        round_number: toto回号
        team: チーム名
        fetched_at: 取得日時

        # 投票率（0.0-1.0）
        vote_0: 0点の投票率
        vote_1: 1点の投票率
        vote_2: 2点の投票率
        vote_3plus: 3点以上の投票率
    """

    round_number: int
    team: str
    vote_0: float
    vote_1: float
    vote_2: float
    vote_3plus: float
    id: str = field(default_factory=lambda: str(uuid4()))
    fetched_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """データクラス生成後のバリデーション"""
        self._validate()

    def _validate(self) -> None:
        """フィールドのバリデーションを実行

        Raises:
            ValidationError: バリデーションに失敗した場合
        """
        # 投票率の範囲チェック
        rates = [self.vote_0, self.vote_1, self.vote_2, self.vote_3plus]
        for i, rate in enumerate(rates):
            if not (0.0 <= rate <= 1.0):
                raise ValidationError(
                    f"vote_{i if i < 3 else '3plus'}",
                    rate,
                    "投票率は0-100%の範囲で指定してください",
                )

        # 合計チェック（5%の誤差許容）
        total = sum(rates)
        if not (0.95 <= total <= 1.05):
            raise ValidationError(
                "vote_total",
                total,
                f"投票率の合計が100%になっていません: {total * 100:.1f}%",
            )

        # チーム名チェック
        if not self.team or not self.team.strip():
            raise ValidationError("team", self.team, "チーム名は必須です")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """辞書からVoteRateオブジェクトを生成

        Args:
            data: 投票率データを含む辞書

        Returns:
            VoteRateオブジェクト
        """
        fetched_at = data.get("fetched_at")
        if isinstance(fetched_at, str):
            fetched_at = datetime.fromisoformat(fetched_at)

        return cls(
            id=data.get("id", str(uuid4())),
            round_number=data["round_number"],
            team=data["team"],
            fetched_at=fetched_at or datetime.now(),
            vote_0=data["vote_0"],
            vote_1=data["vote_1"],
            vote_2=data["vote_2"],
            vote_3plus=data["vote_3plus"],
        )

    def to_dict(self) -> dict:
        """VoteRateオブジェクトを辞書に変換

        Returns:
            投票率データを含む辞書
        """
        return {
            "id": self.id,
            "round_number": self.round_number,
            "team": self.team,
            "fetched_at": self.fetched_at.isoformat(),
            "vote_0": self.vote_0,
            "vote_1": self.vote_1,
            "vote_2": self.vote_2,
            "vote_3plus": self.vote_3plus,
        }

    def get_rate_for_category(self, category: str) -> float:
        """指定カテゴリの投票率を取得

        Args:
            category: totoカテゴリ（"0", "1", "2", "3+"）

        Returns:
            投票率（0.0-1.0）
        """
        mapping = {
            "0": self.vote_0,
            "1": self.vote_1,
            "2": self.vote_2,
            "3+": self.vote_3plus,
        }
        return mapping.get(category, 0.0)

    def get_all_rates(self) -> dict[str, float]:
        """全カテゴリの投票率を取得

        Returns:
            カテゴリと投票率の辞書
        """
        return {
            "0": self.vote_0,
            "1": self.vote_1,
            "2": self.vote_2,
            "3+": self.vote_3plus,
        }

    def get_most_voted_category(self) -> str:
        """最も投票率が高いカテゴリを取得

        Returns:
            totoカテゴリ（"0", "1", "2", "3+"）
        """
        rates = self.get_all_rates()
        return max(rates, key=rates.get)  # type: ignore
