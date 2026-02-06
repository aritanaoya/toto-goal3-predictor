"""Databaseのテスト"""

import sqlite3

import pytest

from toto_predictor.db.database import Database


class TestDatabaseInit:
    """初期化テスト"""

    def test_init_creates_tables(self, tmp_path):
        """テーブルが作成される"""
        db = Database(str(tmp_path / "test.db"))

        assert db.table_exists("matches")
        assert db.table_exists("team_stats")

    def test_init_creates_directory(self, tmp_path):
        """親ディレクトリが作成される"""
        db_path = tmp_path / "subdir" / "test.db"
        Database(str(db_path))  # 初期化でディレクトリ作成

        assert db_path.parent.exists()


class TestDatabaseGetConnection:
    """get_connection()テスト"""

    def test_get_connection_commits_on_success(self, tmp_path):
        """成功時にコミット"""
        db = Database(str(tmp_path / "test.db"))

        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO matches (id, date, season, competition, home_team, away_team) "
                "VALUES ('test', '2025-01-01', 2025, 'Test', 'Home', 'Away')"
            )

        # データが永続化されている
        rows = db.execute("SELECT * FROM matches WHERE id = 'test'")
        assert len(rows) == 1

    def test_get_connection_rollbacks_on_error(self, tmp_path):
        """エラー時にロールバック"""
        db = Database(str(tmp_path / "test.db"))

        # まず1件挿入
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO matches (id, date, season, competition, home_team, away_team) "
                "VALUES ('test1', '2025-01-01', 2025, 'Test', 'Home', 'Away')"
            )

        # エラーを発生させる
        with pytest.raises(sqlite3.IntegrityError):
            with db.get_connection() as conn:
                # 成功する挿入
                conn.execute(
                    "INSERT INTO matches (id, date, season, competition, home_team, away_team) "
                    "VALUES ('test2', '2025-01-02', 2025, 'Test', 'Home', 'Away')"
                )
                # 重複IDで失敗
                conn.execute(
                    "INSERT INTO matches (id, date, season, competition, home_team, away_team) "
                    "VALUES ('test1', '2025-01-03', 2025, 'Test', 'Home', 'Away')"
                )

        # test2はロールバックされている
        rows = db.execute("SELECT * FROM matches WHERE id = 'test2'")
        assert len(rows) == 0


class TestDatabaseExecute:
    """execute()テスト"""

    def test_execute_select(self, tmp_path):
        """SELECT実行"""
        db = Database(str(tmp_path / "test.db"))

        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO matches (id, date, season, competition, home_team, away_team) "
                "VALUES ('m1', '2025-01-01', 2025, 'Test', 'Home', 'Away')"
            )

        rows = db.execute("SELECT * FROM matches")
        assert len(rows) == 1
        assert rows[0]["id"] == "m1"

    def test_execute_with_params(self, tmp_path):
        """パラメータ付きSELECT"""
        db = Database(str(tmp_path / "test.db"))

        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO matches (id, date, season, competition, home_team, away_team) "
                "VALUES ('m1', '2025-01-01', 2025, 'Test', 'Home', 'Away')"
            )
            conn.execute(
                "INSERT INTO matches (id, date, season, competition, home_team, away_team) "
                "VALUES ('m2', '2025-01-02', 2024, 'Test', 'Home', 'Away')"
            )

        rows = db.execute("SELECT * FROM matches WHERE season = ?", (2025,))
        assert len(rows) == 1
        assert rows[0]["season"] == 2025


class TestDatabaseExecuteMany:
    """execute_many()テスト"""

    def test_execute_many(self, tmp_path):
        """バッチ挿入"""
        db = Database(str(tmp_path / "test.db"))

        params_list = [
            ("m1", "2025-01-01", 2025, "Test", "Home1", "Away1"),
            ("m2", "2025-01-02", 2025, "Test", "Home2", "Away2"),
            ("m3", "2025-01-03", 2025, "Test", "Home3", "Away3"),
        ]

        count = db.execute_many(
            "INSERT INTO matches (id, date, season, competition, home_team, away_team) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            params_list,
        )

        assert count == 3
        rows = db.execute("SELECT COUNT(*) as c FROM matches")
        assert rows[0]["c"] == 3


class TestDatabaseTableOperations:
    """テーブル操作テスト"""

    def test_table_exists_true(self, tmp_path):
        """存在するテーブル"""
        db = Database(str(tmp_path / "test.db"))
        assert db.table_exists("matches") is True

    def test_table_exists_false(self, tmp_path):
        """存在しないテーブル"""
        db = Database(str(tmp_path / "test.db"))
        assert db.table_exists("nonexistent") is False

    def test_get_table_count(self, tmp_path):
        """レコード数取得"""
        db = Database(str(tmp_path / "test.db"))

        assert db.get_table_count("matches") == 0

        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO matches (id, date, season, competition, home_team, away_team) "
                "VALUES ('m1', '2025-01-01', 2025, 'Test', 'Home', 'Away')"
            )

        assert db.get_table_count("matches") == 1

    def test_clear_table(self, tmp_path):
        """テーブルクリア"""
        db = Database(str(tmp_path / "test.db"))

        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO matches (id, date, season, competition, home_team, away_team) "
                "VALUES ('m1', '2025-01-01', 2025, 'Test', 'Home', 'Away')"
            )

        assert db.get_table_count("matches") == 1

        db.clear_table("matches")

        assert db.get_table_count("matches") == 0

    def test_vacuum(self, tmp_path):
        """VACUUM実行"""
        db = Database(str(tmp_path / "test.db"))

        # VACUUMはエラーなく実行できればOK
        db.vacuum()
