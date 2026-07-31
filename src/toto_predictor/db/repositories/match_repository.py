"""試合データリポジトリ

このモジュールは、試合データのCRUD操作を提供します。
"""

import logging
from datetime import datetime

from ...models.exceptions import DatabaseError, DataNotFoundError
from ...models.match import Match
from ..database import Database

logger = logging.getLogger(__name__)


class MatchRepository:
    """試合データのリポジトリクラス

    Matchデータのデータベース操作を提供します。

    Attributes:
        db: Databaseインスタンス
    """

    def __init__(self, db: Database) -> None:
        """リポジトリを初期化

        Args:
            db: Databaseインスタンス
        """
        self.db = db

    def save(self, match: Match) -> None:
        """試合データを保存

        Args:
            match: 保存するMatchオブジェクト

        Raises:
            DatabaseError: 保存に失敗した場合
        """
        try:
            with self.db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO matches
                    (id, date, season, competition, home_team, away_team,
                     home_goals, away_goals, duration, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        match.id,
                        match.date.isoformat(),
                        match.season,
                        match.competition,
                        match.home_team,
                        match.away_team,
                        match.home_goals,
                        match.away_goals,
                        match.duration,
                        match.created_at.isoformat(),
                    ),
                )
                logger.debug(f"試合データを保存しました: {match.id}")
        except Exception as e:
            raise DatabaseError(f"試合データの保存に失敗しました: {e}") from e

    def save_many(self, matches: list[Match]) -> int:
        """複数の試合データをバッチ保存

        Args:
            matches: 保存するMatchオブジェクトのリスト

        Returns:
            保存した件数

        Raises:
            DatabaseError: 保存に失敗した場合
        """
        if not matches:
            return 0

        try:
            params_list = [
                (
                    m.id,
                    m.date.isoformat(),
                    m.season,
                    m.competition,
                    m.home_team,
                    m.away_team,
                    m.home_goals,
                    m.away_goals,
                    m.duration,
                    m.created_at.isoformat(),
                )
                for m in matches
            ]

            count = self.db.execute_many(
                """
                INSERT OR REPLACE INTO matches
                (id, date, season, competition, home_team, away_team,
                 home_goals, away_goals, duration, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                params_list,
            )
            logger.info(f"{count}件の試合データを保存しました")
            return len(matches)
        except Exception as e:
            raise DatabaseError(f"試合データのバッチ保存に失敗しました: {e}") from e

    def find_by_id(self, match_id: str) -> Match | None:
        """IDで試合データを検索

        Args:
            match_id: 試合ID

        Returns:
            Matchオブジェクト、見つからない場合はNone
        """
        rows = self.db.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
        if not rows:
            return None
        return self._row_to_match(rows[0])

    def find_by_teams_and_date(
        self, home_team: str, away_team: str, date: datetime
    ) -> Match | None:
        """チーム名と日付で試合を検索

        Args:
            home_team: ホームチーム名
            away_team: アウェイチーム名
            date: 試合日

        Returns:
            Matchオブジェクト、見つからない場合はNone
        """
        rows = self.db.execute(
            """
            SELECT * FROM matches
            WHERE home_team = ? AND away_team = ? AND date = ?
            """,
            (home_team, away_team, date.isoformat()),
        )
        if not rows:
            return None
        return self._row_to_match(rows[0])

    def find_by_team(
        self,
        team: str,
        limit: int | None = None,
        before_date: datetime | None = None,
    ) -> list[Match]:
        """チームの試合一覧を取得

        Args:
            team: チーム名
            limit: 取得件数上限
            before_date: この日付より前の試合のみ取得

        Returns:
            Matchオブジェクトのリスト（日付降順）
        """
        query = """
            SELECT * FROM matches
            WHERE (home_team = ? OR away_team = ?)
        """
        params: list = [team, team]

        if before_date:
            query += " AND date < ?"
            params.append(before_date.isoformat())

        query += " ORDER BY date DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = self.db.execute(query, tuple(params))
        return [self._row_to_match(row) for row in rows]

    def find_by_season(self, season: int) -> list[Match]:
        """シーズンの試合一覧を取得

        Args:
            season: シーズン年

        Returns:
            Matchオブジェクトのリスト（日付降順）
        """
        rows = self.db.execute(
            "SELECT * FROM matches WHERE season = ? ORDER BY date DESC",
            (season,),
        )
        return [self._row_to_match(row) for row in rows]

    def find_all(self, limit: int | None = None) -> list[Match]:
        """全試合データを取得

        Args:
            limit: 取得件数上限

        Returns:
            Matchオブジェクトのリスト（日付降順）
        """
        query = "SELECT * FROM matches ORDER BY date DESC"
        if limit:
            query += f" LIMIT {limit}"
        rows = self.db.execute(query)
        return [self._row_to_match(row) for row in rows]

    def get_teams(self) -> list[str]:
        """登録されているチーム一覧を取得

        Returns:
            チーム名のリスト（ユニーク、アルファベット順）
        """
        rows = self.db.execute(
            """
            SELECT DISTINCT team FROM (
                SELECT home_team as team FROM matches
                UNION
                SELECT away_team as team FROM matches
            )
            ORDER BY team
            """
        )
        return [row["team"] for row in rows]

    def count(self) -> int:
        """試合データの総数を取得

        Returns:
            試合数
        """
        return self.db.get_table_count("matches")

    def count_by_team(self, team: str) -> int:
        """チームの試合数を取得

        Args:
            team: チーム名

        Returns:
            試合数
        """
        rows = self.db.execute(
            "SELECT COUNT(*) as count FROM matches WHERE home_team = ? OR away_team = ?",
            (team, team),
        )
        return rows[0]["count"] if rows else 0

    def delete(self, match_id: str) -> None:
        """試合データを削除

        Args:
            match_id: 試合ID

        Raises:
            DataNotFoundError: 指定IDの試合が見つからない場合
        """
        match = self.find_by_id(match_id)
        if not match:
            raise DataNotFoundError(f"試合が見つかりません: {match_id}")

        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM matches WHERE id = ?", (match_id,))
            logger.info(f"試合データを削除しました: {match_id}")

    def exists(self, match_id: str) -> bool:
        """試合データが存在するかチェック

        Args:
            match_id: 試合ID

        Returns:
            存在すればTrue
        """
        rows = self.db.execute(
            "SELECT 1 FROM matches WHERE id = ? LIMIT 1",
            (match_id,),
        )
        return len(rows) > 0

    def _row_to_match(self, row) -> Match:
        """SQLite行をMatchオブジェクトに変換

        Args:
            row: SQLite行データ

        Returns:
            Matchオブジェクト
        """
        return Match(
            id=row["id"],
            date=datetime.fromisoformat(row["date"]),
            season=row["season"],
            competition=row["competition"],
            home_team=row["home_team"],
            away_team=row["away_team"],
            home_goals=row["home_goals"],
            away_goals=row["away_goals"],
            duration=row["duration"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
