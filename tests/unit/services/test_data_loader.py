"""DataLoaderのユニットテスト"""

import pytest

from toto_predictor.models.exceptions import DataFormatError, DataNotFoundError
from toto_predictor.services.data_loader import DataLoader


class TestDataLoader:
    """DataLoaderのテスト"""

    def test_init_creates_database(self, temp_db):
        """初期化時にデータベースが作成される"""
        loader = DataLoader(temp_db)
        assert loader.db is not None
        assert loader.match_repo is not None
        assert loader.stats_repo is not None

    def test_load_excel_file_not_found(self, temp_db):
        """存在しないファイルでエラーが発生する"""
        loader = DataLoader(temp_db)

        with pytest.raises(DataNotFoundError):
            loader.load_excel("nonexistent.xlsx", 2025)

    def test_load_excel_invalid_extension(self, temp_db, tmp_path):
        """xlsx以外の拡張子でエラーが発生する"""
        # CSVファイルを作成
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b,c\n1,2,3")

        loader = DataLoader(temp_db)

        with pytest.raises(DataFormatError):
            loader.load_excel(str(csv_file), 2025)

    def test_load_directory_not_found(self, temp_db):
        """存在しないディレクトリでエラーが発生する"""
        loader = DataLoader(temp_db)

        with pytest.raises(DataNotFoundError):
            loader.load_directory("/nonexistent/path", 2025)

    def test_load_directory_empty(self, temp_db, tmp_path):
        """Excelファイルがないディレクトリでエラーが発生する"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        loader = DataLoader(temp_db)

        with pytest.raises(DataNotFoundError):
            loader.load_directory(str(empty_dir), 2025)

    def test_get_teams_empty(self, temp_db):
        """空のデータベースで空リストが返る"""
        loader = DataLoader(temp_db)
        teams = loader.get_teams()
        assert teams == []

    def test_get_team_matches_empty(self, temp_db):
        """存在しないチームで空リストが返る"""
        loader = DataLoader(temp_db)
        matches = loader.get_team_matches("Nonexistent Team")
        assert matches == []

    def test_get_team_stats_empty(self, temp_db):
        """存在しないチームで空リストが返る"""
        loader = DataLoader(temp_db)
        stats = loader.get_team_stats("Nonexistent Team")
        assert stats == []

    def test_parse_match_string(self, temp_db):
        """試合文字列のパースが正しく動作する"""
        loader = DataLoader(temp_db)

        # 正常ケース
        result = loader._parse_match_string("Kashima Antlers - Yokohama F. Marinos 2:1")
        assert result == ("Kashima Antlers", "Yokohama F. Marinos", 2, 1)

        # 不正な形式
        result = loader._parse_match_string("Invalid Format")
        assert result is None

        # 空文字列
        result = loader._parse_match_string("")
        assert result is None

    def test_parse_slash_value(self, temp_db):
        """スラッシュ区切り値のパースが正しく動作する"""
        loader = DataLoader(temp_db)

        import pandas as pd

        # テスト用のSeriesを作成
        row = pd.Series(
            {"Shots / on target": 10, "Unnamed: 9": 5},
            index=["Shots / on target", "Unnamed: 9"],
        )

        # メイン値
        main_value = loader._parse_slash_value(row, "Shots / on target", 0)
        assert main_value == 10

        # サブ値
        sub_value = loader._parse_slash_value(row, "Shots / on target", 1)
        assert sub_value == 5

        # 存在しないカラム
        missing_value = loader._parse_slash_value(row, "Nonexistent", 0)
        assert missing_value == 0
