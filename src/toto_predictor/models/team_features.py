"""チーム特徴量データモデル

このモジュールは、機械学習モデルに入力する特徴量を表すデータクラスを定義します。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Self


@dataclass
class TeamFeatures:
    """チーム特徴量を表すデータクラス

    特徴量エンジンによって計算された、機械学習モデルへの入力特徴量を格納します。

    Attributes:
        team: チーム名
        calculated_at: 特徴量計算日時
        window_size: 計算に使用した試合数

        # 攻撃基本統計（平均・標準偏差）
        goals_mean: 平均得点
        goals_std: 得点の標準偏差
        xg_mean: 平均xG
        xg_std: xGの標準偏差

        # トレンド特徴量
        xg_trend: xGトレンド（直近5試合 - 直近20試合の平均差）
        goals_trend: 得点トレンド

        # シュート関連
        shots_mean: 平均シュート数
        shots_on_target_mean: 平均枠内シュート数
        shot_conversion: シュート決定率（goals / shots）

        # パフォーマンス超過
        xg_overperformance: xG超過パフォーマンス（goals - xG）

        # 支配率・パス
        possession_mean: 平均ボール支配率
        passes_mean: 平均パス数
        pass_accuracy: パス成功率

        # 守備統計
        conceded_mean: 平均失点
        conceded_std: 失点の標準偏差
        xg_against_mean: 平均被xG
        ppda_mean: 平均PPDA
        interceptions_mean: 平均インターセプト数

        # ホーム/アウェイ別
        home_goals_mean: ホーム平均得点
        away_goals_mean: アウェイ平均得点

        # その他
        fouls_mean: 平均ファウル数
        yellow_cards_mean: 平均イエローカード数
        corners_mean: 平均コーナーキック数
    """

    team: str
    calculated_at: datetime = field(default_factory=datetime.now)
    window_size: int = 10

    # 攻撃基本統計
    goals_mean: float = 0.0
    goals_std: float = 0.0
    xg_mean: float = 0.0
    xg_std: float = 0.0

    # トレンド特徴量
    xg_trend: float = 0.0
    goals_trend: float = 0.0

    # シュート関連
    shots_mean: float = 0.0
    shots_on_target_mean: float = 0.0
    shot_conversion: float = 0.0

    # パフォーマンス超過
    xg_overperformance: float = 0.0

    # 支配率・パス
    possession_mean: float = 50.0
    passes_mean: float = 0.0
    pass_accuracy: float = 0.0

    # 守備統計
    conceded_mean: float = 0.0
    conceded_std: float = 0.0
    xg_against_mean: float = 0.0
    ppda_mean: float = 10.0
    interceptions_mean: float = 0.0

    # ホーム/アウェイ別
    home_goals_mean: float = 0.0
    away_goals_mean: float = 0.0

    # その他
    fouls_mean: float = 0.0
    yellow_cards_mean: float = 0.0
    corners_mean: float = 0.0

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """辞書からTeamFeaturesオブジェクトを生成

        Args:
            data: 特徴量データを含む辞書

        Returns:
            TeamFeaturesオブジェクト
        """
        calculated_at = data.get("calculated_at")
        if isinstance(calculated_at, str):
            calculated_at = datetime.fromisoformat(calculated_at)

        return cls(
            team=data["team"],
            calculated_at=calculated_at or datetime.now(),
            window_size=data.get("window_size", 10),
            goals_mean=data.get("goals_mean", 0.0),
            goals_std=data.get("goals_std", 0.0),
            xg_mean=data.get("xg_mean", 0.0),
            xg_std=data.get("xg_std", 0.0),
            xg_trend=data.get("xg_trend", 0.0),
            goals_trend=data.get("goals_trend", 0.0),
            shots_mean=data.get("shots_mean", 0.0),
            shots_on_target_mean=data.get("shots_on_target_mean", 0.0),
            shot_conversion=data.get("shot_conversion", 0.0),
            xg_overperformance=data.get("xg_overperformance", 0.0),
            possession_mean=data.get("possession_mean", 50.0),
            passes_mean=data.get("passes_mean", 0.0),
            pass_accuracy=data.get("pass_accuracy", 0.0),
            conceded_mean=data.get("conceded_mean", 0.0),
            conceded_std=data.get("conceded_std", 0.0),
            xg_against_mean=data.get("xg_against_mean", 0.0),
            ppda_mean=data.get("ppda_mean", 10.0),
            interceptions_mean=data.get("interceptions_mean", 0.0),
            home_goals_mean=data.get("home_goals_mean", 0.0),
            away_goals_mean=data.get("away_goals_mean", 0.0),
            fouls_mean=data.get("fouls_mean", 0.0),
            yellow_cards_mean=data.get("yellow_cards_mean", 0.0),
            corners_mean=data.get("corners_mean", 0.0),
        )

    def to_dict(self) -> dict:
        """TeamFeaturesオブジェクトを辞書に変換

        Returns:
            特徴量データを含む辞書
        """
        return {
            "team": self.team,
            "calculated_at": self.calculated_at.isoformat(),
            "window_size": self.window_size,
            "goals_mean": self.goals_mean,
            "goals_std": self.goals_std,
            "xg_mean": self.xg_mean,
            "xg_std": self.xg_std,
            "xg_trend": self.xg_trend,
            "goals_trend": self.goals_trend,
            "shots_mean": self.shots_mean,
            "shots_on_target_mean": self.shots_on_target_mean,
            "shot_conversion": self.shot_conversion,
            "xg_overperformance": self.xg_overperformance,
            "possession_mean": self.possession_mean,
            "passes_mean": self.passes_mean,
            "pass_accuracy": self.pass_accuracy,
            "conceded_mean": self.conceded_mean,
            "conceded_std": self.conceded_std,
            "xg_against_mean": self.xg_against_mean,
            "ppda_mean": self.ppda_mean,
            "interceptions_mean": self.interceptions_mean,
            "home_goals_mean": self.home_goals_mean,
            "away_goals_mean": self.away_goals_mean,
            "fouls_mean": self.fouls_mean,
            "yellow_cards_mean": self.yellow_cards_mean,
            "corners_mean": self.corners_mean,
        }

    def to_feature_vector(self) -> list[float]:
        """機械学習用の特徴量ベクトルに変換

        Returns:
            特徴量のリスト
        """
        return [
            self.goals_mean,
            self.goals_std,
            self.xg_mean,
            self.xg_std,
            self.xg_trend,
            self.goals_trend,
            self.shots_mean,
            self.shots_on_target_mean,
            self.shot_conversion,
            self.xg_overperformance,
            self.possession_mean,
            self.passes_mean,
            self.pass_accuracy,
            self.conceded_mean,
            self.conceded_std,
            self.xg_against_mean,
            self.ppda_mean,
            self.interceptions_mean,
            self.home_goals_mean,
            self.away_goals_mean,
            self.fouls_mean,
            self.yellow_cards_mean,
            self.corners_mean,
        ]

    @staticmethod
    def get_feature_names() -> list[str]:
        """特徴量名のリストを取得

        Returns:
            特徴量名のリスト
        """
        return [
            "goals_mean",
            "goals_std",
            "xg_mean",
            "xg_std",
            "xg_trend",
            "goals_trend",
            "shots_mean",
            "shots_on_target_mean",
            "shot_conversion",
            "xg_overperformance",
            "possession_mean",
            "passes_mean",
            "pass_accuracy",
            "conceded_mean",
            "conceded_std",
            "xg_against_mean",
            "ppda_mean",
            "interceptions_mean",
            "home_goals_mean",
            "away_goals_mean",
            "fouls_mean",
            "yellow_cards_mean",
            "corners_mean",
        ]
