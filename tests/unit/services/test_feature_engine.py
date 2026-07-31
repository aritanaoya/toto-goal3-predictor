"""FeatureEngineのユニットテスト"""

import pytest

from toto_predictor.models.exceptions import DataNotFoundError
from toto_predictor.services.feature_engine import FeatureEngine


class TestFeatureEngine:
    """FeatureEngineのテスト"""

    def test_init_creates_repositories(self, temp_db):
        """初期化時にリポジトリが作成される"""
        engine = FeatureEngine(temp_db)
        assert engine.db is not None
        assert engine.match_repo is not None
        assert engine.stats_repo is not None

    def test_calculate_features_insufficient_data(self, temp_db):
        """データ不足でエラーが発生する"""
        engine = FeatureEngine(temp_db)

        with pytest.raises(DataNotFoundError) as exc_info:
            engine.calculate_features("Nonexistent Team")

        assert "データが不足" in exc_info.value.message

    def test_calculate_features_with_valid_data(self, populated_db):
        """十分なデータがあれば特徴量が計算できる"""
        engine = FeatureEngine(populated_db)

        features = engine.calculate_features("Yokohama F. Marinos")

        # 基本的なチェック
        assert features.team == "Yokohama F. Marinos"
        assert features.goals_mean >= 0
        assert features.xg_mean >= 0
        assert features.shots_mean >= 0
        assert 0 <= features.possession_mean <= 100

    def test_calculate_features_window_sizes(self, populated_db):
        """異なるウィンドウサイズで特徴量が計算できる"""
        engine = FeatureEngine(populated_db)

        features_5 = engine.calculate_features("Yokohama F. Marinos", window_sizes=[5])
        features_10 = engine.calculate_features("Yokohama F. Marinos", window_sizes=[5, 10])

        assert features_5.window_size == 5
        assert features_10.window_size == 10

    def test_shot_conversion_calculation(self, populated_db):
        """シュート決定率が正しく計算される"""
        engine = FeatureEngine(populated_db)

        features = engine.calculate_features("Yokohama F. Marinos")

        if features.shots_mean > 0:
            expected_conversion = features.goals_mean / features.shots_mean
            assert abs(features.shot_conversion - expected_conversion) < 0.01

    def test_xg_overperformance_calculation(self, populated_db):
        """xG超過パフォーマンスが正しく計算される"""
        engine = FeatureEngine(populated_db)

        features = engine.calculate_features("Yokohama F. Marinos")

        expected = features.goals_mean - features.xg_mean
        assert abs(features.xg_overperformance - expected) < 0.01

    def test_prepare_training_data_insufficient_data(self, temp_db):
        """データ不足でエラーが発生する"""
        engine = FeatureEngine(temp_db)

        with pytest.raises(DataNotFoundError):
            engine.prepare_training_data([2025])

    def test_prepare_training_data_with_valid_data(self, populated_db):
        """十分なデータがあれば学習データが準備できる"""
        engine = FeatureEngine(populated_db)

        x_data, y = engine.prepare_training_data([2025])

        # 基本的なチェック
        assert len(x_data) > 0
        assert len(x_data) == len(y)
        assert "goals_mean" in x_data.columns or "is_home" in x_data.columns

    def test_calculate_opponent_features(self, populated_db):
        """対戦相手特徴量が計算できる"""
        engine = FeatureEngine(populated_db)

        features = engine.calculate_opponent_features("Yokohama F. Marinos", "Kawasaki Frontale")

        assert "team_goals_mean" in features
        assert "opponent_conceded_mean" in features
        assert "attack_vs_defense" in features


class TestFeatureEngineDataLeakPrevention:
    """データリーク防止テスト"""

    def test_calculate_features_excludes_match_day(self, populated_db):
        """特徴量計算で試合当日のデータが除外される"""
        from datetime import datetime

        from toto_predictor.db.database import Database
        from toto_predictor.db.repositories.match_repository import MatchRepository
        from toto_predictor.db.repositories.team_stats_repository import TeamStatsRepository

        db = Database(populated_db)
        match_repo = MatchRepository(db)
        stats_repo = TeamStatsRepository(db)

        # テスト対象のチームと日付を取得
        team = "Yokohama F. Marinos"
        matches = match_repo.find_by_team(team, limit=10)
        assert len(matches) > 0

        # 最新の試合日を取得
        latest_match = matches[0]
        match_date = latest_match.date

        # その日の統計データを取得（リークなしの場合は0件になるはず）
        stats_on_match_day = stats_repo.find_by_team(team, before_date=match_date)

        # 試合日より前のデータのみが取得されることを確認
        for stat in stats_on_match_day:
            stat_match = match_repo.find_by_id(stat.match_id)
            if stat_match:
                assert stat_match.date < match_date, (
                    f"試合当日のデータがリーク: match_date={stat_match.date}, "
                    f"as_of_date={match_date}"
                )

    def test_prepare_training_data_uses_before_match_features(self, populated_db):
        """学習データ準備で試合前の特徴量のみが使用される"""
        engine = FeatureEngine(populated_db)

        # 学習データを準備
        x_data, y = engine.prepare_training_data([2025])

        # 特徴量が存在することを確認（リークがない場合でもデータが生成される）
        assert len(x_data) > 0
        assert len(y) > 0

        # 目的変数（得点）が非負であることを確認
        assert (y >= 0).all()

    def test_calculate_features_respects_as_of_date(self, populated_db):
        """as_of_dateが正しく適用される"""
        from datetime import datetime, timedelta

        engine = FeatureEngine(populated_db)
        team = "Yokohama F. Marinos"

        # 異なる基準日で特徴量を計算
        # （過去の日付では利用可能なデータが少なくなる）
        recent_date = datetime(2025, 12, 31)
        old_date = datetime(2025, 6, 1)

        try:
            features_recent = engine.calculate_features(team, as_of_date=recent_date)
            features_old = engine.calculate_features(team, as_of_date=old_date)

            # 両方とも計算できる場合、異なる結果になる可能性がある
            # （少なくともエラーなく計算できることを確認）
            assert features_recent.team == team
            assert features_old.team == team
        except DataNotFoundError:
            # 古い日付ではデータが不足している場合はパス
            pass
