"""Ticketデータモデルのテスト"""

import pytest

from toto_predictor.models.ticket import (
    PAYOUT_RATE,
    TICKET_COST,
    TeamPick,
    TicketRecommendation,
)


@pytest.fixture
def sample_picks():
    """3チーム分のサンプルピック"""
    return [
        TeamPick(team="Team A", category="1", model_prob=0.35, vote_rate=0.30),
        TeamPick(team="Team B", category="2", model_prob=0.28, vote_rate=0.25),
        TeamPick(team="Team C", category="0", model_prob=0.20, vote_rate=0.22, is_contrarian=True),
    ]


class TestTeamPick:
    """TeamPickのテスト"""

    def test_create_basic(self):
        """基本的な生成"""
        pick = TeamPick(team="Team A", category="1", model_prob=0.35, vote_rate=0.30)
        assert pick.team == "Team A"
        assert pick.category == "1"
        assert pick.model_prob == 0.35
        assert pick.vote_rate == 0.30
        assert pick.ev_contribution == 0.0
        assert pick.is_contrarian is False

    def test_to_dict(self):
        """to_dict()が全フィールドを含むこと"""
        pick = TeamPick(
            team="Team A",
            category="3+",
            model_prob=0.15,
            vote_rate=0.10,
            ev_contribution=0.5,
            is_contrarian=True,
        )
        d = pick.to_dict()
        assert d["team"] == "Team A"
        assert d["category"] == "3+"
        assert d["model_prob"] == 0.15
        assert d["is_contrarian"] is True

    def test_from_dict(self):
        """from_dict()で復元できること"""
        data = {
            "team": "Team B",
            "category": "2",
            "model_prob": 0.28,
            "vote_rate": 0.25,
            "ev_contribution": 0.3,
            "is_contrarian": False,
        }
        pick = TeamPick.from_dict(data)
        assert pick.team == "Team B"
        assert pick.model_prob == 0.28

    def test_from_dict_minimal(self):
        """from_dict()で最小限のデータでも復元できること"""
        data = {
            "team": "Team X",
            "category": "0",
            "model_prob": 0.2,
            "vote_rate": 0.25,
        }
        pick = TeamPick.from_dict(data)
        assert pick.ev_contribution == 0.0
        assert pick.is_contrarian is False
        assert pick.match_index == 0
        assert pick.opponent == ""
        assert pick.is_home is True
        assert pick.all_probs == {}

    def test_new_fields_defaults(self):
        """新規フィールドのデフォルト値が後方互換であること"""
        pick = TeamPick(team="Team A", category="1", model_prob=0.35, vote_rate=0.30)
        assert pick.match_index == 0
        assert pick.opponent == ""
        assert pick.is_home is True
        assert pick.all_probs == {}

    def test_new_fields_round_trip(self):
        """新規フィールドを含むto_dict/from_dictラウンドトリップ"""
        pick = TeamPick(
            team="Team A",
            category="1",
            model_prob=0.35,
            vote_rate=0.30,
            match_index=2,
            opponent="Team B",
            is_home=False,
            all_probs={"0": 0.2, "1": 0.35, "2": 0.25, "3+": 0.2},
        )
        d = pick.to_dict()
        restored = TeamPick.from_dict(d)
        assert restored.match_index == 2
        assert restored.opponent == "Team B"
        assert restored.is_home is False
        assert restored.all_probs["1"] == 0.35


class TestTicketRecommendation:
    """TicketRecommendationのテスト"""

    def test_create_basic(self, sample_picks):
        """基本的な生成"""
        ticket = TicketRecommendation(ticket_type="本命", picks=sample_picks)
        assert ticket.ticket_type == "本命"
        assert len(ticket.picks) == 3
        assert ticket.cost == TICKET_COST

    def test_ticket_prob_calculation(self, sample_picks):
        """ticket_probが全チーム確率の積であること"""
        ticket = TicketRecommendation(ticket_type="本命", picks=sample_picks)
        expected = 0.35 * 0.28 * 0.20
        assert ticket.ticket_prob == pytest.approx(expected)

    def test_ticket_vote_share_calculation(self, sample_picks):
        """ticket_vote_shareが投票率の積であること"""
        ticket = TicketRecommendation(ticket_type="本命", picks=sample_picks)
        expected = 0.30 * 0.25 * 0.22
        assert ticket.ticket_vote_share == pytest.approx(expected)

    def test_estimated_payout_calculation(self, sample_picks):
        """estimated_payoutがパリミュチュエル方式で計算されること"""
        ticket = TicketRecommendation(ticket_type="本命", picks=sample_picks)
        vote_share = 0.30 * 0.25 * 0.22
        expected = PAYOUT_RATE / vote_share * TICKET_COST
        assert ticket.estimated_payout == pytest.approx(expected)

    def test_estimated_ev_calculation(self, sample_picks):
        """estimated_evが正しく計算されること"""
        ticket = TicketRecommendation(ticket_type="本命", picks=sample_picks)
        prob = 0.35 * 0.28 * 0.20
        vote_share = 0.30 * 0.25 * 0.22
        payout = PAYOUT_RATE / vote_share * TICKET_COST
        expected_ev = prob * payout - TICKET_COST
        assert ticket.estimated_ev == pytest.approx(expected_ev)

    def test_contrarian_count(self, sample_picks):
        """逆張り数が正しくカウントされること"""
        ticket = TicketRecommendation(ticket_type="穴", picks=sample_picks)
        assert ticket.contrarian_count == 1  # Team Cのみis_contrarian=True

    def test_empty_picks_returns_zero(self):
        """ピックが空の場合にゼロが返ること"""
        ticket = TicketRecommendation(ticket_type="本命")
        assert ticket.ticket_prob == 0.0
        assert ticket.ticket_vote_share == 0.0
        assert ticket.estimated_payout == 0.0

    def test_to_dict_serialization(self, sample_picks):
        """to_dict()でシリアライズできること"""
        ticket = TicketRecommendation(ticket_type="対抗", picks=sample_picks)
        d = ticket.to_dict()

        assert d["ticket_type"] == "対抗"
        assert len(d["picks"]) == 3
        assert "ticket_prob" in d
        assert "estimated_payout" in d
        assert "estimated_ev" in d
        assert d["cost"] == TICKET_COST

    def test_from_dict_deserialization(self, sample_picks):
        """from_dict()でデシリアライズできること"""
        original = TicketRecommendation(ticket_type="穴", picks=sample_picks)
        d = original.to_dict()
        restored = TicketRecommendation.from_dict(d)

        assert restored.ticket_type == "穴"
        assert len(restored.picks) == 3
        assert restored.picks[0].team == "Team A"
        assert restored.ticket_prob == pytest.approx(original.ticket_prob)

    def test_get_summary(self, sample_picks):
        """get_summary()がサマリー文字列を返すこと"""
        ticket = TicketRecommendation(ticket_type="本命", picks=sample_picks)
        summary = ticket.get_summary()
        assert "[本命]" in summary
        assert "的中率=" in summary
        assert "推定払戻=" in summary
        assert "EV=" in summary
