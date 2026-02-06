"""データベース接続管理

このモジュールは、SQLiteデータベースへの接続管理とテーブル作成を提供します。
"""

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:
    """SQLiteデータベース接続管理クラス

    データベースへの接続、テーブル作成、トランザクション管理を提供します。

    Attributes:
        db_path: データベースファイルのパス
    """

    SCHEMA = """
    -- 試合テーブル
    CREATE TABLE IF NOT EXISTS matches (
        id TEXT PRIMARY KEY,
        date DATE NOT NULL,
        season INTEGER NOT NULL,
        competition TEXT NOT NULL,
        home_team TEXT NOT NULL,
        away_team TEXT NOT NULL,
        home_goals INTEGER,
        away_goals INTEGER,
        duration INTEGER DEFAULT 90,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- チーム統計テーブル
    CREATE TABLE IF NOT EXISTS team_stats (
        id TEXT PRIMARY KEY,
        match_id TEXT NOT NULL,
        team TEXT NOT NULL,
        is_home BOOLEAN NOT NULL,
        goals INTEGER DEFAULT 0,
        xg REAL DEFAULT 0.0,
        shots INTEGER DEFAULT 0,
        shots_on_target INTEGER DEFAULT 0,
        possession REAL DEFAULT 50.0,
        passes INTEGER DEFAULT 0,
        passes_accurate INTEGER DEFAULT 0,
        crosses INTEGER DEFAULT 0,
        crosses_accurate INTEGER DEFAULT 0,
        pen_area_entries INTEGER DEFAULT 0,
        conceded_goals INTEGER DEFAULT 0,
        xg_against REAL DEFAULT 0.0,
        shots_against INTEGER DEFAULT 0,
        shots_against_on_target INTEGER DEFAULT 0,
        ppda REAL DEFAULT 10.0,
        interceptions INTEGER DEFAULT 0,
        fouls INTEGER DEFAULT 0,
        yellow_cards INTEGER DEFAULT 0,
        red_cards INTEGER DEFAULT 0,
        corners INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE
    );

    -- インデックス
    CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
    CREATE INDEX IF NOT EXISTS idx_matches_season ON matches(season);
    CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(home_team, away_team);
    CREATE INDEX IF NOT EXISTS idx_team_stats_team ON team_stats(team);
    CREATE INDEX IF NOT EXISTS idx_team_stats_match ON team_stats(match_id);
    """

    def __init__(self, db_path: str) -> None:
        """データベース接続を初期化

        Args:
            db_path: データベースファイルのパス（":memory:"でインメモリDB）
        """
        self.db_path = db_path

        # ファイルパスの場合、親ディレクトリを作成
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # テーブルを初期化
        self._init_tables()

    def _init_tables(self) -> None:
        """データベーステーブルを初期化"""
        with self.get_connection() as conn:
            conn.executescript(self.SCHEMA)
            logger.debug("データベーステーブルを初期化しました")

    @contextmanager
    def get_connection(self) -> Iterator[sqlite3.Connection]:
        """データベース接続を取得するコンテキストマネージャー

        トランザクション管理を自動で行い、例外時はロールバックします。

        Yields:
            sqlite3.Connection: データベース接続

        Example:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM matches")
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        """SQLクエリを実行

        Args:
            query: SQLクエリ文字列
            params: クエリパラメータ

        Returns:
            クエリ結果のリスト
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def execute_many(self, query: str, params_list: list[tuple]) -> int:
        """複数のSQLクエリをバッチ実行

        Args:
            query: SQLクエリ文字列
            params_list: パラメータのリスト

        Returns:
            影響を受けた行数
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            return cursor.rowcount

    def table_exists(self, table_name: str) -> bool:
        """テーブルが存在するかチェック

        Args:
            table_name: テーブル名

        Returns:
            テーブルが存在すればTrue
        """
        result = self.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        return len(result) > 0

    def get_table_count(self, table_name: str) -> int:
        """テーブルのレコード数を取得

        Args:
            table_name: テーブル名

        Returns:
            レコード数
        """
        result = self.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        return result[0]["count"] if result else 0

    def clear_table(self, table_name: str) -> None:
        """テーブルのデータを全削除

        Args:
            table_name: テーブル名
        """
        with self.get_connection() as conn:
            conn.execute(f"DELETE FROM {table_name}")
            logger.info(f"テーブル {table_name} のデータを削除しました")

    def vacuum(self) -> None:
        """データベースを最適化"""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
            logger.debug("データベースを最適化しました")
