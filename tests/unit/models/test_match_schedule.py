"""対戦カードスケジュールのテスト"""

import json
from pathlib import Path

import pytest

from toto_predictor.models.match_schedule import MatchPair, MatchSchedule


class TestMatchPair:
    """MatchPairのテスト"""

    def test_create_basic(self):
        """基本的な生成"""
        pair = MatchPair(match_index=1, home_team="Team A", away_team="Team B")
        assert pair.match_index == 1
        assert pair.home_team == "Team A"
        assert pair.away_team == "Team B"

    def test_to_dict(self):
        """to_dict()が全フィールドを含むこと"""
        pair = MatchPair(match_index=2, home_team="Kashima Antlers", away_team="Kawasaki Frontale")
        d = pair.to_dict()
        assert d["match_index"] == 2
        assert d["home_team"] == "Kashima Antlers"
        assert d["away_team"] == "Kawasaki Frontale"

    def test_from_dict(self):
        """from_dict()で復元できること"""
        data = {"match_index": 3, "home_team": "Urawa Reds", "away_team": "Tokyo"}
        pair = MatchPair.from_dict(data)
        assert pair.match_index == 3
        assert pair.home_team == "Urawa Reds"


class TestMatchSchedule:
    """MatchScheduleのテスト"""

    @pytest.fixture
    def sample_schedule(self):
        """サンプルスケジュール"""
        return MatchSchedule(
            round_number=1608,
            matches=[
                MatchPair(
                    match_index=1, home_team="Kashima Antlers", away_team="Kawasaki Frontale"
                ),
                MatchPair(match_index=2, home_team="Machida Zelvia", away_team="Tokyo"),
                MatchPair(match_index=3, home_team="Urawa Reds", away_team="Yokohama F. Marinos"),
            ],
        )

    def test_to_dict_and_from_dict(self, sample_schedule):
        """直列化→復元のラウンドトリップ"""
        d = sample_schedule.to_dict()
        restored = MatchSchedule.from_dict(d)
        assert restored.round_number == 1608
        assert len(restored.matches) == 3
        assert restored.matches[0].home_team == "Kashima Antlers"

    def test_to_json_and_from_json(self, sample_schedule, tmp_path):
        """JSON保存→読み込みのラウンドトリップ"""
        json_path = str(tmp_path / "schedule.json")
        sample_schedule.to_json(json_path)

        assert Path(json_path).exists()
        restored = MatchSchedule.from_json(json_path)
        assert restored.round_number == 1608
        assert len(restored.matches) == 3

    def test_from_matches_str(self):
        """--matches文字列からの生成"""
        matches_str = (
            "Kashima Antlers:Kawasaki Frontale,Machida Zelvia:Tokyo,Urawa Reds:Yokohama F. Marinos"
        )
        schedule = MatchSchedule.from_matches_str(matches_str, round_number=1608)
        assert schedule.round_number == 1608
        assert len(schedule.matches) == 3
        assert schedule.matches[0].match_index == 1
        assert schedule.matches[0].home_team == "Kashima Antlers"
        assert schedule.matches[0].away_team == "Kawasaki Frontale"
        assert schedule.matches[2].match_index == 3

    def test_from_matches_str_with_spaces(self):
        """空白を含む--matches文字列"""
        schedule = MatchSchedule.from_matches_str(" Team A : Team B , Team C : Team D ")
        assert len(schedule.matches) == 2
        assert schedule.matches[0].home_team == "Team A"
        assert schedule.matches[0].away_team == "Team B"

    def test_from_matches_str_invalid_pair_skipped(self):
        """コロンのないペアはスキップされること"""
        schedule = MatchSchedule.from_matches_str("TeamA:TeamB,InvalidPair,TeamC:TeamD")
        assert len(schedule.matches) == 2

    def test_get_team_info_home(self, sample_schedule):
        """ホームチームの情報取得"""
        info = sample_schedule.get_team_info("Kashima Antlers")
        assert info is not None
        match_index, opponent, is_home = info
        assert match_index == 1
        assert opponent == "Kawasaki Frontale"
        assert is_home is True

    def test_get_team_info_away(self, sample_schedule):
        """アウェイチームの情報取得"""
        info = sample_schedule.get_team_info("Tokyo")
        assert info is not None
        match_index, opponent, is_home = info
        assert match_index == 2
        assert opponent == "Machida Zelvia"
        assert is_home is False

    def test_get_team_info_not_found(self, sample_schedule):
        """存在しないチームはNoneが返ること"""
        assert sample_schedule.get_team_info("Unknown FC") is None

    def test_empty_schedule(self):
        """空のスケジュール"""
        schedule = MatchSchedule(round_number=1608)
        assert len(schedule.matches) == 0
        assert schedule.get_team_info("Any Team") is None
