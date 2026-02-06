"""データローダー

このモジュールは、Wyscout Excelファイルの読み込みとデータベースへの保存を提供します。
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

from ..db.database import Database
from ..db.repositories.match_repository import MatchRepository
from ..db.repositories.team_stats_repository import TeamStatsRepository
from ..models.exceptions import DataFormatError, DataNotFoundError
from ..models.match import Match
from ..models.team_stats import TeamStats

logger = logging.getLogger(__name__)


class DataLoader:
    """Wyscoutデータローダー

    Wyscout形式のExcelファイルを読み込み、SQLiteデータベースに保存します。

    Attributes:
        db: Databaseインスタンス
        match_repo: MatchRepositoryインスタンス
        stats_repo: TeamStatsRepositoryインスタンス
    """

    # Wyscout Excelの必須カラム（スラッシュ区切りの複合カラムはメインカラム名で検証）
    REQUIRED_COLUMNS = [
        "Date",
        "Match",
        "Competition",
        "Team",
        "Goals",
        "xG",
    ]

    def __init__(self, db_path: str) -> None:
        """データローダーを初期化

        Args:
            db_path: データベースファイルのパス
        """
        self.db = Database(db_path)
        self.match_repo = MatchRepository(self.db)
        self.stats_repo = TeamStatsRepository(self.db)

    def load_excel(self, file_path: str, season: int) -> int:
        """Excelファイルを読み込み、DBに保存

        Args:
            file_path: Excelファイルのパス
            season: シーズン年（例: 2024, 2025）

        Returns:
            追加された試合数

        Raises:
            DataNotFoundError: ファイルが存在しない場合
            DataFormatError: ファイル形式が不正な場合
        """
        path = Path(file_path)

        # ファイル存在確認
        if not path.exists():
            raise DataNotFoundError(
                f"ファイルが存在しません: {file_path}",
                details={"path": file_path},
            )

        # 拡張子確認
        if path.suffix.lower() != ".xlsx":
            raise DataFormatError(
                f"xlsx形式のファイルのみ対応しています: {file_path}",
                details={"path": file_path, "extension": path.suffix},
            )

        logger.info(f"Excelファイルを読み込み中: {file_path}")

        try:
            df = pd.read_excel(file_path, engine="openpyxl")
        except Exception as e:
            raise DataFormatError(
                f"Excelファイルの読み込みに失敗しました: {e}",
                details={"path": file_path, "error": str(e)},
            ) from e

        # 必須カラムの確認
        missing_columns = []
        for col in self.REQUIRED_COLUMNS:
            if col not in df.columns:
                missing_columns.append(col)

        if missing_columns:
            raise DataFormatError(
                f"必須カラムが不足しています: {', '.join(missing_columns)}",
                details={"path": file_path, "missing_columns": missing_columns},
            )

        # データ行のフィルタリング（最初の2行はヘッダー/サマリー行の可能性）
        # Match列が有効な試合情報を含む行のみ抽出
        df = df[df["Match"].notna() & df["Match"].str.contains(" - ", na=False)].copy()

        if df.empty:
            logger.warning(f"有効なデータ行がありません: {file_path}")
            return 0

        # データの処理
        matches_added = 0
        for _, row in df.iterrows():
            try:
                match, team_stats = self._parse_row(row, season)
                if match and team_stats:
                    # 重複チェック
                    existing = self.match_repo.find_by_teams_and_date(
                        match.home_team, match.away_team, match.date
                    )
                    if existing:
                        logger.debug(
                            f"重複データをスキップ: {match.home_team} vs {match.away_team}"
                        )
                        continue

                    # 保存
                    self.match_repo.save(match)
                    self.stats_repo.save(team_stats)
                    matches_added += 1
            except Exception as e:
                logger.warning(f"行の処理をスキップ: {e}")
                continue

        logger.info(f"{matches_added}件の試合データを追加しました: {file_path}")
        return matches_added

    def load_directory(self, dir_path: str, season: int) -> int:
        """ディレクトリ内の全Excelファイルを読み込み

        Args:
            dir_path: ディレクトリパス
            season: シーズン年

        Returns:
            追加された総試合数

        Raises:
            DataNotFoundError: ディレクトリが存在しない場合、またはファイルがない場合
        """
        path = Path(dir_path)

        if not path.exists():
            raise DataNotFoundError(
                f"ディレクトリが存在しません: {dir_path}",
                details={"path": dir_path},
            )

        if not path.is_dir():
            raise DataNotFoundError(
                f"ディレクトリではありません: {dir_path}",
                details={"path": dir_path},
            )

        xlsx_files = list(path.glob("*.xlsx"))
        if not xlsx_files:
            raise DataNotFoundError(
                f"ディレクトリ内にExcelファイルがありません: {dir_path}",
                details={"path": dir_path},
            )

        logger.info(f"{len(xlsx_files)}個のExcelファイルを処理します")

        total_added = 0
        success_count = 0
        skip_count = 0
        error_count = 0

        for xlsx_file in xlsx_files:
            try:
                added = self.load_excel(str(xlsx_file), season)
                total_added += added
                success_count += 1
            except DataFormatError as e:
                logger.warning(f"ファイルをスキップ: {xlsx_file.name} - {e.message}")
                skip_count += 1
            except Exception as e:
                logger.error(f"ファイル処理エラー: {xlsx_file.name} - {e}")
                error_count += 1

        logger.info(
            f"インポート完了: 成功={success_count}, スキップ={skip_count}, "
            f"エラー={error_count}, 追加試合数={total_added}"
        )

        return total_added

    def get_team_matches(self, team: str, limit: int | None = None) -> list[Match]:
        """チームの試合一覧を取得

        Args:
            team: チーム名
            limit: 取得件数上限

        Returns:
            Matchオブジェクトのリスト
        """
        return self.match_repo.find_by_team(team, limit=limit)

    def get_team_stats(
        self,
        team: str,
        limit: int | None = None,
        before_date: datetime | None = None,
    ) -> list[TeamStats]:
        """チームの統計データを取得

        Args:
            team: チーム名
            limit: 取得件数上限
            before_date: この日付より前のデータのみ取得

        Returns:
            TeamStatsオブジェクトのリスト
        """
        return self.stats_repo.find_by_team(team, limit=limit, before_date=before_date)

    def get_teams(self) -> list[str]:
        """登録済みチーム一覧を取得

        Returns:
            チーム名のリスト
        """
        return self.match_repo.get_teams()

    def _parse_row(self, row: pd.Series, season: int) -> tuple[Match | None, TeamStats | None]:
        """Excelの1行をMatch, TeamStatsオブジェクトに変換

        Args:
            row: pandas Series（1行分のデータ）
            season: シーズン年

        Returns:
            (Match, TeamStats)のタプル、変換失敗時は(None, None)
        """
        try:
            # 日付の解析
            date_val = row["Date"]
            if isinstance(date_val, str):
                date = datetime.strptime(date_val, "%Y-%m-%d")
            elif isinstance(date_val, datetime):
                date = date_val
            elif hasattr(date_val, "to_pydatetime"):
                date = date_val.to_pydatetime()
            else:
                logger.warning(f"日付形式が不正: {date_val}")
                return None, None

            # 試合情報の解析（例: "Kashima Antlers - Yokohama F. Marinos 2:1"）
            match_str = str(row["Match"])
            match_info = self._parse_match_string(match_str)
            if not match_info:
                logger.warning(f"試合情報の解析に失敗: {match_str}")
                return None, None

            home_team, away_team, home_goals, away_goals = match_info

            # チーム名の取得（このファイルのチーム）
            team_name = str(row["Team"])
            is_home = team_name == home_team

            # Matchオブジェクトの作成
            match_id = str(uuid4())
            match = Match(
                id=match_id,
                date=date,
                season=season,
                competition=str(row.get("Competition", "")),
                home_team=home_team,
                away_team=away_team,
                home_goals=home_goals,
                away_goals=away_goals,
                duration=int(row.get("Duration", 90) or 90),
            )

            # TeamStatsオブジェクトの作成
            goals = home_goals if is_home else away_goals
            conceded = away_goals if is_home else home_goals

            stats = TeamStats(
                match_id=match_id,
                team=team_name,
                is_home=is_home,
                goals=goals if goals is not None else 0,
                xg=float(row.get("xG", 0) or 0),
                shots=self._parse_slash_value(row, "Shots / on target", 0),
                shots_on_target=self._parse_slash_value(row, "Shots / on target", 1),
                possession=float(row.get("Possession, %", 50) or 50),
                passes=self._parse_slash_value(row, "Passes / accurate", 0),
                passes_accurate=self._parse_slash_value(row, "Passes / accurate", 1),
                crosses=self._parse_slash_value(row, "Crosses / accurate", 0),
                crosses_accurate=self._parse_slash_value(row, "Crosses / accurate", 1),
                pen_area_entries=self._parse_slash_value(
                    row, "Penalty area entries (runs / crosses)", 0
                ),
                conceded_goals=conceded if conceded is not None else 0,
                xg_against=float(row.get("xG_against", 0) or 0),
                shots_against=self._parse_slash_value(row, "Shots against / on target", 0),
                shots_against_on_target=self._parse_slash_value(
                    row, "Shots against / on target", 1
                ),
                ppda=float(row.get("PPDA", 10) or 10),
                interceptions=int(row.get("Interceptions", 0) or 0),
                fouls=int(row.get("Fouls", 0) or 0),
                yellow_cards=int(row.get("Yellow cards", 0) or 0),
                red_cards=int(row.get("Red cards", 0) or 0),
                corners=self._parse_slash_value(row, "Corners / with shots", 0),
            )

            return match, stats

        except Exception as e:
            logger.warning(f"行の解析エラー: {e}")
            return None, None

    def _parse_match_string(self, match_str: str) -> tuple[str, str, int, int] | None:
        """試合文字列を解析

        Args:
            match_str: 試合文字列（例: "Kashima Antlers - Yokohama F. Marinos 2:1"）

        Returns:
            (home_team, away_team, home_goals, away_goals)のタプル、解析失敗時はNone
        """
        # パターン: "Team1 - Team2 score1:score2"
        pattern = r"^(.+?)\s*-\s*(.+?)\s+(\d+):(\d+)$"
        match = re.match(pattern, match_str.strip())

        if not match:
            return None

        home_team = match.group(1).strip()
        away_team = match.group(2).strip()
        home_goals = int(match.group(3))
        away_goals = int(match.group(4))

        return home_team, away_team, home_goals, away_goals

    def _parse_slash_value(self, row: pd.Series, column_name: str, index: int) -> int:
        """スラッシュ区切りの複合カラム値を解析

        Wyscoutのカラム名は "Main / Sub" 形式で、値が分割されている。
        実際のデータは後続のUnnamed列に格納されている。

        Args:
            row: pandas Series
            column_name: カラム名
            index: 取得するインデックス（0=メイン値、1=サブ値）

        Returns:
            解析した整数値（解析失敗時は0）
        """
        try:
            if column_name in row.index:
                # メインカラムの位置を取得
                col_idx = row.index.get_loc(column_name)
                if isinstance(col_idx, int):
                    # index=0ならメインカラム、index=1なら次のUnnamed列
                    target_idx = col_idx + index
                    if target_idx < len(row):
                        val = row.iloc[target_idx]
                        if pd.notna(val):
                            return int(float(val))
            return 0
        except (ValueError, TypeError, IndexError):
            return 0
