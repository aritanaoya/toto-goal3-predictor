"""チーム統計データモデル

このモジュールは、試合ごとのチーム統計データを表すデータクラスを定義します。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Self
from uuid import uuid4

from .exceptions import ValidationError


@dataclass
class TeamStats:
    """チーム統計データを表すデータクラス

    Wyscoutからエクスポートされた試合統計データを格納します。

    Attributes:
        id: 統計データの一意識別子（UUID）
        match_id: 試合ID（外部キー）
        team: チーム名
        is_home: ホームかどうか

        # 攻撃指標
        goals: 得点
        xg: 期待得点（Expected Goals）
        shots: シュート数
        shots_on_target: 枠内シュート数

        # チャンス創出
        possession: ボール支配率（%）
        passes: パス数
        passes_accurate: 成功パス数
        crosses: クロス数
        crosses_accurate: 成功クロス数
        pen_area_entries: ペナルティエリア侵入回数

        # 守備指標
        conceded_goals: 失点
        xg_against: 被期待得点
        shots_against: 被シュート数
        shots_against_on_target: 被枠内シュート数
        ppda: PPDA（Passes Per Defensive Action）- プレス強度指標
        interceptions: インターセプト数

        # その他
        fouls: ファウル数
        yellow_cards: イエローカード数
        red_cards: レッドカード数
        corners: コーナーキック数

        created_at: レコード作成日時
    """

    match_id: str
    team: str
    is_home: bool

    # 攻撃指標
    goals: int = 0
    xg: float = 0.0
    shots: int = 0
    shots_on_target: int = 0

    # チャンス創出
    possession: float = 50.0
    passes: int = 0
    passes_accurate: int = 0
    crosses: int = 0
    crosses_accurate: int = 0
    pen_area_entries: int = 0

    # 守備指標
    conceded_goals: int = 0
    xg_against: float = 0.0
    shots_against: int = 0
    shots_against_on_target: int = 0
    ppda: float = 10.0
    interceptions: int = 0

    # その他
    fouls: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    corners: int = 0

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
        # 得点バリデーション
        if self.goals < 0:
            raise ValidationError("goals", self.goals, "得点は0以上で指定してください")

        # xGバリデーション
        if self.xg < 0:
            raise ValidationError("xg", self.xg, "xGは0以上で指定してください")

        # ボール支配率バリデーション
        if not (0 <= self.possession <= 100):
            raise ValidationError(
                "possession", self.possession, "ボール支配率は0-100%の範囲で指定してください"
            )

        # シュートバリデーション
        if self.shots < 0:
            raise ValidationError("shots", self.shots, "シュート数は0以上で指定してください")
        if self.shots_on_target < 0:
            raise ValidationError(
                "shots_on_target",
                self.shots_on_target,
                "枠内シュート数は0以上で指定してください",
            )
        if self.shots_on_target > self.shots:
            raise ValidationError(
                "shots_on_target",
                self.shots_on_target,
                "枠内シュート数はシュート数を超えられません",
            )

        # PPDAバリデーション
        if self.ppda <= 0:
            raise ValidationError("ppda", self.ppda, "PPDAは正の値で指定してください")

        # チーム名バリデーション
        if not self.team or not self.team.strip():
            raise ValidationError("team", self.team, "チーム名は必須です")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """辞書からTeamStatsオブジェクトを生成

        Args:
            data: チーム統計データを含む辞書

        Returns:
            TeamStatsオブジェクト
        """
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            id=data.get("id", str(uuid4())),
            match_id=data["match_id"],
            team=data["team"],
            is_home=data["is_home"],
            goals=data.get("goals", 0),
            xg=data.get("xg", 0.0),
            shots=data.get("shots", 0),
            shots_on_target=data.get("shots_on_target", 0),
            possession=data.get("possession", 50.0),
            passes=data.get("passes", 0),
            passes_accurate=data.get("passes_accurate", 0),
            crosses=data.get("crosses", 0),
            crosses_accurate=data.get("crosses_accurate", 0),
            pen_area_entries=data.get("pen_area_entries", 0),
            conceded_goals=data.get("conceded_goals", 0),
            xg_against=data.get("xg_against", 0.0),
            shots_against=data.get("shots_against", 0),
            shots_against_on_target=data.get("shots_against_on_target", 0),
            ppda=data.get("ppda", 10.0),
            interceptions=data.get("interceptions", 0),
            fouls=data.get("fouls", 0),
            yellow_cards=data.get("yellow_cards", 0),
            red_cards=data.get("red_cards", 0),
            corners=data.get("corners", 0),
            created_at=created_at or datetime.now(),
        )

    def to_dict(self) -> dict:
        """TeamStatsオブジェクトを辞書に変換

        Returns:
            チーム統計データを含む辞書
        """
        return {
            "id": self.id,
            "match_id": self.match_id,
            "team": self.team,
            "is_home": self.is_home,
            "goals": self.goals,
            "xg": self.xg,
            "shots": self.shots,
            "shots_on_target": self.shots_on_target,
            "possession": self.possession,
            "passes": self.passes,
            "passes_accurate": self.passes_accurate,
            "crosses": self.crosses,
            "crosses_accurate": self.crosses_accurate,
            "pen_area_entries": self.pen_area_entries,
            "conceded_goals": self.conceded_goals,
            "xg_against": self.xg_against,
            "shots_against": self.shots_against,
            "shots_against_on_target": self.shots_against_on_target,
            "ppda": self.ppda,
            "interceptions": self.interceptions,
            "fouls": self.fouls,
            "yellow_cards": self.yellow_cards,
            "red_cards": self.red_cards,
            "corners": self.corners,
            "created_at": self.created_at.isoformat(),
        }

    @property
    def pass_accuracy(self) -> float:
        """パス成功率を計算

        Returns:
            パス成功率（0-100%）
        """
        if self.passes == 0:
            return 0.0
        return (self.passes_accurate / self.passes) * 100

    @property
    def shot_conversion(self) -> float:
        """シュート決定率を計算

        Returns:
            シュート決定率（ゴール数/シュート数）
        """
        if self.shots == 0:
            return 0.0
        return self.goals / self.shots

    @property
    def xg_overperformance(self) -> float:
        """xG超過パフォーマンスを計算

        Returns:
            実得点 - xG（正の値はxGを上回る実績）
        """
        return self.goals - self.xg

    def get_toto_category(self) -> str:
        """totoカテゴリを取得

        Returns:
            totoカテゴリ（"0", "1", "2", "3+"）
        """
        if self.goals == 0:
            return "0"
        elif self.goals == 1:
            return "1"
        elif self.goals == 2:
            return "2"
        else:
            return "3+"
