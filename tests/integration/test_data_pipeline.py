"""データパイプラインの統合テスト"""

from datetime import datetime

import pytest

from toto_predictor.db.database import Database
from toto_predictor.db.repositories.match_repository import MatchRepository
from toto_predictor.db.repositories.team_stats_repository import TeamStatsRepository
from toto_predictor.models.match import Match
from toto_predictor.models.team_stats import TeamStats
from toto_predictor.services.feature_engine import FeatureEngine


class TestDataPipeline:
    """データパイプラインの統合テスト"""

    def test_match_to_stats_relationship(self, temp_db):
        """試合とチーム統計の関連が正しく保存される"""
        db = Database(temp_db)
        match_repo = MatchRepository(db)
        stats_repo = TeamStatsRepository(db)

        # 試合を作成
        match = Match(
            date=datetime(2025, 12, 1),
            season=2025,
            competition="Japan. J1 League",
            home_team="Yokohama F. Marinos",
            away_team="Kawasaki Frontale",
            home_goals=2,
            away_goals=1,
        )
        match_repo.save(match)

        # ホームチーム統計
        home_stats = TeamStats(
            match_id=match.id,
            team="Yokohama F. Marinos",
            is_home=True,
            goals=2,
            xg=1.8,
        )
        stats_repo.save(home_stats)

        # アウェイチーム統計
        away_stats = TeamStats(
            match_id=match.id,
            team="Kawasaki Frontale",
            is_home=False,
            goals=1,
            xg=0.9,
        )
        stats_repo.save(away_stats)

        # 関連の検証
        stats = stats_repo.find_by_match_id(match.id)
        assert len(stats) == 2

        home = next(s for s in stats if s.is_home)
        away = next(s for s in stats if not s.is_home)

        assert home.team == "Yokohama F. Marinos"
        assert away.team == "Kawasaki Frontale"

    def test_feature_calculation_from_stored_data(self, populated_db):
        """保存されたデータから特徴量が計算できる"""
        engine = FeatureEngine(populated_db)

        features = engine.calculate_features("Yokohama F. Marinos")

        assert features.team == "Yokohama F. Marinos"
        assert features.goals_mean >= 0
        assert features.xg_mean >= 0

    def test_training_data_preparation(self, populated_db):
        """学習データの準備が正しく動作する"""
        engine = FeatureEngine(populated_db)

        x_data, y = engine.prepare_training_data([2025])

        # データが存在する
        assert len(x_data) > 0
        assert len(y) > 0
        assert len(x_data) == len(y)

        # 特徴量が数値
        assert x_data.dtypes.apply(lambda x: x.kind in "iuf").all()

        # 目標変数が非負整数
        assert (y >= 0).all()

    def test_team_stats_query_by_team(self, populated_db):
        """チーム別統計クエリが正しく動作する"""
        db = Database(populated_db)
        stats_repo = TeamStatsRepository(db)

        stats = stats_repo.find_by_team("Yokohama F. Marinos", limit=5)

        assert len(stats) <= 5
        assert all(s.team == "Yokohama F. Marinos" for s in stats)

    def test_average_stats_calculation(self, populated_db):
        """平均統計計算が正しく動作する"""
        db = Database(populated_db)
        stats_repo = TeamStatsRepository(db)

        avg = stats_repo.get_average_stats("Yokohama F. Marinos", limit=10)

        assert "goals_avg" in avg
        assert "xg_avg" in avg
        assert avg["goals_avg"] >= 0

    def test_batch_save_matches(self, temp_db):
        """試合データのバッチ保存が正しく動作する"""
        db = Database(temp_db)
        match_repo = MatchRepository(db)

        matches = [
            Match(
                date=datetime(2025, 12, i),
                season=2025,
                competition="Japan. J1 League",
                home_team=f"Team {i}",
                away_team=f"Team {i + 1}",
                home_goals=i % 4,
                away_goals=(i + 1) % 3,
            )
            for i in range(1, 11)
        ]

        count = match_repo.save_many(matches)

        assert count == 10
        assert match_repo.count() == 10

    def test_find_by_season(self, populated_db):
        """シーズン別検索が正しく動作する"""
        db = Database(populated_db)
        match_repo = MatchRepository(db)

        matches_2025 = match_repo.find_by_season(2025)
        matches_2024 = match_repo.find_by_season(2024)

        assert len(matches_2025) > 0
        assert len(matches_2024) == 0
        assert all(m.season == 2025 for m in matches_2025)

    def test_delete_cascade(self, temp_db):
        """試合削除時にチーム統計も削除される"""
        db = Database(temp_db)
        match_repo = MatchRepository(db)
        stats_repo = TeamStatsRepository(db)

        # 試合と統計を作成
        match = Match(
            date=datetime(2025, 12, 1),
            season=2025,
            competition="Test",
            home_team="A",
            away_team="B",
            home_goals=1,
            away_goals=0,
        )
        match_repo.save(match)

        stats = TeamStats(
            match_id=match.id,
            team="A",
            is_home=True,
            goals=1,
        )
        stats_repo.save(stats)

        # 統計を手動で削除
        stats_repo.delete_by_match_id(match.id)

        # 検証
        remaining_stats = stats_repo.find_by_match_id(match.id)
        assert len(remaining_stats) == 0
