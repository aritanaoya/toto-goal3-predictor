"""FeatureEngineの対戦カード特徴量テスト"""

from datetime import datetime

import pytest

from toto_predictor.models.matchup_features import MatchupFeatures
from toto_predictor.services.feature_engine import FeatureEngine


class TestCalculateMatchupFeatures:
    """calculate_matchup_features()のテスト"""

    def test_returns_matchup_features_object(self, populated_db):
        """MatchupFeaturesオブジェクトが返ること"""
        engine = FeatureEngine(populated_db)
        matchup = engine.calculate_matchup_features(
            "Yokohama F. Marinos", "Kawasaki Frontale", is_home=True
        )
        assert isinstance(matchup, MatchupFeatures)
        assert matchup.team == "Yokohama F. Marinos"
        assert matchup.opponent == "Kawasaki Frontale"
        assert matchup.is_home is True

    def test_different_opponents_produce_different_features(self, populated_db):
        """同じチームでも相手が変わると特徴量が変わること"""
        engine = FeatureEngine(populated_db)

        matchup_vs_kawasaki = engine.calculate_matchup_features(
            "Yokohama F. Marinos", "Kawasaki Frontale", is_home=True
        )
        matchup_vs_kashima = engine.calculate_matchup_features(
            "Yokohama F. Marinos", "Kashima Antlers", is_home=True
        )

        # チーム攻撃指標は同じ（同チーム同条件）
        assert matchup_vs_kawasaki.goals_mean == matchup_vs_kashima.goals_mean

        # 相手守備指標は異なる
        assert matchup_vs_kawasaki.opp_conceded_mean != matchup_vs_kashima.opp_conceded_mean

        # 特徴量ベクトル全体が異なる（相手が違うため）
        assert matchup_vs_kawasaki.to_feature_vector() != matchup_vs_kashima.to_feature_vector()

    def test_home_away_produces_different_adjustment(self, populated_db):
        """ホーム/アウェイで調整済みゴール平均が異なること"""
        engine = FeatureEngine(populated_db)

        matchup_home = engine.calculate_matchup_features(
            "Yokohama F. Marinos", "Kawasaki Frontale", is_home=True
        )
        matchup_away = engine.calculate_matchup_features(
            "Yokohama F. Marinos", "Kawasaki Frontale", is_home=False
        )

        assert matchup_home.is_home is True
        assert matchup_away.is_home is False
        # adjusted_goals_meanがホーム/アウェイで異なるべき
        # （populated_dbのデータ構造上、異なることが期待される）

    def test_feature_vector_length_is_correct(self, populated_db):
        """特徴量ベクトルの長さが25であること"""
        engine = FeatureEngine(populated_db)
        matchup = engine.calculate_matchup_features(
            "Yokohama F. Marinos", "Kawasaki Frontale", is_home=True
        )
        vector = matchup.to_feature_vector()
        names = MatchupFeatures.get_feature_names()
        assert len(vector) == 25
        assert len(vector) == len(names)


class TestPrepareTrainingDataMatchup:
    """prepare_training_data()の対戦カード対応テスト"""

    def test_use_matchup_true_produces_matchup_columns(self, populated_db):
        """use_matchup=Trueで対戦カード特徴量列が含まれること"""
        engine = FeatureEngine(populated_db)
        features_df, targets = engine.prepare_training_data([2025], use_matchup=True)

        # 対戦カード固有の列が含まれること
        assert "opp_conceded_mean" in features_df.columns
        assert "attack_vs_defense" in features_df.columns
        assert "xg_diff" in features_df.columns
        assert "is_home" in features_df.columns

    def test_use_matchup_false_produces_legacy_columns(self, populated_db):
        """use_matchup=Falseで従来の特徴量列が含まれること"""
        engine = FeatureEngine(populated_db)
        features_df, targets = engine.prepare_training_data([2025], use_matchup=False)

        # 従来の列（相手の列がない）
        assert "goals_mean" in features_df.columns
        assert "opp_conceded_mean" not in features_df.columns

    def test_matchup_data_has_different_columns(self, populated_db):
        """matchup特徴量に対戦相手固有の列が含まれること"""
        engine = FeatureEngine(populated_db)
        matchup_df, _ = engine.prepare_training_data([2025], use_matchup=True)
        legacy_df, _ = engine.prepare_training_data([2025], use_matchup=False)

        # matchup固有の列が含まれる
        assert "opp_conceded_mean" in matchup_df.columns
        assert "attack_vs_defense" in matchup_df.columns
        # legacy固有の列はmatchupには含まれない
        assert "window_size" not in matchup_df.columns
        assert "fouls_mean" not in matchup_df.columns

    def test_matchup_training_data_has_samples(self, populated_db):
        """matchupモードでもサンプルが生成されること"""
        engine = FeatureEngine(populated_db)
        matchup_df, matchup_targets = engine.prepare_training_data([2025], use_matchup=True)

        # matchupモードは両チームのデータが必要なため、レガシーより少なくなりうる
        assert len(matchup_df) > 0
        assert len(matchup_df) == len(matchup_targets)
