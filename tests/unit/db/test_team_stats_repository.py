"""TeamStatsRepositoryのテスト"""

from datetime import datetime

import pytest

from toto_predictor.db.database import Database
from toto_predictor.db.repositories.match_repository import MatchRepository
from toto_predictor.db.repositories.team_stats_repository import TeamStatsRepository
from toto_predictor.models.exceptions import DataNotFoundError
from toto_predictor.models.match import Match
from toto_predictor.models.team_stats import TeamStats


class TestTeamStatsRepositorySave:
    """save()テスト"""

    @pytest.fixture
    def db_with_match(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        match_repo = MatchRepository(db)
        match = Match(
            date=datetime(2025, 1, 1),
            season=2025,
            competition="J1 League",
            home_team="Marinos",
            away_team="Frontale",
            home_goals=2,
            away_goals=1,
        )
        match_repo.save(match)
        return db, match

    def test_save_and_find_by_id(self, db_with_match):
        """保存と検索"""
        db, match = db_with_match
        repo = TeamStatsRepository(db)

        stats = TeamStats(
            match_id=match.id,
            team="Marinos",
            is_home=True,
            goals=2,
            xg=1.8,
            shots=15,
            shots_on_target=8,
            possession=55.0,
        )

        repo.save(stats)

        found = repo.find_by_id(stats.id)
        assert found is not None
        assert found.team == "Marinos"
        assert found.goals == 2
        assert found.xg == 1.8

    def test_find_by_id_not_found(self, db_with_match):
        """見つからない場合"""
        db, _ = db_with_match
        repo = TeamStatsRepository(db)

        found = repo.find_by_id("nonexistent")
        assert found is None


class TestTeamStatsRepositorySaveMany:
    """save_many()テスト"""

    @pytest.fixture
    def db_with_matches(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        match_repo = MatchRepository(db)
        matches = []

        for i in range(5):
            match = Match(
                date=datetime(2025, 1, i + 1),
                season=2025,
                competition="J1 League",
                home_team="Marinos",
                away_team="Frontale",
                home_goals=i,
                away_goals=0,
            )
            match_repo.save(match)
            matches.append(match)

        return db, matches

    def test_save_many(self, db_with_matches):
        """バッチ保存"""
        db, matches = db_with_matches
        repo = TeamStatsRepository(db)

        stats_list = [
            TeamStats(
                match_id=m.id,
                team="Marinos",
                is_home=True,
                goals=i,
                xg=1.0 + i * 0.1,
            )
            for i, m in enumerate(matches)
        ]

        count = repo.save_many(stats_list)

        assert count == 5
        assert repo.count() == 5

    def test_save_many_empty(self, db_with_matches):
        """空リスト"""
        db, _ = db_with_matches
        repo = TeamStatsRepository(db)

        count = repo.save_many([])
        assert count == 0


class TestTeamStatsRepositoryFind:
    """検索テスト"""

    @pytest.fixture
    def populated_repo(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        match_repo = MatchRepository(db)
        stats_repo = TeamStatsRepository(db)

        # 試合とチーム統計を作成
        for i in range(5):
            match = Match(
                date=datetime(2025, 1, i + 1),
                season=2025,
                competition="J1 League",
                home_team="Marinos",
                away_team="Frontale",
                home_goals=i,
                away_goals=0,
            )
            match_repo.save(match)

            stats_home = TeamStats(
                match_id=match.id,
                team="Marinos",
                is_home=True,
                goals=i,
                xg=1.0 + i * 0.2,
                shots=10 + i,
            )
            stats_away = TeamStats(
                match_id=match.id,
                team="Frontale",
                is_home=False,
                goals=0,
                xg=0.5,
                shots=5,
            )
            stats_repo.save(stats_home)
            stats_repo.save(stats_away)

        return stats_repo

    def test_find_by_match_id(self, populated_repo):
        """試合IDで検索"""
        # 任意の試合を取得
        all_stats = populated_repo.find_by_team("Marinos")
        match_id = all_stats[0].match_id

        stats = populated_repo.find_by_match_id(match_id)

        assert len(stats) == 2  # ホーム/アウェイ

    def test_find_by_team(self, populated_repo):
        """チームで検索"""
        stats = populated_repo.find_by_team("Marinos")

        assert len(stats) == 5
        assert all(s.team == "Marinos" for s in stats)

    def test_find_by_team_with_limit(self, populated_repo):
        """チームで検索（件数制限）"""
        stats = populated_repo.find_by_team("Marinos", limit=3)
        assert len(stats) == 3

    def test_find_by_team_with_before_date(self, populated_repo):
        """チームで検索（日付前）"""
        stats = populated_repo.find_by_team("Marinos", before_date=datetime(2025, 1, 3))
        assert len(stats) == 2

    def test_find_by_team_and_match(self, populated_repo):
        """チームと試合IDで検索"""
        # 任意の試合を取得
        all_stats = populated_repo.find_by_team("Marinos")
        match_id = all_stats[0].match_id

        found = populated_repo.find_by_team_and_match("Marinos", match_id)

        assert found is not None
        assert found.team == "Marinos"
        assert found.match_id == match_id

    def test_find_by_team_and_match_not_found(self, populated_repo):
        """見つからない場合"""
        found = populated_repo.find_by_team_and_match("Marinos", "nonexistent")
        assert found is None


class TestTeamStatsRepositoryCount:
    """カウントテスト"""

    @pytest.fixture
    def populated_repo(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        match_repo = MatchRepository(db)
        stats_repo = TeamStatsRepository(db)

        for i in range(5):
            match = Match(
                date=datetime(2025, 1, i + 1),
                season=2025,
                competition="J1 League",
                home_team="Marinos",
                away_team="Frontale",
            )
            match_repo.save(match)

            stats_home = TeamStats(match_id=match.id, team="Marinos", is_home=True)
            stats_away = TeamStats(match_id=match.id, team="Frontale", is_home=False)
            stats_repo.save(stats_home)
            stats_repo.save(stats_away)

        return stats_repo

    def test_count(self, populated_repo):
        """総数"""
        assert populated_repo.count() == 10

    def test_count_by_team(self, populated_repo):
        """チーム別カウント"""
        assert populated_repo.count_by_team("Marinos") == 5
        assert populated_repo.count_by_team("Frontale") == 5
        assert populated_repo.count_by_team("Unknown") == 0


class TestTeamStatsRepositoryGetTeams:
    """get_teams()テスト"""

    def test_get_teams(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        match_repo = MatchRepository(db)
        stats_repo = TeamStatsRepository(db)

        match = Match(
            date=datetime(2025, 1, 1),
            season=2025,
            competition="J1 League",
            home_team="Marinos",
            away_team="Frontale",
        )
        match_repo.save(match)

        stats_home = TeamStats(match_id=match.id, team="Marinos", is_home=True)
        stats_away = TeamStats(match_id=match.id, team="Frontale", is_home=False)
        stats_repo.save(stats_home)
        stats_repo.save(stats_away)

        teams = stats_repo.get_teams()
        assert len(teams) == 2
        assert "Marinos" in teams
        assert "Frontale" in teams


class TestTeamStatsRepositoryDelete:
    """delete()テスト"""

    @pytest.fixture
    def repo_with_data(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        match_repo = MatchRepository(db)
        stats_repo = TeamStatsRepository(db)

        match = Match(
            date=datetime(2025, 1, 1),
            season=2025,
            competition="J1 League",
            home_team="Marinos",
            away_team="Frontale",
        )
        match_repo.save(match)

        stats_home = TeamStats(match_id=match.id, team="Marinos", is_home=True)
        stats_away = TeamStats(match_id=match.id, team="Frontale", is_home=False)
        stats_repo.save(stats_home)
        stats_repo.save(stats_away)

        return stats_repo, stats_home, stats_away, match

    def test_delete(self, repo_with_data):
        """削除"""
        repo, stats_home, _, _ = repo_with_data

        repo.delete(stats_home.id)

        assert repo.find_by_id(stats_home.id) is None
        assert repo.count() == 1

    def test_delete_not_found(self, repo_with_data):
        """見つからない場合エラー"""
        repo, _, _, _ = repo_with_data

        with pytest.raises(DataNotFoundError):
            repo.delete("nonexistent")

    def test_delete_by_match_id(self, repo_with_data):
        """試合IDで削除"""
        repo, _, _, match = repo_with_data

        count = repo.delete_by_match_id(match.id)

        assert count == 2
        assert repo.count() == 0


class TestTeamStatsRepositoryGetAverageStats:
    """get_average_stats()テスト"""

    @pytest.fixture
    def populated_repo(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        match_repo = MatchRepository(db)
        stats_repo = TeamStatsRepository(db)

        for i in range(5):
            match = Match(
                date=datetime(2025, 1, i + 1),
                season=2025,
                competition="J1 League",
                home_team="Marinos",
                away_team="Frontale",
            )
            match_repo.save(match)

            stats = TeamStats(
                match_id=match.id,
                team="Marinos",
                is_home=True,
                goals=i,  # 0, 1, 2, 3, 4 -> avg = 2.0
                xg=1.0 + i * 0.2,  # 1.0, 1.2, 1.4, 1.6, 1.8 -> avg = 1.4
                shots=10,
            )
            stats_repo.save(stats)

        return stats_repo

    def test_get_average_stats(self, populated_repo):
        """平均統計取得"""
        avg = populated_repo.get_average_stats("Marinos", limit=5)

        assert "goals_avg" in avg
        assert avg["goals_avg"] == pytest.approx(2.0, abs=0.01)
        assert avg["xg_avg"] == pytest.approx(1.4, abs=0.01)

    def test_get_average_stats_with_limit(self, populated_repo):
        """制限付き平均統計"""
        # 直近3試合のみ（得点: 2, 3, 4 -> avg = 3.0）
        avg = populated_repo.get_average_stats("Marinos", limit=3)

        assert avg["goals_avg"] == pytest.approx(3.0, abs=0.01)

    def test_get_average_stats_no_data(self, populated_repo):
        """データなし"""
        avg = populated_repo.get_average_stats("Unknown")
        assert avg == {}
