"""チーム統計リポジトリ

このモジュールは、チーム統計データのCRUD操作を提供します。
"""

import logging
from datetime import datetime

from ...models.exceptions import DatabaseError, DataNotFoundError
from ...models.team_stats import TeamStats
from ..database import Database

logger = logging.getLogger(__name__)


class TeamStatsRepository:
    """チーム統計データのリポジトリクラス

    TeamStatsデータのデータベース操作を提供します。

    Attributes:
        db: Databaseインスタンス
    """

    def __init__(self, db: Database) -> None:
        """リポジトリを初期化

        Args:
            db: Databaseインスタンス
        """
        self.db = db

    def save(self, stats: TeamStats) -> None:
        """チーム統計データを保存

        Args:
            stats: 保存するTeamStatsオブジェクト

        Raises:
            DatabaseError: 保存に失敗した場合
        """
        try:
            with self.db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO team_stats
                    (id, match_id, team, is_home, goals, xg, shots, shots_on_target,
                     possession, passes, passes_accurate, crosses, crosses_accurate,
                     pen_area_entries, conceded_goals, xg_against, shots_against,
                     shots_against_on_target, ppda, interceptions, fouls,
                     yellow_cards, red_cards, corners, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        stats.id,
                        stats.match_id,
                        stats.team,
                        stats.is_home,
                        stats.goals,
                        stats.xg,
                        stats.shots,
                        stats.shots_on_target,
                        stats.possession,
                        stats.passes,
                        stats.passes_accurate,
                        stats.crosses,
                        stats.crosses_accurate,
                        stats.pen_area_entries,
                        stats.conceded_goals,
                        stats.xg_against,
                        stats.shots_against,
                        stats.shots_against_on_target,
                        stats.ppda,
                        stats.interceptions,
                        stats.fouls,
                        stats.yellow_cards,
                        stats.red_cards,
                        stats.corners,
                        stats.created_at.isoformat(),
                    ),
                )
                logger.debug(f"チーム統計を保存しました: {stats.id}")
        except Exception as e:
            raise DatabaseError(f"チーム統計の保存に失敗しました: {e}") from e

    def save_many(self, stats_list: list[TeamStats]) -> int:
        """複数のチーム統計データをバッチ保存

        Args:
            stats_list: 保存するTeamStatsオブジェクトのリスト

        Returns:
            保存した件数

        Raises:
            DatabaseError: 保存に失敗した場合
        """
        if not stats_list:
            return 0

        try:
            params_list = [
                (
                    s.id,
                    s.match_id,
                    s.team,
                    s.is_home,
                    s.goals,
                    s.xg,
                    s.shots,
                    s.shots_on_target,
                    s.possession,
                    s.passes,
                    s.passes_accurate,
                    s.crosses,
                    s.crosses_accurate,
                    s.pen_area_entries,
                    s.conceded_goals,
                    s.xg_against,
                    s.shots_against,
                    s.shots_against_on_target,
                    s.ppda,
                    s.interceptions,
                    s.fouls,
                    s.yellow_cards,
                    s.red_cards,
                    s.corners,
                    s.created_at.isoformat(),
                )
                for s in stats_list
            ]

            self.db.execute_many(
                """
                INSERT OR REPLACE INTO team_stats
                (id, match_id, team, is_home, goals, xg, shots, shots_on_target,
                 possession, passes, passes_accurate, crosses, crosses_accurate,
                 pen_area_entries, conceded_goals, xg_against, shots_against,
                 shots_against_on_target, ppda, interceptions, fouls,
                 yellow_cards, red_cards, corners, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                params_list,
            )
            logger.info(f"{len(stats_list)}件のチーム統計を保存しました")
            return len(stats_list)
        except Exception as e:
            raise DatabaseError(f"チーム統計のバッチ保存に失敗しました: {e}") from e

    def find_by_id(self, stats_id: str) -> TeamStats | None:
        """IDでチーム統計を検索

        Args:
            stats_id: 統計ID

        Returns:
            TeamStatsオブジェクト、見つからない場合はNone
        """
        rows = self.db.execute("SELECT * FROM team_stats WHERE id = ?", (stats_id,))
        if not rows:
            return None
        return self._row_to_team_stats(rows[0])

    def find_by_match_id(self, match_id: str) -> list[TeamStats]:
        """試合IDでチーム統計を検索

        Args:
            match_id: 試合ID

        Returns:
            TeamStatsオブジェクトのリスト（通常2件：ホーム/アウェイ）
        """
        rows = self.db.execute(
            "SELECT * FROM team_stats WHERE match_id = ?",
            (match_id,),
        )
        return [self._row_to_team_stats(row) for row in rows]

    def find_by_team(
        self,
        team: str,
        limit: int | None = None,
        before_date: datetime | None = None,
    ) -> list[TeamStats]:
        """チームの統計一覧を取得

        Args:
            team: チーム名
            limit: 取得件数上限
            before_date: この日付より前の試合のみ取得

        Returns:
            TeamStatsオブジェクトのリスト（日付降順）
        """
        query = """
            SELECT ts.* FROM team_stats ts
            JOIN matches m ON ts.match_id = m.id
            WHERE ts.team = ?
        """
        params: list = [team]

        if before_date:
            query += " AND m.date < ?"
            params.append(before_date.isoformat())

        query += " ORDER BY m.date DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = self.db.execute(query, tuple(params))
        return [self._row_to_team_stats(row) for row in rows]

    def find_by_team_and_match(self, team: str, match_id: str) -> TeamStats | None:
        """チーム名と試合IDでチーム統計を検索

        Args:
            team: チーム名
            match_id: 試合ID

        Returns:
            TeamStatsオブジェクト、見つからない場合はNone
        """
        rows = self.db.execute(
            "SELECT * FROM team_stats WHERE team = ? AND match_id = ?",
            (team, match_id),
        )
        if not rows:
            return None
        return self._row_to_team_stats(rows[0])

    def count(self) -> int:
        """チーム統計の総数を取得

        Returns:
            統計数
        """
        return self.db.get_table_count("team_stats")

    def count_by_team(self, team: str) -> int:
        """チームの統計数を取得

        Args:
            team: チーム名

        Returns:
            統計数
        """
        rows = self.db.execute(
            "SELECT COUNT(*) as count FROM team_stats WHERE team = ?",
            (team,),
        )
        return rows[0]["count"] if rows else 0

    def delete(self, stats_id: str) -> None:
        """チーム統計を削除

        Args:
            stats_id: 統計ID

        Raises:
            DataNotFoundError: 指定IDの統計が見つからない場合
        """
        stats = self.find_by_id(stats_id)
        if not stats:
            raise DataNotFoundError(f"チーム統計が見つかりません: {stats_id}")

        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM team_stats WHERE id = ?", (stats_id,))
            logger.info(f"チーム統計を削除しました: {stats_id}")

    def delete_by_match_id(self, match_id: str) -> int:
        """試合IDに関連するチーム統計を削除

        Args:
            match_id: 試合ID

        Returns:
            削除した件数
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM team_stats WHERE match_id = ?", (match_id,))
            count = cursor.rowcount
            logger.info(f"試合 {match_id} のチーム統計を {count}件 削除しました")
            return count

    def get_teams(self) -> list[str]:
        """登録されているチーム一覧を取得

        Returns:
            チーム名のリスト（ユニーク、アルファベット順）
        """
        rows = self.db.execute("SELECT DISTINCT team FROM team_stats ORDER BY team")
        return [row["team"] for row in rows]

    def get_average_stats(self, team: str, limit: int = 10) -> dict:
        """チームの平均統計を取得

        Args:
            team: チーム名
            limit: 計算に使用する直近試合数

        Returns:
            平均統計の辞書
        """
        rows = self.db.execute(
            """
            SELECT
                AVG(goals) as goals_avg,
                AVG(xg) as xg_avg,
                AVG(shots) as shots_avg,
                AVG(shots_on_target) as shots_on_target_avg,
                AVG(possession) as possession_avg,
                AVG(ppda) as ppda_avg,
                AVG(conceded_goals) as conceded_avg,
                AVG(xg_against) as xg_against_avg
            FROM (
                SELECT ts.* FROM team_stats ts
                JOIN matches m ON ts.match_id = m.id
                WHERE ts.team = ?
                ORDER BY m.date DESC
                LIMIT ?
            )
            """,
            (team, limit),
        )
        if not rows or rows[0]["goals_avg"] is None:
            return {}
        return dict(rows[0])

    def _row_to_team_stats(self, row) -> TeamStats:
        """SQLite行をTeamStatsオブジェクトに変換

        Args:
            row: SQLite行データ

        Returns:
            TeamStatsオブジェクト
        """
        return TeamStats(
            id=row["id"],
            match_id=row["match_id"],
            team=row["team"],
            is_home=bool(row["is_home"]),
            goals=row["goals"],
            xg=row["xg"],
            shots=row["shots"],
            shots_on_target=row["shots_on_target"],
            possession=row["possession"],
            passes=row["passes"],
            passes_accurate=row["passes_accurate"],
            crosses=row["crosses"],
            crosses_accurate=row["crosses_accurate"],
            pen_area_entries=row["pen_area_entries"],
            conceded_goals=row["conceded_goals"],
            xg_against=row["xg_against"],
            shots_against=row["shots_against"],
            shots_against_on_target=row["shots_against_on_target"],
            ppda=row["ppda"],
            interceptions=row["interceptions"],
            fouls=row["fouls"],
            yellow_cards=row["yellow_cards"],
            red_cards=row["red_cards"],
            corners=row["corners"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
