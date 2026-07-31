"""データモデルのユニットテスト"""

from datetime import datetime

import pytest

from toto_predictor.models.exceptions import ValidationError
from toto_predictor.models.match import Match
from toto_predictor.models.prediction import Prediction
from toto_predictor.models.recommendation import Recommendation
from toto_predictor.models.team_stats import TeamStats
from toto_predictor.models.vote_rate import VoteRate


class TestMatch:
    """Matchモデルのテスト"""

    def test_create_valid_match(self):
        """有効な試合データを作成できる"""
        match = Match(
            date=datetime(2025, 12, 1),
            season=2025,
            competition="Japan. J1 League",
            home_team="Yokohama F. Marinos",
            away_team="Kawasaki Frontale",
            home_goals=2,
            away_goals=1,
        )

        assert match.home_team == "Yokohama F. Marinos"
        assert match.away_team == "Kawasaki Frontale"
        assert match.home_goals == 2
        assert match.away_goals == 1

    def test_invalid_season_raises_error(self):
        """不正なシーズンでエラーが発生する"""
        with pytest.raises(ValidationError) as exc_info:
            Match(
                date=datetime(2025, 12, 1),
                season=2050,  # 範囲外
                competition="Japan. J1 League",
                home_team="Team A",
                away_team="Team B",
            )

        assert exc_info.value.field == "season"

    def test_negative_goals_raises_error(self):
        """負の得点でエラーが発生する"""
        with pytest.raises(ValidationError) as exc_info:
            Match(
                date=datetime(2025, 12, 1),
                season=2025,
                competition="Japan. J1 League",
                home_team="Team A",
                away_team="Team B",
                home_goals=-1,
            )

        assert exc_info.value.field == "home_goals"

    def test_empty_team_name_raises_error(self):
        """空のチーム名でエラーが発生する"""
        with pytest.raises(ValidationError) as exc_info:
            Match(
                date=datetime(2025, 12, 1),
                season=2025,
                competition="Japan. J1 League",
                home_team="",
                away_team="Team B",
            )

        assert exc_info.value.field == "home_team"

    def test_is_finished(self):
        """試合終了判定が正しい"""
        finished = Match(
            date=datetime(2025, 12, 1),
            season=2025,
            competition="Test",
            home_team="A",
            away_team="B",
            home_goals=1,
            away_goals=0,
        )
        assert finished.is_finished() is True

        unfinished = Match(
            date=datetime(2025, 12, 1),
            season=2025,
            competition="Test",
            home_team="A",
            away_team="B",
        )
        assert unfinished.is_finished() is False

    def test_get_toto_category(self):
        """totoカテゴリが正しく取得できる"""
        match = Match(
            date=datetime(2025, 12, 1),
            season=2025,
            competition="Test",
            home_team="A",
            away_team="B",
            home_goals=3,
            away_goals=0,
        )

        assert match.get_toto_category("A") == "3+"
        assert match.get_toto_category("B") == "0"
        assert match.get_toto_category("C") is None

    def test_to_dict_and_from_dict(self):
        """辞書変換が正しく動作する"""
        match = Match(
            date=datetime(2025, 12, 1),
            season=2025,
            competition="Japan. J1 League",
            home_team="Team A",
            away_team="Team B",
            home_goals=2,
            away_goals=1,
        )

        data = match.to_dict()
        restored = Match.from_dict(data)

        assert restored.home_team == match.home_team
        assert restored.home_goals == match.home_goals

    def test_away_goals_negative_raises_error(self):
        """アウェイチームの負の得点でエラーが発生する"""
        with pytest.raises(ValidationError) as exc_info:
            Match(
                date=datetime(2025, 12, 1),
                season=2025,
                competition="Test",
                home_team="Team A",
                away_team="Team B",
                home_goals=0,
                away_goals=-1,
            )

        assert exc_info.value.field == "away_goals"

    def test_empty_away_team_raises_error(self):
        """空のアウェイチーム名でエラーが発生する"""
        with pytest.raises(ValidationError) as exc_info:
            Match(
                date=datetime(2025, 12, 1),
                season=2025,
                competition="Test",
                home_team="Team A",
                away_team="",
            )

        assert exc_info.value.field == "away_team"

    def test_negative_duration_raises_error(self):
        """負の試合時間でエラーが発生する"""
        with pytest.raises(ValidationError) as exc_info:
            Match(
                date=datetime(2025, 12, 1),
                season=2025,
                competition="Test",
                home_team="Team A",
                away_team="Team B",
                duration=-10,
            )

        assert exc_info.value.field == "duration"

    def test_from_dict_with_datetime_object(self):
        """from_dictがdatetimeオブジェクトを受け入れる"""
        data = {
            "date": datetime(2025, 1, 1),  # datetimeオブジェクト
            "season": 2025,
            "competition": "Test",
            "home_team": "Team A",
            "away_team": "Team B",
        }

        match = Match.from_dict(data)
        assert match.date == datetime(2025, 1, 1)

    def test_from_dict_with_missing_date(self):
        """from_dictが日付なしでも動作する"""
        data = {
            "season": 2025,
            "competition": "Test",
            "home_team": "Team A",
            "away_team": "Team B",
        }

        match = Match.from_dict(data)
        # date is set to now by default
        assert match.date is not None

    def test_get_toto_category_all_values(self):
        """全totoカテゴリが正しく取得できる"""
        # 1点
        match_1 = Match(
            date=datetime(2025, 12, 1),
            season=2025,
            competition="Test",
            home_team="A",
            away_team="B",
            home_goals=1,
            away_goals=2,
        )
        assert match_1.get_toto_category("A") == "1"
        assert match_1.get_toto_category("B") == "2"

    def test_get_toto_category_unfinished(self):
        """未終了試合ではNoneを返す"""
        match = Match(
            date=datetime(2025, 12, 1),
            season=2025,
            competition="Test",
            home_team="A",
            away_team="B",
            home_goals=None,
            away_goals=None,
        )

        assert match.get_toto_category("A") is None
        assert match.get_toto_category("B") is None


class TestTeamStats:
    """TeamStatsモデルのテスト"""

    def test_create_valid_stats(self):
        """有効な統計データを作成できる"""
        stats = TeamStats(
            match_id="test-match-id",
            team="Yokohama F. Marinos",
            is_home=True,
            goals=2,
            xg=1.8,
            shots=15,
            shots_on_target=8,
            possession=55.0,
        )

        assert stats.team == "Yokohama F. Marinos"
        assert stats.goals == 2
        assert stats.xg == 1.8

    def test_negative_goals_raises_error(self):
        """負の得点でエラーが発生する"""
        with pytest.raises(ValidationError):
            TeamStats(
                match_id="test",
                team="Team A",
                is_home=True,
                goals=-1,
            )

    def test_invalid_possession_raises_error(self):
        """不正なボール支配率でエラーが発生する"""
        with pytest.raises(ValidationError):
            TeamStats(
                match_id="test",
                team="Team A",
                is_home=True,
                possession=150.0,
            )

    def test_shots_on_target_exceeds_shots_raises_error(self):
        """枠内シュートがシュート数を超えるとエラーが発生する"""
        with pytest.raises(ValidationError):
            TeamStats(
                match_id="test",
                team="Team A",
                is_home=True,
                shots=5,
                shots_on_target=10,
            )

    def test_shot_conversion_property(self):
        """シュート決定率が正しく計算される"""
        stats = TeamStats(
            match_id="test",
            team="Team A",
            is_home=True,
            goals=2,
            shots=10,
            shots_on_target=5,
        )

        assert stats.shot_conversion == 0.2

    def test_xg_overperformance_property(self):
        """xG超過パフォーマンスが正しく計算される"""
        stats = TeamStats(
            match_id="test",
            team="Team A",
            is_home=True,
            goals=3,
            xg=2.0,
        )

        assert stats.xg_overperformance == 1.0

    def test_get_toto_category(self):
        """totoカテゴリが正しく取得できる"""
        assert TeamStats(match_id="t", team="A", is_home=True, goals=0).get_toto_category() == "0"
        assert TeamStats(match_id="t", team="A", is_home=True, goals=1).get_toto_category() == "1"
        assert TeamStats(match_id="t", team="A", is_home=True, goals=2).get_toto_category() == "2"
        assert TeamStats(match_id="t", team="A", is_home=True, goals=5).get_toto_category() == "3+"

    def test_negative_xg_raises_error(self):
        """負のxGでエラーが発生する"""
        with pytest.raises(ValidationError) as exc_info:
            TeamStats(match_id="t", team="A", is_home=True, xg=-1.0)
        assert exc_info.value.field == "xg"

    def test_negative_shots_raises_error(self):
        """負のシュート数でエラーが発生する"""
        with pytest.raises(ValidationError) as exc_info:
            TeamStats(match_id="t", team="A", is_home=True, shots=-1)
        assert exc_info.value.field == "shots"

    def test_negative_shots_on_target_raises_error(self):
        """負の枠内シュート数でエラーが発生する"""
        with pytest.raises(ValidationError) as exc_info:
            TeamStats(match_id="t", team="A", is_home=True, shots_on_target=-1)
        assert exc_info.value.field == "shots_on_target"

    def test_zero_ppda_raises_error(self):
        """PPDAが0でエラーが発生する"""
        with pytest.raises(ValidationError) as exc_info:
            TeamStats(match_id="t", team="A", is_home=True, ppda=0)
        assert exc_info.value.field == "ppda"

    def test_empty_team_raises_error(self):
        """空のチーム名でエラーが発生する"""
        with pytest.raises(ValidationError) as exc_info:
            TeamStats(match_id="t", team="", is_home=True)
        assert exc_info.value.field == "team"

    def test_from_dict_and_to_dict(self):
        """辞書変換が正しく動作する"""
        stats = TeamStats(
            match_id="m1",
            team="Team A",
            is_home=True,
            goals=2,
            xg=1.5,
            shots=10,
            shots_on_target=5,
            possession=60.0,
        )

        data = stats.to_dict()
        restored = TeamStats.from_dict(data)

        assert restored.team == stats.team
        assert restored.goals == stats.goals
        assert restored.xg == stats.xg


class TestPrediction:
    """Predictionモデルのテスト"""

    def test_create_valid_prediction(self):
        """有効な予測を作成できる"""
        pred = Prediction(
            round_number=1607,
            team="Yokohama F. Marinos",
            prob_0=0.18,
            prob_1=0.32,
            prob_2=0.28,
            prob_3plus=0.22,
        )

        assert pred.team == "Yokohama F. Marinos"
        assert abs(sum([pred.prob_0, pred.prob_1, pred.prob_2, pred.prob_3plus]) - 1.0) < 0.01

    def test_invalid_probability_range_raises_error(self):
        """確率範囲外でエラーが発生する"""
        with pytest.raises(ValidationError):
            Prediction(
                round_number=1607,
                team="Team A",
                prob_0=1.5,  # 範囲外
                prob_1=0.0,
                prob_2=0.0,
                prob_3plus=0.0,
            )

    def test_probability_sum_validation(self):
        """確率合計が100%でないとエラーが発生する"""
        with pytest.raises(ValidationError):
            Prediction(
                round_number=1607,
                team="Team A",
                prob_0=0.5,
                prob_1=0.5,
                prob_2=0.5,
                prob_3plus=0.5,  # 合計200%
            )

    def test_get_most_likely_category(self):
        """最も確率が高いカテゴリが取得できる"""
        pred = Prediction(
            round_number=1607,
            team="Team A",
            prob_0=0.10,
            prob_1=0.50,
            prob_2=0.25,
            prob_3plus=0.15,
        )

        assert pred.get_most_likely_category() == "1"

    def test_expected_goals(self):
        """期待得点が正しく計算される"""
        pred = Prediction(
            round_number=1607,
            team="Team A",
            prob_0=1.0,
            prob_1=0.0,
            prob_2=0.0,
            prob_3plus=0.0,
        )

        assert pred.expected_goals == 0.0


class TestVoteRate:
    """VoteRateモデルのテスト"""

    def test_create_valid_vote_rate(self):
        """有効な投票率を作成できる"""
        vr = VoteRate(
            round_number=1607,
            team="Yokohama F. Marinos",
            vote_0=0.22,
            vote_1=0.35,
            vote_2=0.25,
            vote_3plus=0.18,
        )

        assert vr.team == "Yokohama F. Marinos"
        assert abs(sum([vr.vote_0, vr.vote_1, vr.vote_2, vr.vote_3plus]) - 1.0) < 0.05

    def test_invalid_vote_rate_raises_error(self):
        """不正な投票率でエラーが発生する"""
        with pytest.raises(ValidationError):
            VoteRate(
                round_number=1607,
                team="Team A",
                vote_0=1.5,
                vote_1=0.0,
                vote_2=0.0,
                vote_3plus=0.0,
            )

    def test_get_most_voted_category(self):
        """最も投票率が高いカテゴリが取得できる"""
        vr = VoteRate(
            round_number=1607,
            team="Team A",
            vote_0=0.10,
            vote_1=0.50,
            vote_2=0.25,
            vote_3plus=0.15,
        )

        assert vr.get_most_voted_category() == "1"


class TestRecommendation:
    """Recommendationモデルのテスト"""

    def test_create_valid_recommendation(self):
        """有効な推奨を作成できる"""
        rec = Recommendation(
            round_number=1607,
            team="Yokohama F. Marinos",
            category="3+",
            model_prob=0.25,
            vote_rate=0.16,
            value_score=1.56,
            action="買い",
            kelly_fraction=0.05,
            confidence="high",
        )

        assert rec.team == "Yokohama F. Marinos"
        assert rec.is_value_bet is True
        assert rec.is_recommended is True

    def test_is_value_bet_false_when_low_score(self):
        """バリュースコアが低い場合はバリューベットではない"""
        rec = Recommendation(
            round_number=1607,
            team="Team A",
            category="0",
            model_prob=0.10,
            vote_rate=0.20,
            value_score=0.50,
            action="スキップ",
        )

        assert rec.is_value_bet is False

    def test_get_summary(self):
        """サマリーが正しく生成される"""
        rec = Recommendation(
            round_number=1607,
            team="Team A",
            category="1",
            model_prob=0.30,
            vote_rate=0.20,
            value_score=1.50,
            action="買い",
        )

        summary = rec.get_summary()
        assert "Team A" in summary
        assert "1点" in summary
        assert "買い" in summary

    def test_from_dict_and_to_dict(self):
        """辞書変換が正しく動作する"""
        rec = Recommendation(
            round_number=1607,
            team="Team A",
            category="1",
            model_prob=0.30,
            vote_rate=0.20,
            value_score=1.50,
            action="買い",
            kelly_fraction=0.05,
            confidence="high",
        )

        data = rec.to_dict()
        restored = Recommendation.from_dict(data)

        assert restored.team == rec.team
        assert restored.model_prob == rec.model_prob
        assert restored.confidence == rec.confidence

    def test_expected_value(self):
        """期待値が正しく計算される"""
        rec = Recommendation(
            round_number=1607,
            team="Team A",
            category="1",
            model_prob=0.30,
            vote_rate=0.20,
            value_score=1.50,
            action="買い",
        )

        # expected_value = model_prob * (1 / vote_rate * 0.5)
        # = 0.30 * (1 / 0.20 * 0.5) = 0.30 * 2.5 = 0.75
        assert rec.expected_value == pytest.approx(0.75, abs=0.01)

    def test_expected_value_zero_vote_rate(self):
        """投票率0の場合は期待値0"""
        rec = Recommendation(
            round_number=1607,
            team="Team A",
            category="1",
            model_prob=0.30,
            vote_rate=0.0,
            value_score=0.0,
            action="スキップ",
        )

        assert rec.expected_value == 0.0

    def test_is_recommended_for_all_actions(self):
        """各アクションの推奨判定"""
        for action, expected in [
            ("必買", True),
            ("買い", True),
            ("検討", True),
            ("慎重", False),
            ("スキップ", False),
        ]:
            rec = Recommendation(
                round_number=1607,
                team="Team A",
                category="1",
                model_prob=0.30,
                vote_rate=0.20,
                value_score=1.50,
                action=action,
            )
            assert rec.is_recommended == expected, f"action={action}"
