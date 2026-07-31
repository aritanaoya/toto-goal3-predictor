"""StrategyEngineの拡張メソッドテスト"""

import tempfile
from pathlib import Path

import pytest

from toto_predictor.models.match_schedule import MatchPair, MatchSchedule
from toto_predictor.models.prediction import Prediction
from toto_predictor.models.ticket import TicketRecommendation
from toto_predictor.models.vote_rate import VoteRate
from toto_predictor.services.strategy_engine import StrategyEngine


@pytest.fixture
def sample_predictions():
    """6チーム分のサンプル予測"""
    return [
        Prediction(
            round_number=1607, team="Team A", prob_0=0.15, prob_1=0.35, prob_2=0.30, prob_3plus=0.20
        ),
        Prediction(
            round_number=1607, team="Team B", prob_0=0.25, prob_1=0.30, prob_2=0.25, prob_3plus=0.20
        ),
        Prediction(
            round_number=1607, team="Team C", prob_0=0.10, prob_1=0.25, prob_2=0.35, prob_3plus=0.30
        ),
    ]


@pytest.fixture
def sample_votes():
    """6チーム分のサンプル投票率"""
    return [
        VoteRate(
            round_number=1607, team="Team A", vote_0=0.20, vote_1=0.35, vote_2=0.25, vote_3plus=0.20
        ),
        VoteRate(
            round_number=1607, team="Team B", vote_0=0.22, vote_1=0.38, vote_2=0.22, vote_3plus=0.18
        ),
        VoteRate(
            round_number=1607, team="Team C", vote_0=0.18, vote_1=0.30, vote_2=0.30, vote_3plus=0.22
        ),
    ]


@pytest.fixture
def engine(tmp_path):
    """テスト用StrategyEngine"""
    return StrategyEngine(reports_dir=str(tmp_path / "reports"))


class TestCalculateEvScores:
    """calculate_ev_scores()のテスト"""

    def test_returns_recommendations(self, engine, sample_predictions, sample_votes):
        """Recommendationリストが返ること"""
        recs = engine.calculate_ev_scores(sample_predictions, sample_votes)
        assert len(recs) > 0
        # 3チーム × 4カテゴリ = 12件
        assert len(recs) == 12

    def test_ev_formula_is_correct(self, engine, sample_predictions, sample_votes):
        """EV計算式が正しいこと"""
        recs = engine.calculate_ev_scores(sample_predictions, sample_votes)

        # Team Aの1点を検証: model_prob=0.35, vote_rate=0.35
        team_a_cat1 = [r for r in recs if r.team == "Team A" and r.category == "1"][0]
        expected_ev = 0.35 * (0.49 / 0.35) - 1
        assert team_a_cat1.ev == pytest.approx(expected_ev, abs=0.001)

    def test_contrarian_score_formula(self, engine, sample_predictions, sample_votes):
        """逆張りスコア計算式が正しいこと"""
        recs = engine.calculate_ev_scores(sample_predictions, sample_votes)

        # Team Aの0点: model_prob=0.15, vote_rate=0.20
        team_a_cat0 = [r for r in recs if r.team == "Team A" and r.category == "0"][0]
        expected_contrarian = (0.15 - 0.20) / 0.20
        assert team_a_cat0.contrarian_score == pytest.approx(expected_contrarian, abs=0.001)

    def test_best_ev_for_team_is_marked(self, engine, sample_predictions, sample_votes):
        """各チームの最高EVカテゴリにis_best_ev_for_teamが付くこと"""
        recs = engine.calculate_ev_scores(sample_predictions, sample_votes)

        for team in ["Team A", "Team B", "Team C"]:
            team_recs = [r for r in recs if r.team == team]
            best_ev_recs = [r for r in team_recs if r.is_best_ev_for_team]
            assert len(best_ev_recs) == 1  # 各チームに1つだけ

    def test_sorted_by_ev_descending(self, engine, sample_predictions, sample_votes):
        """EVの降順でソートされること"""
        recs = engine.calculate_ev_scores(sample_predictions, sample_votes)
        evs = [r.ev for r in recs]
        assert evs == sorted(evs, reverse=True)

    def test_missing_vote_rate_team_is_skipped(self, engine, sample_predictions):
        """投票率がないチームはスキップされること"""
        # Team Bの投票率がない
        votes = [
            VoteRate(
                round_number=1607,
                team="Team A",
                vote_0=0.20,
                vote_1=0.35,
                vote_2=0.25,
                vote_3plus=0.20,
            ),
        ]
        recs = engine.calculate_ev_scores(sample_predictions, votes)
        assert len(recs) == 4  # Team Aのみ


class TestGenerateTickets:
    """generate_tickets()のテスト"""

    def test_generates_tickets(self, engine, sample_predictions, sample_votes):
        """チケットが生成されること"""
        tickets = engine.generate_tickets(sample_predictions, sample_votes)
        assert len(tickets) >= 1

    def test_honmei_ticket_uses_most_likely(self, engine, sample_predictions, sample_votes):
        """本命チケットが最頻カテゴリを使用すること"""
        tickets = engine.generate_tickets(sample_predictions, sample_votes)
        honmei = [t for t in tickets if t.ticket_type == "本命"]
        assert len(honmei) == 1

        # Team Aの最頻は1点(0.35)
        team_a_pick = [p for p in honmei[0].picks if p.team == "Team A"]
        assert len(team_a_pick) == 1
        assert team_a_pick[0].category == "1"

    def test_tickets_have_all_teams(self, engine, sample_predictions, sample_votes):
        """各チケットが全チームのピックを含むこと"""
        tickets = engine.generate_tickets(sample_predictions, sample_votes)
        for ticket in tickets:
            assert len(ticket.picks) == 3  # 3チーム

    def test_ticket_properties_are_computed(self, engine, sample_predictions, sample_votes):
        """チケットのプロパティが計算されること"""
        tickets = engine.generate_tickets(sample_predictions, sample_votes)
        for ticket in tickets:
            assert ticket.ticket_prob > 0
            assert ticket.ticket_vote_share > 0
            assert ticket.estimated_payout > 0

    def test_ana_ticket_has_contrarian_picks(self, engine, sample_predictions, sample_votes):
        """穴チケットに逆張り選択が含まれること"""
        tickets = engine.generate_tickets(sample_predictions, sample_votes)
        ana = [t for t in tickets if t.ticket_type == "穴"]
        if ana:
            assert ana[0].contrarian_count > 0

    def test_empty_predictions_returns_empty(self, engine):
        """空の予測で空リストが返ること"""
        tickets = engine.generate_tickets([], [])
        assert tickets == []


class TestGenerateEnhancedReport:
    """generate_enhanced_report()のテスト"""

    def test_generates_report_file(self, engine, sample_predictions, sample_votes, tmp_path):
        """レポートファイルが生成されること"""
        recs = engine.calculate_ev_scores(sample_predictions, sample_votes)
        tickets = engine.generate_tickets(sample_predictions, sample_votes)
        path = engine.generate_enhanced_report(recs, tickets)

        assert Path(path).exists()
        content = Path(path).read_text()
        assert "拡張購入戦略レポート" in content

    def test_report_contains_ticket_section(self, engine, sample_predictions, sample_votes):
        """レポートにチケットセクションが含まれること"""
        recs = engine.calculate_ev_scores(sample_predictions, sample_votes)
        tickets = engine.generate_tickets(sample_predictions, sample_votes)
        path = engine.generate_enhanced_report(recs, tickets)

        content = Path(path).read_text()
        assert "推奨チケット" in content
        assert "本命チケット" in content

    def test_report_contains_ev_analysis(self, engine, sample_predictions, sample_votes):
        """レポートにEV分析セクションが含まれること"""
        recs = engine.calculate_ev_scores(sample_predictions, sample_votes)
        tickets = engine.generate_tickets(sample_predictions, sample_votes)
        path = engine.generate_enhanced_report(recs, tickets)

        content = Path(path).read_text()
        assert "チーム別EV分析" in content

    def test_report_contains_investment_summary(self, engine, sample_predictions, sample_votes):
        """レポートに投資サマリーが含まれること"""
        recs = engine.calculate_ev_scores(sample_predictions, sample_votes)
        tickets = engine.generate_tickets(sample_predictions, sample_votes)
        path = engine.generate_enhanced_report(recs, tickets)

        content = Path(path).read_text()
        assert "投資サマリー" in content

    def test_empty_recommendations_returns_empty(self, engine):
        """空の推奨で空文字列が返ること"""
        path = engine.generate_enhanced_report([], [])
        assert path == ""

    def test_custom_output_path(self, engine, sample_predictions, sample_votes, tmp_path):
        """カスタム出力パスで生成できること"""
        recs = engine.calculate_ev_scores(sample_predictions, sample_votes)
        tickets = engine.generate_tickets(sample_predictions, sample_votes)
        custom_path = str(tmp_path / "custom_report.md")
        path = engine.generate_enhanced_report(recs, tickets, output_path=custom_path)

        assert path == custom_path
        assert Path(path).exists()


class TestGenerateTicketsWithSchedule:
    """generate_tickets() with schedule のテスト"""

    @pytest.fixture
    def sample_schedule(self):
        """サンプルスケジュール（3チーム=1.5試合分なので2試合分に拡張はしない）"""
        return MatchSchedule(
            round_number=1607,
            matches=[
                MatchPair(match_index=1, home_team="Team A", away_team="Team B"),
                MatchPair(match_index=2, home_team="Team C", away_team="Team D"),
            ],
        )

    def test_schedule_enriches_picks(self, engine, sample_predictions, sample_votes):
        """scheduleを渡すとTeamPickにmatch_index等が設定されること"""
        schedule = MatchSchedule(
            round_number=1607,
            matches=[
                MatchPair(match_index=1, home_team="Team A", away_team="Team B"),
                MatchPair(match_index=2, home_team="Team C", away_team="Team D"),
            ],
        )
        tickets = engine.generate_tickets(sample_predictions, sample_votes, schedule=schedule)
        honmei = [t for t in tickets if t.ticket_type == "本命"][0]

        team_a_pick = [p for p in honmei.picks if p.team == "Team A"]
        assert len(team_a_pick) == 1
        assert team_a_pick[0].match_index == 1
        assert team_a_pick[0].opponent == "Team B"
        assert team_a_pick[0].is_home is True

    def test_schedule_none_works_as_before(self, engine, sample_predictions, sample_votes):
        """schedule=Noneの場合は従来通り動作すること"""
        tickets = engine.generate_tickets(sample_predictions, sample_votes, schedule=None)
        assert len(tickets) >= 1
        honmei = [t for t in tickets if t.ticket_type == "本命"][0]
        # match_indexはデフォルトの0
        assert all(p.match_index == 0 for p in honmei.picks)

    def test_all_probs_set_on_picks(self, engine, sample_predictions, sample_votes):
        """all_probsがTeamPickに設定されること"""
        tickets = engine.generate_tickets(sample_predictions, sample_votes, schedule=None)
        honmei = [t for t in tickets if t.ticket_type == "本命"][0]
        team_a_pick = [p for p in honmei.picks if p.team == "Team A"][0]
        assert "0" in team_a_pick.all_probs
        assert "1" in team_a_pick.all_probs
        assert "2" in team_a_pick.all_probs
        assert "3+" in team_a_pick.all_probs
        assert team_a_pick.all_probs["1"] == pytest.approx(0.35)


class TestGenerateMarksheetReport:
    """generate_marksheet_report()のテスト"""

    def test_generates_marksheet_file(self, engine, sample_predictions, sample_votes):
        """マークシートレポートファイルが生成されること"""
        schedule = MatchSchedule(
            round_number=1607,
            matches=[
                MatchPair(match_index=1, home_team="Team A", away_team="Team B"),
                MatchPair(match_index=2, home_team="Team C", away_team="Team D"),
            ],
        )
        tickets = engine.generate_tickets(sample_predictions, sample_votes, schedule=schedule)
        path = engine.generate_marksheet_report(tickets, round_number=1607)

        assert Path(path).exists()
        content = Path(path).read_text()
        assert "マークシート" in content

    def test_marksheet_contains_match_sections(self, engine, sample_predictions, sample_votes):
        """マークシートに試合セクションが含まれること"""
        schedule = MatchSchedule(
            round_number=1607,
            matches=[
                MatchPair(match_index=1, home_team="Team A", away_team="Team B"),
                MatchPair(match_index=2, home_team="Team C", away_team="Team D"),
            ],
        )
        tickets = engine.generate_tickets(sample_predictions, sample_votes, schedule=schedule)
        path = engine.generate_marksheet_report(tickets, round_number=1607)

        content = Path(path).read_text()
        assert "第1試合" in content
        assert "本命チケット" in content

    def test_marksheet_contains_selection_marker(self, engine, sample_predictions, sample_votes):
        """マークシートに◉マーカーが含まれること"""
        schedule = MatchSchedule(
            round_number=1607,
            matches=[
                MatchPair(match_index=1, home_team="Team A", away_team="Team B"),
            ],
        )
        tickets = engine.generate_tickets(sample_predictions, sample_votes, schedule=schedule)
        path = engine.generate_marksheet_report(tickets, round_number=1607)

        content = Path(path).read_text()
        assert "◉" in content

    def test_marksheet_empty_tickets(self, engine):
        """空チケットで空文字列が返ること"""
        path = engine.generate_marksheet_report([], round_number=1607)
        assert path == ""

    def test_marksheet_custom_output_path(self, engine, sample_predictions, sample_votes, tmp_path):
        """カスタム出力パスで生成できること"""
        tickets = engine.generate_tickets(sample_predictions, sample_votes)
        custom_path = str(tmp_path / "custom_marksheet.md")
        path = engine.generate_marksheet_report(tickets, output_path=custom_path, round_number=1607)
        assert path == custom_path
        assert Path(path).exists()


class TestExistingMethodsUnchanged:
    """既存メソッドが変更なく動作することのテスト"""

    def test_calculate_value_scores_still_works(self, engine, sample_predictions, sample_votes):
        """既存のcalculate_value_scoresが動作すること"""
        recs = engine.calculate_value_scores(sample_predictions, sample_votes)
        assert len(recs) == 12  # 3チーム × 4カテゴリ

    def test_generate_report_still_works(self, engine, sample_predictions, sample_votes):
        """既存のgenerate_reportが動作すること"""
        recs = engine.calculate_value_scores(sample_predictions, sample_votes)
        path = engine.generate_report(recs)
        assert Path(path).exists()
