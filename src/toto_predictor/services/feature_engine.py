"""特徴量エンジン

このモジュールは、生データから機械学習モデル用の特徴量を計算します。
"""

import logging
from datetime import datetime

import pandas as pd

from ..db.database import Database
from ..db.repositories.match_repository import MatchRepository
from ..db.repositories.team_stats_repository import TeamStatsRepository
from ..models.exceptions import DataNotFoundError
from ..models.matchup_features import MatchupFeatures
from ..models.team_features import TeamFeatures

logger = logging.getLogger(__name__)


class FeatureEngine:
    """特徴量計算エンジン

    チームの過去試合データから機械学習モデル用の特徴量を計算します。

    Attributes:
        db: Databaseインスタンス
        match_repo: MatchRepositoryインスタンス
        stats_repo: TeamStatsRepositoryインスタンス
    """

    # 特徴量計算に必要な最小試合数
    MIN_MATCHES = 5

    def __init__(self, db_path: str) -> None:
        """特徴量エンジンを初期化

        Args:
            db_path: データベースファイルのパス
        """
        self.db = Database(db_path)
        self.match_repo = MatchRepository(self.db)
        self.stats_repo = TeamStatsRepository(self.db)

    def calculate_features(
        self,
        team: str,
        as_of_date: datetime | None = None,
        window_sizes: list[int] | None = None,
    ) -> TeamFeatures:
        """指定日時点でのチームの特徴量を計算

        Args:
            team: チーム名
            as_of_date: 特徴量を計算する基準日時（Noneの場合は現在）
            window_sizes: 計算に使用するウィンドウサイズのリスト（デフォルト: [5, 10, 20]）

        Returns:
            計算された特徴量を含むTeamFeaturesオブジェクト

        Raises:
            DataNotFoundError: チームのデータが不足している場合
        """
        if as_of_date is None:
            as_of_date = datetime.now()

        if window_sizes is None:
            window_sizes = [5, 10, 20]

        # チームの試合統計を取得（指定日以前）
        stats_list = self.stats_repo.find_by_team(
            team, limit=max(window_sizes), before_date=as_of_date
        )

        if len(stats_list) < self.MIN_MATCHES:
            raise DataNotFoundError(
                f"チーム {team} の試合データが不足しています "
                f"（必要: {self.MIN_MATCHES}試合、現在: {len(stats_list)}試合）",
                details={"team": team, "available_matches": len(stats_list)},
            )

        # DataFrameに変換
        df = pd.DataFrame([s.to_dict() for s in stats_list])

        # 欠損値の処理（数値列を0で補完）
        numeric_columns = [
            "goals",
            "xg",
            "shots",
            "shots_on_target",
            "possession",
            "passes",
            "passes_accurate",
            "conceded_goals",
            "xg_against",
            "ppda",
            "interceptions",
            "fouls",
            "yellow_cards",
            "corners",
        ]
        for col in numeric_columns:
            if col in df.columns:
                nan_count = df[col].isna().sum()
                if nan_count > 0:
                    logger.warning(f"欠損値を検出: {col} ({nan_count}件) - 0で補完")
                    df[col] = df[col].fillna(0)

        # 主要ウィンドウサイズでの特徴量計算（デフォルト: 10試合）
        main_window = window_sizes[1] if len(window_sizes) > 1 else window_sizes[0]
        df_main = df.head(main_window)

        # 基本統計量の計算
        features = TeamFeatures(
            team=team,
            calculated_at=as_of_date,
            window_size=main_window,
            # 攻撃基本統計
            goals_mean=df_main["goals"].mean(),
            goals_std=df_main["goals"].std() if len(df_main) > 1 else 0.0,
            xg_mean=df_main["xg"].mean(),
            xg_std=df_main["xg"].std() if len(df_main) > 1 else 0.0,
            # シュート関連
            shots_mean=df_main["shots"].mean(),
            shots_on_target_mean=df_main["shots_on_target"].mean(),
            # 支配率・パス
            possession_mean=df_main["possession"].mean(),
            passes_mean=df_main["passes"].mean(),
            # 守備統計
            conceded_mean=df_main["conceded_goals"].mean(),
            conceded_std=df_main["conceded_goals"].std() if len(df_main) > 1 else 0.0,
            xg_against_mean=df_main["xg_against"].mean(),
            ppda_mean=df_main["ppda"].mean(),
            interceptions_mean=df_main["interceptions"].mean(),
            # その他
            fouls_mean=df_main["fouls"].mean(),
            yellow_cards_mean=df_main["yellow_cards"].mean(),
            corners_mean=df_main["corners"].mean(),
        )

        # 派生特徴量の計算
        if features.shots_mean > 0:
            features.shot_conversion = features.goals_mean / features.shots_mean
        else:
            features.shot_conversion = 0.0

        features.xg_overperformance = features.goals_mean - features.xg_mean

        # パス成功率
        if features.passes_mean > 0:
            features.pass_accuracy = (
                df_main["passes_accurate"].mean() / features.passes_mean
            ) * 100

        # トレンド特徴量（短期 vs 長期）
        if len(window_sizes) >= 2 and len(df) >= window_sizes[0]:
            short_window = window_sizes[0]  # 5試合
            long_window = min(window_sizes[-1], len(df))  # 20試合（または利用可能な最大）

            df_short = df.head(short_window)
            df_long = df.head(long_window)

            features.xg_trend = df_short["xg"].mean() - df_long["xg"].mean()
            features.goals_trend = df_short["goals"].mean() - df_long["goals"].mean()

        # ホーム/アウェイ別の平均得点
        home_stats = df_main[df_main["is_home"]]
        away_stats = df_main[~df_main["is_home"]]

        if len(home_stats) > 0:
            features.home_goals_mean = home_stats["goals"].mean()
        if len(away_stats) > 0:
            features.away_goals_mean = away_stats["goals"].mean()

        # 外れ値の検出（ログ出力のみ、クリッピングは行わない）
        self._check_outliers(features, team)

        logger.debug(f"チーム {team} の特徴量を計算しました（{main_window}試合）")
        return features

    def _check_outliers(self, features: TeamFeatures, team: str) -> None:
        """外れ値を検出してログ出力

        Args:
            features: 計算された特徴量
            team: チーム名

        Note:
            外れ値はクリッピングせず、ログ出力のみ行います。
            toto GOAL3では「3点以上」カテゴリがあるため、
            高得点傾向のデータは有用な情報として扱います。
        """
        # 外れ値閾値（前処理設計書より）
        thresholds = {
            "goals_mean": (0, 5),
            "xg_mean": (0, 4.0),
            "possession_mean": (20, 80),
            "shots_mean": (0, 25),
            "ppda_mean": (5.0, 20.0),
        }

        outliers = []
        if features.goals_mean > thresholds["goals_mean"][1]:
            outliers.append(f"goals_mean={features.goals_mean:.2f}")
        if features.xg_mean > thresholds["xg_mean"][1]:
            outliers.append(f"xg_mean={features.xg_mean:.2f}")
        if features.possession_mean < thresholds["possession_mean"][0]:
            outliers.append(f"possession_mean={features.possession_mean:.1f}%（低）")
        elif features.possession_mean > thresholds["possession_mean"][1]:
            outliers.append(f"possession_mean={features.possession_mean:.1f}%（高）")
        if features.shots_mean > thresholds["shots_mean"][1]:
            outliers.append(f"shots_mean={features.shots_mean:.1f}")
        if features.ppda_mean > thresholds["ppda_mean"][1]:
            outliers.append(f"ppda_mean={features.ppda_mean:.1f}")

        if outliers:
            logger.warning(f"外れ値を検出: {team} - {', '.join(outliers)}")

    def calculate_opponent_features(
        self,
        team: str,
        opponent: str,
        as_of_date: datetime | None = None,
    ) -> dict:
        """対戦相手を考慮した特徴量を計算

        Args:
            team: 対象チーム名
            opponent: 対戦相手チーム名
            as_of_date: 特徴量計算の基準日時

        Returns:
            対戦相手を考慮した特徴量の辞書
        """
        team_features = self.calculate_features(team, as_of_date)
        opponent_features = self.calculate_features(opponent, as_of_date)

        return {
            "team_goals_mean": team_features.goals_mean,
            "team_xg_mean": team_features.xg_mean,
            "team_shot_conversion": team_features.shot_conversion,
            "opponent_conceded_mean": opponent_features.conceded_mean,
            "opponent_xg_against_mean": opponent_features.xg_against_mean,
            "opponent_ppda_mean": opponent_features.ppda_mean,
            # 攻撃力 vs 守備力の差
            "attack_vs_defense": team_features.xg_mean - opponent_features.xg_against_mean,
        }

    def calculate_matchup_features(
        self,
        team: str,
        opponent: str,
        is_home: bool,
        as_of_date: datetime | None = None,
    ) -> MatchupFeatures:
        """対戦カード特徴量を計算

        チームと対戦相手の両方の特徴量から、交互作用特徴量を含む
        MatchupFeaturesオブジェクトを生成します。

        Args:
            team: 対象チーム名
            opponent: 対戦相手チーム名
            is_home: 対象チームがホームかどうか
            as_of_date: 特徴量計算の基準日時

        Returns:
            MatchupFeaturesオブジェクト

        Raises:
            DataNotFoundError: いずれかのチームのデータが不足している場合
        """
        team_features = self.calculate_features(team, as_of_date)
        opponent_features = self.calculate_features(opponent, as_of_date)

        matchup = MatchupFeatures.from_team_features(team_features, opponent_features, is_home)

        logger.debug(
            f"対戦カード特徴量を計算: {team} vs {opponent} "
            f"(attack_vs_defense={matchup.attack_vs_defense:.3f})"
        )
        return matchup

    def prepare_training_data(
        self,
        seasons: list[int],
        min_matches_before: int = 10,
        use_matchup: bool = True,
    ) -> tuple[pd.DataFrame, pd.Series]:
        """モデル学習用のデータを準備

        各試合について、試合前の特徴量と実際の得点を紐付けたデータセットを生成します。

        Args:
            seasons: 対象シーズンのリスト
            min_matches_before: 特徴量計算に必要な最小試合数
            use_matchup: 対戦カード特徴量を使用するかどうか（デフォルト: True）

        Returns:
            (特徴量DataFrame, 目的変数Series)のタプル

        Raises:
            DataNotFoundError: データが不足している場合
        """
        all_features = []
        all_targets = []

        for season in seasons:
            matches = self.match_repo.find_by_season(season)
            logger.info(f"シーズン {season}: {len(matches)}試合")

            for match in matches:
                if not match.is_finished():
                    continue

                # 各チームについて特徴量と目標を計算
                for team, opponent, is_home in [
                    (match.home_team, match.away_team, True),
                    (match.away_team, match.home_team, False),
                ]:
                    try:
                        if use_matchup:
                            # 対戦カード特徴量を使用
                            matchup = self.calculate_matchup_features(
                                team, opponent, is_home, as_of_date=match.date
                            )
                            feature_dict = matchup.to_dict()
                        else:
                            # 従来のチーム単体特徴量を使用
                            features = self.calculate_features(
                                team,
                                as_of_date=match.date,
                                window_sizes=[5, 10, 20],
                            )
                            feature_dict = features.to_dict()
                            feature_dict["is_home"] = int(is_home)

                        # 実際の得点（目標変数）
                        goals = match.home_goals if is_home else match.away_goals

                        all_features.append(feature_dict)
                        all_targets.append(goals)

                    except DataNotFoundError:
                        # データ不足の場合はスキップ
                        continue

        if not all_features:
            raise DataNotFoundError(
                "学習用データが不足しています",
                details={"seasons": seasons},
            )

        # DataFrameに変換
        features_df = pd.DataFrame(all_features)
        targets = pd.Series(all_targets, name="goals")

        # 不要なカラムを削除
        drop_columns = ["team", "opponent", "calculated_at"]
        features_df = features_df.drop(
            columns=[c for c in drop_columns if c in features_df.columns]
        )

        # bool型のis_homeをintに変換
        if "is_home" in features_df.columns:
            features_df["is_home"] = features_df["is_home"].astype(int)

        logger.info(
            f"学習データを準備しました: {len(features_df)}サンプル, "
            f"{len(features_df.columns)}特徴量 (matchup={use_matchup})"
        )
        return features_df, targets

    def get_feature_importance(self, model, feature_names: list[str]) -> pd.DataFrame:
        """モデルの特徴量重要度を取得

        Args:
            model: 学習済みモデル（feature_importances_属性を持つ）
            feature_names: 特徴量名のリスト

        Returns:
            特徴量重要度のDataFrame
        """
        if hasattr(model, "feature_importances_"):
            importance = model.feature_importances_
        else:
            return pd.DataFrame()

        df = pd.DataFrame({"feature": feature_names, "importance": importance}).sort_values(
            "importance", ascending=False
        )

        return df
