"""対戦カード特徴量データモデル

このモジュールは、対戦相手を考慮した機械学習モデル入力特徴量を定義します。
チーム攻撃指標 × 相手守備指標 の交互作用特徴量を含みます。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Self

from .team_features import TeamFeatures


@dataclass
class MatchupFeatures:
    """対戦カード特徴量を表すデータクラス

    チーム固有の特徴量に加え、対戦相手の守備指標と交互作用特徴量を格納します。
    同じチームでも対戦相手が異なれば異なる特徴量ベクトルを生成します。

    Attributes:
        team: チーム名
        opponent: 対戦相手チーム名
        is_home: ホームかどうか
        calculated_at: 特徴量計算日時

        # チーム攻撃指標（TeamFeaturesから転写）
        goals_mean: 平均得点
        goals_std: 得点の標準偏差
        xg_mean: 平均xG
        xg_std: xGの標準偏差
        xg_trend: xGトレンド
        goals_trend: 得点トレンド
        shots_mean: 平均シュート数
        shots_on_target_mean: 平均枠内シュート数
        shot_conversion: シュート決定率
        xg_overperformance: xG超過パフォーマンス
        possession_mean: 平均ボール支配率
        passes_mean: 平均パス数
        pass_accuracy: パス成功率

        # 相手守備指標
        opp_conceded_mean: 相手平均失点
        opp_conceded_std: 相手失点の標準偏差
        opp_xg_against_mean: 相手平均被xG
        opp_ppda_mean: 相手平均PPDA
        opp_interceptions_mean: 相手平均インターセプト数
        opp_possession_mean: 相手平均ボール支配率

        # 交互作用特徴量
        attack_vs_defense: 攻撃力 vs 守備力（team_xg - opp_xg_against）
        xg_diff: xG差（team_xg - opp_xg）
        possession_diff: 支配率差
        shot_conversion_vs_opp_defense: シュート決定率 vs 相手守備

        # ホーム/アウェイ調整
        adjusted_goals_mean: ホーム/アウェイ調整済み平均得点
    """

    team: str
    opponent: str
    is_home: bool = True
    calculated_at: datetime = field(default_factory=datetime.now)

    # チーム攻撃指標
    goals_mean: float = 0.0
    goals_std: float = 0.0
    xg_mean: float = 0.0
    xg_std: float = 0.0
    xg_trend: float = 0.0
    goals_trend: float = 0.0
    shots_mean: float = 0.0
    shots_on_target_mean: float = 0.0
    shot_conversion: float = 0.0
    xg_overperformance: float = 0.0
    possession_mean: float = 50.0
    passes_mean: float = 0.0
    pass_accuracy: float = 0.0

    # 相手守備指標
    opp_conceded_mean: float = 0.0
    opp_conceded_std: float = 0.0
    opp_xg_against_mean: float = 0.0
    opp_ppda_mean: float = 10.0
    opp_interceptions_mean: float = 0.0
    opp_possession_mean: float = 50.0

    # 交互作用特徴量
    attack_vs_defense: float = 0.0
    xg_diff: float = 0.0
    possession_diff: float = 0.0
    shot_conversion_vs_opp_defense: float = 0.0

    # ホーム/アウェイ調整
    adjusted_goals_mean: float = 0.0

    @classmethod
    def from_team_features(
        cls,
        team_features: TeamFeatures,
        opponent_features: TeamFeatures,
        is_home: bool,
    ) -> Self:
        """2チームのTeamFeaturesからMatchupFeaturesを生成

        Args:
            team_features: 対象チームの特徴量
            opponent_features: 対戦相手の特徴量
            is_home: 対象チームがホームかどうか

        Returns:
            MatchupFeaturesオブジェクト
        """
        # 交互作用特徴量の算出
        attack_vs_defense = team_features.xg_mean - opponent_features.xg_against_mean
        xg_diff = team_features.xg_mean - opponent_features.xg_mean
        possession_diff = team_features.possession_mean - (100 - opponent_features.possession_mean)
        shot_conversion_vs_opp_defense = (
            (
                team_features.shot_conversion
                - opponent_features.conceded_mean / max(opponent_features.shots_mean, 1)
            )
            if opponent_features.shots_mean > 0
            else team_features.shot_conversion
        )

        # ホーム/アウェイ調整済みゴール平均
        adjusted_goals = team_features.home_goals_mean if is_home else team_features.away_goals_mean

        return cls(
            team=team_features.team,
            opponent=opponent_features.team,
            is_home=is_home,
            calculated_at=team_features.calculated_at,
            # チーム攻撃指標
            goals_mean=team_features.goals_mean,
            goals_std=team_features.goals_std,
            xg_mean=team_features.xg_mean,
            xg_std=team_features.xg_std,
            xg_trend=team_features.xg_trend,
            goals_trend=team_features.goals_trend,
            shots_mean=team_features.shots_mean,
            shots_on_target_mean=team_features.shots_on_target_mean,
            shot_conversion=team_features.shot_conversion,
            xg_overperformance=team_features.xg_overperformance,
            possession_mean=team_features.possession_mean,
            passes_mean=team_features.passes_mean,
            pass_accuracy=team_features.pass_accuracy,
            # 相手守備指標
            opp_conceded_mean=opponent_features.conceded_mean,
            opp_conceded_std=opponent_features.conceded_std,
            opp_xg_against_mean=opponent_features.xg_against_mean,
            opp_ppda_mean=opponent_features.ppda_mean,
            opp_interceptions_mean=opponent_features.interceptions_mean,
            opp_possession_mean=opponent_features.possession_mean,
            # 交互作用特徴量
            attack_vs_defense=attack_vs_defense,
            xg_diff=xg_diff,
            possession_diff=possession_diff,
            shot_conversion_vs_opp_defense=shot_conversion_vs_opp_defense,
            # ホーム/アウェイ調整
            adjusted_goals_mean=adjusted_goals,
        )

    def to_dict(self) -> dict:
        """MatchupFeaturesオブジェクトを辞書に変換

        Returns:
            特徴量データを含む辞書
        """
        return {
            "team": self.team,
            "opponent": self.opponent,
            "is_home": self.is_home,
            "calculated_at": self.calculated_at.isoformat(),
            # チーム攻撃指標
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
            # 相手守備指標
            "opp_conceded_mean": self.opp_conceded_mean,
            "opp_conceded_std": self.opp_conceded_std,
            "opp_xg_against_mean": self.opp_xg_against_mean,
            "opp_ppda_mean": self.opp_ppda_mean,
            "opp_interceptions_mean": self.opp_interceptions_mean,
            "opp_possession_mean": self.opp_possession_mean,
            # 交互作用特徴量
            "attack_vs_defense": self.attack_vs_defense,
            "xg_diff": self.xg_diff,
            "possession_diff": self.possession_diff,
            "shot_conversion_vs_opp_defense": self.shot_conversion_vs_opp_defense,
            # ホーム/アウェイ調整
            "adjusted_goals_mean": self.adjusted_goals_mean,
        }

    def to_feature_vector(self) -> list[float]:
        """機械学習用の特徴量ベクトルに変換

        Returns:
            特徴量のリスト（get_feature_names()と同じ順序）
        """
        return [
            # チーム攻撃指標
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
            # 相手守備指標
            self.opp_conceded_mean,
            self.opp_conceded_std,
            self.opp_xg_against_mean,
            self.opp_ppda_mean,
            self.opp_interceptions_mean,
            self.opp_possession_mean,
            # 交互作用特徴量
            self.attack_vs_defense,
            self.xg_diff,
            self.possession_diff,
            self.shot_conversion_vs_opp_defense,
            # ホーム/アウェイ調整
            self.adjusted_goals_mean,
            # ホーム/アウェイフラグ
            float(self.is_home),
        ]

    @staticmethod
    def get_feature_names() -> list[str]:
        """特徴量名のリストを取得

        Returns:
            特徴量名のリスト（to_feature_vector()と同じ順序）
        """
        return [
            # チーム攻撃指標
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
            # 相手守備指標
            "opp_conceded_mean",
            "opp_conceded_std",
            "opp_xg_against_mean",
            "opp_ppda_mean",
            "opp_interceptions_mean",
            "opp_possession_mean",
            # 交互作用特徴量
            "attack_vs_defense",
            "xg_diff",
            "possession_diff",
            "shot_conversion_vs_opp_defense",
            # ホーム/アウェイ調整
            "adjusted_goals_mean",
            # ホーム/アウェイフラグ
            "is_home",
        ]
