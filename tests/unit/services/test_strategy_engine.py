"""StrategyEngineのユニットテスト"""

import pytest

from toto_predictor.models.prediction import Prediction
from toto_predictor.models.vote_rate import VoteRate
from toto_predictor.services.strategy_engine import StrategyEngine


class TestStrategyEngine:
    """StrategyEngineのテスト"""

    @pytest.fixture
    def engine(self, tmp_path):
        """StrategyEngineインスタンス"""
        return StrategyEngine(str(tmp_path / "reports"))

    @pytest.fixture
    def sample_prediction(self):
        """サンプル予測"""
        return Prediction(
            round_number=1607,
            team="Yokohama F. Marinos",
            prob_0=0.18,
            prob_1=0.32,
            prob_2=0.28,
            prob_3plus=0.22,
        )

    @pytest.fixture
    def sample_vote_rate(self):
        """サンプル投票率"""
        return VoteRate(
            round_number=1607,
            team="Yokohama F. Marinos",
            vote_0=0.22,
            vote_1=0.35,
            vote_2=0.25,
            vote_3plus=0.18,
        )

    def test_calculate_value_score_normal(self, engine):
        """正常なバリュースコア計算"""
        score = engine._calculate_value_score(0.30, 0.20)
        assert score == pytest.approx(1.5)

    def test_calculate_value_score_zero_vote(self, engine):
        """投票率0の場合はMIN_RATEで計算"""
        score = engine._calculate_value_score(0.30, 0.0)
        assert score == pytest.approx(30.0)  # 0.30 / 0.01

    def test_determine_action_must_buy(self, engine):
        """高確率・高バリューで「必買」"""
        action = engine._determine_action(0.35, 1.6)
        assert action == "必買"

    def test_determine_action_buy_high_prob(self, engine):
        """高確率・中バリューで「買い」"""
        action = engine._determine_action(0.35, 1.2)
        assert action == "買い"

    def test_determine_action_caution(self, engine):
        """高確率・低バリューで「慎重」"""
        action = engine._determine_action(0.35, 0.8)
        assert action == "慎重"

    def test_determine_action_buy_mid_prob(self, engine):
        """中確率・高バリューで「買い」"""
        action = engine._determine_action(0.20, 1.6)
        assert action == "買い"

    def test_determine_action_consider(self, engine):
        """中確率・中バリューで「検討」"""
        action = engine._determine_action(0.20, 1.1)
        assert action == "検討"

    def test_determine_action_skip_mid_prob(self, engine):
        """中確率・低バリューで「スキップ」"""
        action = engine._determine_action(0.20, 0.8)
        assert action == "スキップ"

    def test_determine_action_consider_low_prob(self, engine):
        """低確率・高バリューで「検討」"""
        action = engine._determine_action(0.10, 1.6)
        assert action == "検討"

    def test_determine_action_skip_low_prob(self, engine):
        """低確率・低バリューで「スキップ」"""
        action = engine._determine_action(0.10, 0.8)
        assert action == "スキップ"

    def test_calculate_kelly_positive_edge(self, engine):
        """正のエッジがあるとケリー比率が正"""
        kelly = engine._calculate_kelly(0.50, 0.20)  # 大きなエッジ
        assert kelly > 0
        assert kelly <= 0.1  # 上限チェック

    def test_calculate_kelly_negative_edge(self, engine):
        """負のエッジだとケリー比率は0"""
        kelly = engine._calculate_kelly(0.10, 0.50)  # 負のエッジ
        assert kelly == 0.0

    def test_calculate_kelly_zero_vote(self, engine):
        """投票率0だとケリー比率は0"""
        kelly = engine._calculate_kelly(0.30, 0.0)
        assert kelly == 0.0

    def test_determine_confidence_high(self, engine):
        """高確率・高バリューで「high」"""
        confidence = engine._determine_confidence(0.35, 1.5)
        assert confidence == "high"

    def test_determine_confidence_medium(self, engine):
        """中確率・中バリューで「medium」"""
        confidence = engine._determine_confidence(0.25, 1.1)
        assert confidence == "medium"

    def test_determine_confidence_low(self, engine):
        """低確率・低バリューで「low」"""
        confidence = engine._determine_confidence(0.10, 0.8)
        assert confidence == "low"

    def test_calculate_value_scores(self, engine, sample_prediction, sample_vote_rate):
        """バリュースコア計算が正しく動作する"""
        recommendations = engine.calculate_value_scores([sample_prediction], [sample_vote_rate])

        assert len(recommendations) == 4  # 4カテゴリ
        assert all(r.team == "Yokohama F. Marinos" for r in recommendations)
        assert all(r.round_number == 1607 for r in recommendations)

    def test_calculate_value_scores_sorted(self, engine, sample_prediction, sample_vote_rate):
        """推奨がバリュースコア降順でソートされる"""
        recommendations = engine.calculate_value_scores([sample_prediction], [sample_vote_rate])

        for i in range(len(recommendations) - 1):
            assert recommendations[i].value_score >= recommendations[i + 1].value_score

    def test_generate_report(self, engine, sample_prediction, sample_vote_rate):
        """レポート生成が正しく動作する"""
        recommendations = engine.calculate_value_scores([sample_prediction], [sample_vote_rate])

        report_path = engine.generate_report(recommendations)

        assert report_path != ""
        with open(report_path) as f:
            content = f.read()

        assert "GOAL3" in content
        assert "Yokohama F. Marinos" in content
        assert "バリュー" in content

    def test_generate_report_empty_recommendations(self, engine):
        """空の推奨でも動作する"""
        report_path = engine.generate_report([])
        assert report_path == ""
