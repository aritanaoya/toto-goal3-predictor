"""チケット推奨データモデル

このモジュールは、toto GOAL3のチケット購入推奨を表すデータクラスを定義します。
1枚のチケット（12チーム分の選択）と、その期待値を格納します。
"""

from dataclasses import dataclass, field
from datetime import datetime
from functools import reduce
from typing import Any, Literal, Self
from uuid import uuid4

from .recommendation import TotoCategory

TicketType = Literal["本命", "対抗", "穴"]


@dataclass
class TeamPick:
    """1チームの選択を表すデータクラス

    Attributes:
        team: チーム名
        category: 選択カテゴリ（"0", "1", "2", "3+"）
        model_prob: モデル予測確率
        vote_rate: 投票率
        ev_contribution: EV貢献度
        is_contrarian: 逆張り選択かどうか
        match_index: 試合番号（1-3、0は未設定）
        opponent: 対戦相手チーム名
        is_home: ホームかどうか
        all_probs: 全カテゴリの確率辞書（{"0": p0, "1": p1, "2": p2, "3+": p3}）
    """

    team: str
    category: TotoCategory
    model_prob: float
    vote_rate: float
    ev_contribution: float = 0.0
    is_contrarian: bool = False
    match_index: int = 0
    opponent: str = ""
    is_home: bool = True
    all_probs: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換"""
        return {
            "team": self.team,
            "category": self.category,
            "model_prob": self.model_prob,
            "vote_rate": self.vote_rate,
            "ev_contribution": self.ev_contribution,
            "is_contrarian": self.is_contrarian,
            "match_index": self.match_index,
            "opponent": self.opponent,
            "is_home": self.is_home,
            "all_probs": self.all_probs,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """辞書からTeamPickオブジェクトを生成"""
        return cls(
            team=data["team"],
            category=data["category"],
            model_prob=data["model_prob"],
            vote_rate=data["vote_rate"],
            ev_contribution=data.get("ev_contribution", 0.0),
            is_contrarian=data.get("is_contrarian", False),
            match_index=data.get("match_index", 0),
            opponent=data.get("opponent", ""),
            is_home=data.get("is_home", True),
            all_probs=data.get("all_probs", {}),
        )


# toto GOAL3のチケット1枚あたりの金額
TICKET_COST = 200

# パリミュチュエル方式の払戻率
PAYOUT_RATE = 0.49


@dataclass
class TicketRecommendation:
    """1枚のチケット全体を表すデータクラス

    Attributes:
        id: チケットの一意識別子
        ticket_type: チケットタイプ（"本命", "対抗", "穴"）
        picks: 全チームの選択リスト
        cost: チケット金額（固定200円）
        created_at: 作成日時
    """

    ticket_type: TicketType
    picks: list[TeamPick] = field(default_factory=list)
    cost: int = TICKET_COST
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def ticket_prob(self) -> float:
        """全チーム的中確率の積

        Returns:
            チケット全体の的中確率
        """
        if not self.picks:
            return 0.0
        return reduce(lambda acc, p: acc * p.model_prob, self.picks, 1.0)

    @property
    def ticket_vote_share(self) -> float:
        """投票率の積

        Returns:
            チケットの投票率シェア
        """
        if not self.picks:
            return 0.0
        return reduce(lambda acc, p: acc * p.vote_rate, self.picks, 1.0)

    @property
    def estimated_payout(self) -> float:
        """推定払戻額

        パリミュチュエル方式: PAYOUT_RATE / ticket_vote_share × cost

        Returns:
            推定払戻額（円）
        """
        vote_share = self.ticket_vote_share
        if vote_share <= 0:
            return 0.0
        return PAYOUT_RATE / vote_share * self.cost

    @property
    def estimated_ev(self) -> float:
        """推定期待値

        ticket_prob × estimated_payout - cost

        Returns:
            推定期待値（円）
        """
        return self.ticket_prob * self.estimated_payout - self.cost

    @property
    def contrarian_count(self) -> int:
        """逆張り選択の数"""
        return sum(1 for p in self.picks if p.is_contrarian)

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換"""
        return {
            "id": self.id,
            "ticket_type": self.ticket_type,
            "picks": [p.to_dict() for p in self.picks],
            "cost": self.cost,
            "ticket_prob": self.ticket_prob,
            "ticket_vote_share": self.ticket_vote_share,
            "estimated_payout": self.estimated_payout,
            "estimated_ev": self.estimated_ev,
            "contrarian_count": self.contrarian_count,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """辞書からTicketRecommendationオブジェクトを生成"""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            id=data.get("id", str(uuid4())),
            ticket_type=data["ticket_type"],
            picks=[TeamPick.from_dict(p) for p in data.get("picks", [])],
            cost=data.get("cost", TICKET_COST),
            created_at=created_at or datetime.now(),
        )

    def get_summary(self) -> str:
        """チケットサマリーを取得"""
        return (
            f"[{self.ticket_type}] "
            f"的中率={self.ticket_prob:.2e}, "
            f"推定払戻=¥{self.estimated_payout:,.0f}, "
            f"EV=¥{self.estimated_ev:,.0f}"
        )
