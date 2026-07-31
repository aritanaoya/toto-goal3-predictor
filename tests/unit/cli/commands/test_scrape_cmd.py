"""scrapeコマンドのテスト"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from toto_predictor.cli.commands.scrape_cmd import app
from toto_predictor.models.exceptions import ScrapingError


class TestScrapeCommand:
    """scrapeコマンドのテスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_scrape_help(self, runner):
        """ヘルプが表示される"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--round" in result.stdout
        assert "--cache" in result.stdout

    @patch("toto_predictor.cli.commands.scrape_cmd.VoteScraper")
    def test_scrape_success(self, mock_scraper, runner, sample_vote_rate):
        """正常なスクレイピングが成功する"""
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.fetch.return_value = [sample_vote_rate]
        mock_scraper.return_value = mock_scraper_instance

        result = runner.invoke(app, ["--round", "1607"])
        assert result.exit_code == 0
        assert "投票率" in result.stdout

    @patch("toto_predictor.cli.commands.scrape_cmd.VoteScraper")
    def test_scrape_use_cache(self, mock_scraper, runner, sample_vote_rate):
        """キャッシュ使用オプション"""
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.get_cached.return_value = [sample_vote_rate]
        mock_scraper.return_value = mock_scraper_instance

        result = runner.invoke(app, ["--round", "1607", "--cache"])
        assert result.exit_code == 0
        assert "キャッシュ" in result.stdout

    @patch("toto_predictor.cli.commands.scrape_cmd.VoteScraper")
    def test_scrape_cache_miss(self, mock_scraper, runner, sample_vote_rate):
        """キャッシュミス時はフェッチ"""
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.get_cached.return_value = None
        mock_scraper_instance.fetch.return_value = [sample_vote_rate]
        mock_scraper.return_value = mock_scraper_instance

        runner.invoke(app, ["--round", "1607", "--cache"])
        # キャッシュミスでもフェッチして続行
        mock_scraper_instance.fetch.assert_called_once()

    @patch("toto_predictor.cli.commands.scrape_cmd.VoteScraper")
    def test_scrape_network_error(self, mock_scraper, runner):
        """ネットワークエラーの処理"""
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.fetch.side_effect = ScrapingError("接続エラー")
        mock_scraper.return_value = mock_scraper_instance

        result = runner.invoke(app, ["--round", "1607"])
        assert result.exit_code == 1
        assert "エラー" in result.stdout

    @patch("toto_predictor.cli.commands.scrape_cmd.VoteScraper")
    def test_scrape_latest_round(self, mock_scraper, runner, sample_vote_rate):
        """最新回の取得（round=0）"""
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.fetch.return_value = [sample_vote_rate]
        mock_scraper.return_value = mock_scraper_instance

        result = runner.invoke(app, [])  # デフォルトでround=0
        assert result.exit_code == 0
        # round_number=Noneでfetchが呼ばれる
        mock_scraper_instance.fetch.assert_called_once()

    @patch("toto_predictor.cli.commands.scrape_cmd.VoteScraper")
    def test_scrape_empty_result(self, mock_scraper, runner):
        """空の結果"""
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.fetch.return_value = []
        mock_scraper.return_value = mock_scraper_instance

        result = runner.invoke(app, ["--round", "1607"])
        # 空でも正常終了
        assert "ありません" in result.stdout or result.exit_code == 0

    @patch("toto_predictor.cli.commands.scrape_cmd.VoteScraper")
    def test_scrape_cache_dir_option(self, mock_scraper, runner, tmp_path, sample_vote_rate):
        """キャッシュディレクトリオプション"""
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.fetch.return_value = [sample_vote_rate]
        mock_scraper.return_value = mock_scraper_instance

        cache_dir = tmp_path / "votes"
        runner.invoke(
            app,
            ["--round", "1607", "--cache-dir", str(cache_dir)],
        )
        # キャッシュディレクトリが渡される
        mock_scraper.assert_called_once()
        call_kwargs = mock_scraper.call_args[1]
        assert str(cache_dir) in call_kwargs.get("cache_dir", "")
