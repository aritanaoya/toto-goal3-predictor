"""CLI mainモジュールのテスト"""

import pytest
from typer.testing import CliRunner

from toto_predictor.cli.main import app


class TestCLIMain:
    """メインCLIのテスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_version_command(self, runner):
        """versionコマンドが正しく動作する"""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "v0.1.0" in result.stdout

    def test_info_command(self, runner):
        """infoコマンドがシステム情報を表示する"""
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0
        assert "Python" in result.stdout

    def test_help_command(self, runner):
        """helpが正しく表示される"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "toto GOAL3" in result.stdout

    def test_verbose_option(self, runner):
        """--verboseオプションが動作する"""
        result = runner.invoke(app, ["--verbose", "version"])
        assert result.exit_code == 0

    def test_import_help(self, runner):
        """importコマンドのヘルプ"""
        result = runner.invoke(app, ["import", "--help"])
        assert result.exit_code == 0
        assert "Wyscout" in result.stdout

    def test_train_help(self, runner):
        """trainコマンドのヘルプ"""
        result = runner.invoke(app, ["train", "--help"])
        assert result.exit_code == 0
        assert "シーズン" in result.stdout

    def test_predict_help(self, runner):
        """predictコマンドのヘルプ"""
        result = runner.invoke(app, ["predict", "--help"])
        assert result.exit_code == 0
        assert "予測" in result.stdout

    def test_scrape_help(self, runner):
        """scrapeコマンドのヘルプ"""
        result = runner.invoke(app, ["scrape", "--help"])
        assert result.exit_code == 0
        assert "投票率" in result.stdout

    def test_strategy_help(self, runner):
        """strategyコマンドのヘルプ"""
        result = runner.invoke(app, ["strategy", "--help"])
        assert result.exit_code == 0
        assert "購入戦略" in result.stdout

    def test_pipeline_help(self, runner):
        """pipelineコマンドのヘルプ"""
        result = runner.invoke(app, ["pipeline", "--help"])
        assert result.exit_code == 0
        assert "パイプライン" in result.stdout
