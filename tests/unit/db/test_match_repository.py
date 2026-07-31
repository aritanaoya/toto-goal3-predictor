"""MatchRepositoryのテスト"""

from datetime import datetime

import pytest

from toto_predictor.db.database import Database
from toto_predictor.db.repositories.match_repository import MatchRepository
from toto_predictor.models.exceptions import DataNotFoundError
from toto_predictor.models.match import Match


class TestMatchRepositorySave:
    """save()テスト"""

    @pytest.fixture
    def repo(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        return MatchRepository(db)

    def test_save_and_find_by_id(self, repo):
        """保存と検索"""
        match = Match(
            date=datetime(2025, 1, 1),
            season=2025,
            competition="J1 League",
            home_team="Team A",
            away_team="Team B",
            home_goals=2,
            away_goals=1,
        )

        repo.save(match)

        found = repo.find_by_id(match.id)
        assert found is not None
        assert found.home_team == "Team A"
        assert found.away_team == "Team B"
        assert found.home_goals == 2

    def test_save_update_existing(self, repo):
        """既存データの更新"""
        match = Match(
            date=datetime(2025, 1, 1),
            season=2025,
            competition="J1 League",
            home_team="Team A",
            away_team="Team B",
            home_goals=2,
            away_goals=1,
        )

        repo.save(match)

        # 同じIDで更新
        match.home_goals = 3
        repo.save(match)

        found = repo.find_by_id(match.id)
        assert found.home_goals == 3

    def test_find_by_id_not_found(self, repo):
        """見つからない場合"""
        found = repo.find_by_id("nonexistent")
        assert found is None


class TestMatchRepositorySaveMany:
    """save_many()テスト"""

    @pytest.fixture
    def repo(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        return MatchRepository(db)

    def test_save_many(self, repo):
        """バッチ保存"""
        matches = [
            Match(
                date=datetime(2025, 1, i),
                season=2025,
                competition="J1 League",
                home_team=f"Home{i}",
                away_team=f"Away{i}",
                home_goals=i,
                away_goals=0,
            )
            for i in range(1, 6)
        ]

        count = repo.save_many(matches)

        assert count == 5
        assert repo.count() == 5

    def test_save_many_empty(self, repo):
        """空リスト"""
        count = repo.save_many([])
        assert count == 0


class TestMatchRepositoryFind:
    """検索テスト"""

    @pytest.fixture
    def populated_repo(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        repo = MatchRepository(db)

        matches = [
            Match(
                date=datetime(2025, 1, 1),
                season=2025,
                competition="J1 League",
                home_team="Marinos",
                away_team="Frontale",
                home_goals=2,
                away_goals=1,
            ),
            Match(
                date=datetime(2025, 1, 8),
                season=2025,
                competition="J1 League",
                home_team="Frontale",
                away_team="Antlers",
                home_goals=1,
                away_goals=1,
            ),
            Match(
                date=datetime(2024, 12, 1),
                season=2024,
                competition="J1 League",
                home_team="Marinos",
                away_team="Antlers",
                home_goals=3,
                away_goals=0,
            ),
        ]

        for m in matches:
            repo.save(m)

        return repo

    def test_find_by_teams_and_date(self, populated_repo):
        """チームと日付で検索"""
        found = populated_repo.find_by_teams_and_date("Marinos", "Frontale", datetime(2025, 1, 1))

        assert found is not None
        assert found.home_team == "Marinos"
        assert found.away_team == "Frontale"

    def test_find_by_teams_and_date_not_found(self, populated_repo):
        """見つからない場合"""
        found = populated_repo.find_by_teams_and_date("Marinos", "Frontale", datetime(2025, 1, 2))
        assert found is None

    def test_find_by_team(self, populated_repo):
        """チームで検索"""
        matches = populated_repo.find_by_team("Marinos")

        assert len(matches) == 2
        # 日付降順
        assert matches[0].date > matches[1].date

    def test_find_by_team_with_limit(self, populated_repo):
        """チームで検索（件数制限）"""
        matches = populated_repo.find_by_team("Marinos", limit=1)
        assert len(matches) == 1

    def test_find_by_team_with_before_date(self, populated_repo):
        """チームで検索（日付前）"""
        matches = populated_repo.find_by_team("Marinos", before_date=datetime(2025, 1, 1))
        assert len(matches) == 1
        assert matches[0].date.year == 2024

    def test_find_by_season(self, populated_repo):
        """シーズンで検索"""
        matches = populated_repo.find_by_season(2025)
        assert len(matches) == 2

        matches_2024 = populated_repo.find_by_season(2024)
        assert len(matches_2024) == 1

    def test_find_all(self, populated_repo):
        """全件検索"""
        matches = populated_repo.find_all()
        assert len(matches) == 3

    def test_find_all_with_limit(self, populated_repo):
        """全件検索（件数制限）"""
        matches = populated_repo.find_all(limit=2)
        assert len(matches) == 2


class TestMatchRepositoryCount:
    """カウントテスト"""

    @pytest.fixture
    def populated_repo(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        repo = MatchRepository(db)

        matches = [
            Match(
                date=datetime(2025, 1, i),
                season=2025,
                competition="J1 League",
                home_team="Marinos" if i % 2 == 0 else "Frontale",
                away_team="Frontale" if i % 2 == 0 else "Marinos",
                home_goals=i,
                away_goals=0,
            )
            for i in range(1, 11)
        ]

        for m in matches:
            repo.save(m)

        return repo

    def test_count(self, populated_repo):
        """総数"""
        assert populated_repo.count() == 10

    def test_count_by_team(self, populated_repo):
        """チーム別カウント"""
        assert populated_repo.count_by_team("Marinos") == 10
        assert populated_repo.count_by_team("Frontale") == 10
        assert populated_repo.count_by_team("Unknown") == 0


class TestMatchRepositoryGetTeams:
    """get_teams()テスト"""

    def test_get_teams(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        repo = MatchRepository(db)

        matches = [
            Match(
                date=datetime(2025, 1, 1),
                season=2025,
                competition="J1 League",
                home_team="Marinos",
                away_team="Frontale",
            ),
            Match(
                date=datetime(2025, 1, 2),
                season=2025,
                competition="J1 League",
                home_team="Antlers",
                away_team="Reds",
            ),
        ]

        for m in matches:
            repo.save(m)

        teams = repo.get_teams()
        assert len(teams) == 4
        assert "Marinos" in teams
        assert "Frontale" in teams
        # アルファベット順
        assert teams == sorted(teams)


class TestMatchRepositoryDelete:
    """delete()テスト"""

    @pytest.fixture
    def repo(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        return MatchRepository(db)

    def test_delete(self, repo):
        """削除"""
        match = Match(
            date=datetime(2025, 1, 1),
            season=2025,
            competition="J1 League",
            home_team="Team A",
            away_team="Team B",
        )
        repo.save(match)

        assert repo.exists(match.id)

        repo.delete(match.id)

        assert not repo.exists(match.id)

    def test_delete_not_found(self, repo):
        """見つからない場合エラー"""
        with pytest.raises(DataNotFoundError):
            repo.delete("nonexistent")


class TestMatchRepositoryExists:
    """exists()テスト"""

    @pytest.fixture
    def repo(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        return MatchRepository(db)

    def test_exists_true(self, repo):
        """存在する場合"""
        match = Match(
            date=datetime(2025, 1, 1),
            season=2025,
            competition="J1 League",
            home_team="Team A",
            away_team="Team B",
        )
        repo.save(match)

        assert repo.exists(match.id) is True

    def test_exists_false(self, repo):
        """存在しない場合"""
        assert repo.exists("nonexistent") is False
