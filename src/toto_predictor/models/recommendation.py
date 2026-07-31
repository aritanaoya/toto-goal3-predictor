"""購入推奨データモデル

このモジュールは、バリュースコアに基づく購入推奨を表すデータクラスを定義します。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Self
from uuid import uuid4

TotoCategory = Literal["0", "1", "2", "3+"]
ActionType = Literal["必買", "買い", "検討", "慎重", "スキップ"]
ConfidenceLevel = Literal["high", "medium", "low"]


@dataclass
class Recommendation:
    """購入推奨を表すデータクラス

    モデル予測と投票率を比較し、バリューベットを特定した結果を格納します。

    Attributes:
        id: 推奨の一意識別子（UUID）
        round_number: toto回号
        team: チーム名
        category: totoカテゴリ（"0", "1", "2", "3+"）

        # スコア
        model_prob: モデル予測確率
        vote_rate: 公衆投票率
        value_score: バリュースコア（model_prob / vote_rate）

        # 推奨
        action: アクション（"必買", "買い", "検討", "慎重", "スキップ"）
        kelly_fraction: ケリー基準による推奨ベット比率
        confidence: 信頼度（"high", "medium", "low"）

        created_at: レコード作成日時
    """

    round_number: int
    team: str
    category: TotoCategory
    model_prob: float
    vote_rate: float
    value_score: float
    action: ActionType
    kelly_fraction: float = 0.0
    confidence: ConfidenceLevel = "medium"
    ev: float = 0.0
    contrarian_score: float = 0.0
    is_best_ev_for_team: bool = False
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """辞書からRecommendationオブジェクトを生成

        Args:
            data: 推奨データを含む辞書

        Returns:
            Recommendationオブジェクト
        """
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            id=data.get("id", str(uuid4())),
            round_number=data["round_number"],
            team=data["team"],
            category=data["category"],
            model_prob=data["model_prob"],
            vote_rate=data["vote_rate"],
            value_score=data["value_score"],
            action=data["action"],
            kelly_fraction=data.get("kelly_fraction", 0.0),
            confidence=data.get("confidence", "medium"),
            ev=data.get("ev", 0.0),
            contrarian_score=data.get("contrarian_score", 0.0),
            is_best_ev_for_team=data.get("is_best_ev_for_team", False),
            created_at=created_at or datetime.now(),
        )

    def to_dict(self) -> dict:
        """Recommendationオブジェクトを辞書に変換

        Returns:
            推奨データを含む辞書
        """
        return {
            "id": self.id,
            "round_number": self.round_number,
            "team": self.team,
            "category": self.category,
            "model_prob": self.model_prob,
            "vote_rate": self.vote_rate,
            "value_score": self.value_score,
            "action": self.action,
            "kelly_fraction": self.kelly_fraction,
            "confidence": self.confidence,
            "ev": self.ev,
            "contrarian_score": self.contrarian_score,
            "is_best_ev_for_team": self.is_best_ev_for_team,
            "created_at": self.created_at.isoformat(),
        }

    @property
    def is_value_bet(self) -> bool:
        """バリューベットかどうか判定

        Returns:
            バリュースコアが1.0以上ならTrue
        """
        return self.value_score >= 1.0

    @property
    def is_recommended(self) -> bool:
        """購入推奨かどうか判定

        Returns:
            アクションが「必買」「買い」「検討」のいずれかならTrue
        """
        return self.action in ("必買", "買い", "検討")

    @property
    def expected_value(self) -> float:
        """期待値を計算

        toto GOAL3はパリミュチュエル方式のため、簡易的な期待値を計算。
        実際の払戻率は約50%程度を想定。

        Returns:
            期待値（1.0以上が理論上プラス）
        """
        if self.vote_rate <= 0:
            return 0.0
        # 簡易オッズ = 1 / 投票率 * 払戻率(0.5想定)
        estimated_odds = (1.0 / self.vote_rate) * 0.5
        return self.model_prob * estimated_odds

    def get_summary(self) -> str:
        """推奨サマリーを取得

        Returns:
            推奨内容の文字列
        """
        return (
            f"{self.team} {self.category}点: "
            f"モデル{self.model_prob * 100:.1f}% vs 投票{self.vote_rate * 100:.1f}% "
            f"(バリュー{self.value_score:.2f}) → {self.action}"
        )
