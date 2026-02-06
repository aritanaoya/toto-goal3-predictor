"""予測結果データモデル

このモジュールは、モデルによる得点分布予測結果を表すデータクラスを定義します。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Self
from uuid import uuid4

from .exceptions import ValidationError


@dataclass
class Prediction:
    """予測結果を表すデータクラス

    Attributes:
        id: 予測の一意識別子（UUID）
        round_number: toto回号
        team: チーム名
        predicted_at: 予測日時

        # 得点確率分布
        prob_0: 0点の確率
        prob_1: 1点の確率
        prob_2: 2点の確率
        prob_3plus: 3点以上の確率

        # モデル別予測（参考）
        poisson_lambda: ポアソン分布のλ（期待得点）
        xgb_probs: XGBoostの生確率リスト
    """

    round_number: int
    team: str
    prob_0: float
    prob_1: float
    prob_2: float
    prob_3plus: float
    poisson_lambda: float = 0.0
    xgb_probs: list[float] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))
    predicted_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """データクラス生成後のバリデーション"""
        self._validate()

    def _validate(self) -> None:
        """フィールドのバリデーションを実行

        Raises:
            ValidationError: バリデーションに失敗した場合
        """
        # 確率の範囲チェック
        probs = [self.prob_0, self.prob_1, self.prob_2, self.prob_3plus]
        for i, prob in enumerate(probs):
            if not (0.0 <= prob <= 1.0):
                raise ValidationError(
                    f"prob_{i if i < 3 else '3plus'}",
                    prob,
                    "確率は0-100%の範囲で指定してください",
                )

        # 合計チェック（誤差許容）
        total = sum(probs)
        if not (0.99 <= total <= 1.01):
            raise ValidationError(
                "prob_total",
                total,
                f"予測確率の合計が100%になっていません: {total * 100:.1f}%",
            )

        # チーム名チェック
        if not self.team or not self.team.strip():
            raise ValidationError("team", self.team, "チーム名は必須です")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """辞書からPredictionオブジェクトを生成

        Args:
            data: 予測データを含む辞書

        Returns:
            Predictionオブジェクト
        """
        predicted_at = data.get("predicted_at")
        if isinstance(predicted_at, str):
            predicted_at = datetime.fromisoformat(predicted_at)

        return cls(
            id=data.get("id", str(uuid4())),
            round_number=data["round_number"],
            team=data["team"],
            predicted_at=predicted_at or datetime.now(),
            prob_0=data["prob_0"],
            prob_1=data["prob_1"],
            prob_2=data["prob_2"],
            prob_3plus=data["prob_3plus"],
            poisson_lambda=data.get("poisson_lambda", 0.0),
            xgb_probs=data.get("xgb_probs", []),
        )

    def to_dict(self) -> dict:
        """Predictionオブジェクトを辞書に変換

        Returns:
            予測データを含む辞書
        """
        return {
            "id": self.id,
            "round_number": self.round_number,
            "team": self.team,
            "predicted_at": self.predicted_at.isoformat(),
            "prob_0": self.prob_0,
            "prob_1": self.prob_1,
            "prob_2": self.prob_2,
            "prob_3plus": self.prob_3plus,
            "poisson_lambda": self.poisson_lambda,
            "xgb_probs": self.xgb_probs,
        }

    def get_most_likely_category(self) -> str:
        """最も確率が高いカテゴリを取得

        Returns:
            totoカテゴリ（"0", "1", "2", "3+"）
        """
        probs = {
            "0": self.prob_0,
            "1": self.prob_1,
            "2": self.prob_2,
            "3+": self.prob_3plus,
        }
        return max(probs, key=probs.get)  # type: ignore

    def get_prob_for_category(self, category: str) -> float:
        """指定カテゴリの確率を取得

        Args:
            category: totoカテゴリ（"0", "1", "2", "3+"）

        Returns:
            確率（0.0-1.0）
        """
        mapping = {
            "0": self.prob_0,
            "1": self.prob_1,
            "2": self.prob_2,
            "3+": self.prob_3plus,
        }
        return mapping.get(category, 0.0)

    def get_all_probs(self) -> dict[str, float]:
        """全カテゴリの確率を取得

        Returns:
            カテゴリと確率の辞書
        """
        return {
            "0": self.prob_0,
            "1": self.prob_1,
            "2": self.prob_2,
            "3+": self.prob_3plus,
        }

    @property
    def expected_goals(self) -> float:
        """期待得点を計算

        Returns:
            期待得点
        """
        # 簡易計算: 0*p0 + 1*p1 + 2*p2 + 3.5*p3+ (3点以上は平均3.5と仮定)
        return 0 * self.prob_0 + 1 * self.prob_1 + 2 * self.prob_2 + 3.5 * self.prob_3plus
