"""MatchupFeaturesデータモデルのテスト"""

from datetime import datetime

import pytest

from toto_predictor.models.matchup_features import MatchupFeatures
from toto_predictor.models.team_features import TeamFeatures


@pytest.fixture
def team_a_features():
    """攻撃的なチームAの特徴量"""
    return TeamFeatures(
        team="Team A",
        calculated_at=datetime(2025, 12, 1),
        goals_mean=2.0,
        goals_std=1.0,
        xg_mean=1.8,
        xg_std=0.5,
        xg_trend=0.2,
        goals_trend=0.3,
        shots_mean=15.0,
        shots_on_target_mean=7.0,
        shot_conversion=0.133,
        xg_overperformance=0.2,
        possession_mean=58.0,
        passes_mean=500.0,
        pass_accuracy=85.0,
        conceded_mean=1.0,
        conceded_std=0.8,
        xg_against_mean=0.9,
        ppda_mean=8.0,
        interceptions_mean=12.0,
        home_goals_mean=2.5,
        away_goals_mean=1.5,
        fouls_mean=11.0,
        yellow_cards_mean=1.5,
        corners_mean=6.0,
    )


@pytest.fixture
def team_b_features():
    """守備的なチームBの特徴量"""
    return TeamFeatures(
        team="Team B",
        calculated_at=datetime(2025, 12, 1),
        goals_mean=0.8,
        goals_std=0.7,
        xg_mean=0.7,
        xg_std=0.3,
        xg_trend=-0.1,
        goals_trend=-0.2,
        shots_mean=8.0,
        shots_on_target_mean=3.0,
        shot_conversion=0.1,
        xg_overperformance=0.1,
        possession_mean=42.0,
        passes_mean=350.0,
        pass_accuracy=78.0,
        conceded_mean=0.5,
        conceded_std=0.6,
        xg_against_mean=0.6,
        ppda_mean=12.0,
        interceptions_mean=15.0,
        home_goals_mean=1.0,
        away_goals_mean=0.6,
        fouls_mean=14.0,
        yellow_cards_mean=2.0,
        corners_mean=3.0,
    )


@pytest.fixture
def team_c_features():
    """中間的なチームCの特徴量"""
    return TeamFeatures(
        team="Team C",
        calculated_at=datetime(2025, 12, 1),
        goals_mean=1.5,
        goals_std=0.9,
        xg_mean=1.4,
        xg_std=0.4,
        xg_trend=0.0,
        goals_trend=0.1,
        shots_mean=12.0,
        shots_on_target_mean=5.0,
        shot_conversion=0.125,
        xg_overperformance=0.1,
        possession_mean=50.0,
        passes_mean=420.0,
        pass_accuracy=80.0,
        conceded_mean=1.2,
        conceded_std=0.9,
        xg_against_mean=1.1,
        ppda_mean=10.0,
        interceptions_mean=10.0,
        home_goals_mean=1.8,
        away_goals_mean=1.2,
        fouls_mean=12.0,
        yellow_cards_mean=1.8,
        corners_mean=5.0,
    )


class TestMatchupFeaturesCreation:
    """MatchupFeaturesの生成テスト"""

    def test_from_team_features_basic(self, team_a_features, team_b_features):
        """from_team_features で基本的な生成ができること"""
        matchup = MatchupFeatures.from_team_features(team_a_features, team_b_features, is_home=True)

        assert matchup.team == "Team A"
        assert matchup.opponent == "Team B"
        assert matchup.is_home is True

    def test_from_team_features_attack_stats_copied(self, team_a_features, team_b_features):
        """チーム攻撃指標がTeamFeaturesから正しく転写されること"""
        matchup = MatchupFeatures.from_team_features(team_a_features, team_b_features, is_home=True)

        assert matchup.goals_mean == team_a_features.goals_mean
        assert matchup.xg_mean == team_a_features.xg_mean
        assert matchup.shots_mean == team_a_features.shots_mean
        assert matchup.possession_mean == team_a_features.possession_mean

    def test_from_team_features_opponent_defense_stats(self, team_a_features, team_b_features):
        """相手守備指標がopponent_featuresから正しく取得されること"""
        matchup = MatchupFeatures.from_team_features(team_a_features, team_b_features, is_home=True)

        assert matchup.opp_conceded_mean == team_b_features.conceded_mean
        assert matchup.opp_xg_against_mean == team_b_features.xg_against_mean
        assert matchup.opp_ppda_mean == team_b_features.ppda_mean
        assert matchup.opp_interceptions_mean == team_b_features.interceptions_mean

    def test_from_team_features_interaction_features(self, team_a_features, team_b_features):
        """交互作用特徴量が正しく計算されること"""
        matchup = MatchupFeatures.from_team_features(team_a_features, team_b_features, is_home=True)

        # attack_vs_defense = team_xg_mean - opp_xg_against_mean
        expected_avd = team_a_features.xg_mean - team_b_features.xg_against_mean
        assert matchup.attack_vs_defense == pytest.approx(expected_avd)

        # xg_diff = team_xg_mean - opp_xg_mean
        expected_xg_diff = team_a_features.xg_mean - team_b_features.xg_mean
        assert matchup.xg_diff == pytest.approx(expected_xg_diff)

        # possession_diff
        expected_poss_diff = team_a_features.possession_mean - (
            100 - team_b_features.possession_mean
        )
        assert matchup.possession_diff == pytest.approx(expected_poss_diff)

    def test_from_team_features_home_adjustment(self, team_a_features, team_b_features):
        """ホーム時にhome_goals_mean、アウェイ時にaway_goals_meanが使用されること"""
        matchup_home = MatchupFeatures.from_team_features(
            team_a_features, team_b_features, is_home=True
        )
        assert matchup_home.adjusted_goals_mean == team_a_features.home_goals_mean

        matchup_away = MatchupFeatures.from_team_features(
            team_a_features, team_b_features, is_home=False
        )
        assert matchup_away.adjusted_goals_mean == team_a_features.away_goals_mean


class TestMatchupFeaturesDifferentiation:
    """同チーム異相手で特徴量が変わることのテスト"""

    def test_same_team_different_opponents_produces_different_features(
        self, team_a_features, team_b_features, team_c_features
    ):
        """同じチームでも相手が違えば異なる特徴量ベクトルになること"""
        matchup_vs_b = MatchupFeatures.from_team_features(
            team_a_features, team_b_features, is_home=True
        )
        matchup_vs_c = MatchupFeatures.from_team_features(
            team_a_features, team_c_features, is_home=True
        )

        # チーム攻撃指標は同じ
        assert matchup_vs_b.goals_mean == matchup_vs_c.goals_mean
        assert matchup_vs_b.xg_mean == matchup_vs_c.xg_mean

        # 相手守備指標は異なる
        assert matchup_vs_b.opp_conceded_mean != matchup_vs_c.opp_conceded_mean
        assert matchup_vs_b.opp_xg_against_mean != matchup_vs_c.opp_xg_against_mean

        # 交互作用特徴量も異なる
        assert matchup_vs_b.attack_vs_defense != matchup_vs_c.attack_vs_defense
        assert matchup_vs_b.xg_diff != matchup_vs_c.xg_diff

        # 特徴量ベクトル全体が異なる
        assert matchup_vs_b.to_feature_vector() != matchup_vs_c.to_feature_vector()


class TestMatchupFeaturesConversion:
    """変換メソッドのテスト"""

    def test_to_dict_contains_all_fields(self, team_a_features, team_b_features):
        """to_dict()が全フィールドを含むこと"""
        matchup = MatchupFeatures.from_team_features(team_a_features, team_b_features, is_home=True)
        d = matchup.to_dict()

        assert d["team"] == "Team A"
        assert d["opponent"] == "Team B"
        assert d["is_home"] is True
        assert "goals_mean" in d
        assert "opp_conceded_mean" in d
        assert "attack_vs_defense" in d
        assert "adjusted_goals_mean" in d

    def test_to_feature_vector_length_matches_names(self, team_a_features, team_b_features):
        """to_feature_vector()の長さがget_feature_names()と一致すること"""
        matchup = MatchupFeatures.from_team_features(team_a_features, team_b_features, is_home=True)
        vector = matchup.to_feature_vector()
        names = MatchupFeatures.get_feature_names()

        assert len(vector) == len(names)

    def test_to_feature_vector_contains_is_home(self, team_a_features, team_b_features):
        """to_feature_vector()の最後にis_homeフラグが含まれること"""
        matchup_home = MatchupFeatures.from_team_features(
            team_a_features, team_b_features, is_home=True
        )
        matchup_away = MatchupFeatures.from_team_features(
            team_a_features, team_b_features, is_home=False
        )

        assert matchup_home.to_feature_vector()[-1] == 1.0
        assert matchup_away.to_feature_vector()[-1] == 0.0

    def test_get_feature_names_is_static(self):
        """get_feature_names()がstaticmethodとして動作すること"""
        names = MatchupFeatures.get_feature_names()
        assert isinstance(names, list)
        assert len(names) == 25  # 13攻撃 + 6守備 + 4交互 + 1調整 + 1 is_home
        assert names[0] == "goals_mean"
        assert names[-1] == "is_home"

    def test_to_feature_vector_all_numeric(self, team_a_features, team_b_features):
        """to_feature_vector()の全要素がfloatであること"""
        matchup = MatchupFeatures.from_team_features(team_a_features, team_b_features, is_home=True)
        vector = matchup.to_feature_vector()
        for v in vector:
            assert isinstance(v, float)


class TestMatchupFeaturesDirectCreation:
    """直接生成のテスト"""

    def test_create_with_defaults(self):
        """デフォルト値で生成できること"""
        matchup = MatchupFeatures(team="Team X", opponent="Team Y")
        assert matchup.goals_mean == 0.0
        assert matchup.opp_conceded_mean == 0.0
        assert matchup.is_home is True

    def test_create_with_explicit_values(self):
        """明示的な値で生成できること"""
        matchup = MatchupFeatures(
            team="Team X",
            opponent="Team Y",
            is_home=False,
            goals_mean=2.5,
            opp_conceded_mean=1.8,
            attack_vs_defense=0.7,
        )
        assert matchup.goals_mean == 2.5
        assert matchup.opp_conceded_mean == 1.8
        assert matchup.attack_vs_defense == 0.7
        assert matchup.is_home is False
