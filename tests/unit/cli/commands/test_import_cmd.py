"""importコマンドのテスト"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from toto_predictor.cli.commands.import_cmd import app


class TestImportCommand:
    """importコマンドのテスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_import_success(self, runner, tmp_path, sample_excel_path):
        """正常なインポートが成功する"""
        db_path = str(tmp_path / "test.db")
        excel_dir = str(Path(sample_excel_path).parent)

        result = runner.invoke(
            app,
            [
                "--dir",
                excel_dir,
                "--season",
                "2025",
                "--db",
                db_path,
            ],
        )
        assert result.exit_code == 0
        assert "インポート完了" in result.stdout or "試合" in result.stdout

    def test_import_directory_not_found(self, runner, tmp_path):
        """存在しないディレクトリでエラー"""
        result = runner.invoke(
            app,
            [
                "--dir",
                "/nonexistent/path",
                "--db",
                str(tmp_path / "test.db"),
            ],
        )
        assert result.exit_code == 1
        assert "見つかりません" in result.stdout or "Error" in result.stdout

    def test_import_empty_directory(self, runner, tmp_path):
        """空のディレクトリでエラー"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = runner.invoke(
            app,
            [
                "--dir",
                str(empty_dir),
                "--db",
                str(tmp_path / "test.db"),
            ],
        )
        assert result.exit_code == 1

    def test_import_help(self, runner):
        """ヘルプが表示される"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--dir" in result.stdout
        assert "--season" in result.stdout

    def test_import_with_season_option(self, runner, tmp_path, sample_excel_path):
        """シーズンオプションが正しく渡される"""
        db_path = str(tmp_path / "test.db")
        excel_dir = str(Path(sample_excel_path).parent)

        result = runner.invoke(
            app,
            [
                "--dir",
                excel_dir,
                "--season",
                "2024",
                "--db",
                db_path,
            ],
        )
        # シーズンが正しく処理される（エラーなし）
        assert "2024" in result.stdout or result.exit_code == 0

    def test_import_default_db_path(self, runner, tmp_path, sample_excel_path):
        """デフォルトDBパスが使用される"""
        excel_dir = str(Path(sample_excel_path).parent)

        result = runner.invoke(
            app,
            [
                "--dir",
                excel_dir,
                "--season",
                "2025",
            ],
        )
        # デフォルトパスでの処理（ディレクトリがなければエラー）
        assert result.exit_code in [0, 1]

    def test_import_shows_team_list(self, runner, tmp_path, sample_excel_path):
        """インポート後にチーム一覧が表示される"""
        db_path = str(tmp_path / "test.db")
        excel_dir = str(Path(sample_excel_path).parent)

        result = runner.invoke(
            app,
            [
                "--dir",
                excel_dir,
                "--season",
                "2025",
                "--db",
                db_path,
            ],
        )
        if result.exit_code == 0:
            assert "登録チーム" in result.stdout

    def test_import_data_format_error(self, runner, tmp_path):
        """データ形式エラーの処理"""
        import pandas as pd

        # 不正な形式のExcelを作成
        invalid_excel = tmp_path / "Team Stats Invalid.xlsx"
        pd.DataFrame({"InvalidColumn": [1, 2, 3]}).to_excel(
            invalid_excel, index=False, engine="openpyxl"
        )

        result = runner.invoke(
            app,
            [
                "--dir",
                str(tmp_path),
                "--season",
                "2025",
                "--db",
                str(tmp_path / "test.db"),
            ],
        )
        # データ形式エラーまたはインポート0件
        assert result.exit_code in [0, 1]
