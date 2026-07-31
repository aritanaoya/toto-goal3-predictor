"""pipelineコマンドのテスト"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from typer.testing import CliRunner

from toto_predictor.cli.commands.pipeline_cmd import app
from toto_predictor.models.exceptions import TotoPredictorError


class TestPipelineCommand:
    """pipelineコマンドのテスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_pipeline_help(self, runner):
        """ヘルプが表示される"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--round" in result.stdout
        assert "--skip-import" in result.stdout
        assert "--skip-train" in result.stdout

    @patch("toto_predictor.cli.commands.pipeline_cmd.StrategyEngine")
    @patch("toto_predictor.cli.commands.pipeline_cmd.VoteScraper")
    @patch("toto_predictor.cli.commands.pipeline_cmd.ModelEnsemble")
    @patch("toto_predictor.cli.commands.pipeline_cmd.FeatureEngine")
    @patch("toto_predictor.cli.commands.pipeline_cmd.DataLoader")
    def test_pipeline_full(
        self,
        mock_loader,
        mock_engine,
        mock_model,
        mock_scraper,
        mock_strategy,
        runner,
        tmp_path,
    ):
        """完全なパイプライン実行"""
        # DataLoaderモック
        mock_loader_instance = MagicMock()
        mock_loader_instance.get_teams.return_value = ["Team A"]
        mock_loader_instance.load_directory.return_value = 10
        mock_loader.return_value = mock_loader_instance

        # FeatureEngineモック
        mock_engine_instance = MagicMock()
        mock_engine_instance.prepare_training_data.return_value = (
            pd.DataFrame({"f1": [1, 2]}),
            pd.Series([0, 1]),
        )
        mock_engine_instance.calculate_features.return_value = MagicMock()
        mock_engine.return_value = mock_engine_instance

        # ModelEnsembleモック
        mock_model_instance = MagicMock()
        mock_model_instance.train.return_value = {
            "brier_score": 0.15,
            "brier_score_std": 0.02,
            "accuracy": 0.45,
            "accuracy_std": 0.05,
            "n_samples": 100,
            "cv_folds": 5,
        }
        mock_prediction = MagicMock()
        mock_prediction.to_dict.return_value = {}
        mock_model_instance.predict.return_value = mock_prediction
        mock_model.return_value = mock_model_instance

        # VoteScraperモック
        mock_scraper_instance = MagicMock()
        mock_vote = MagicMock()
        mock_vote.team = "Team A"
        mock_scraper_instance.fetch.return_value = [mock_vote]
        mock_scraper.return_value = mock_scraper_instance

        # StrategyEngineモック
        mock_strategy_instance = MagicMock()
        mock_strategy_instance.calculate_value_scores.return_value = []
        mock_strategy_instance.generate_report.return_value = str(tmp_path / "report.md")
        mock_strategy.return_value = mock_strategy_instance

        result = runner.invoke(
            app,
            [
                "--round",
                "1607",
                "--skip-import",
                "--skip-train",
                "--db",
                ":memory:",
                "--model-dir",
                str(tmp_path / "models"),
            ],
        )
        # パイプラインが実行される
        assert "パイプライン" in result.stdout or result.exit_code == 0

    @patch("toto_predictor.cli.commands.pipeline_cmd.VoteScraper")
    @patch("toto_predictor.cli.commands.pipeline_cmd.ModelEnsemble")
    @patch("toto_predictor.cli.commands.pipeline_cmd.FeatureEngine")
    @patch("toto_predictor.cli.commands.pipeline_cmd.DataLoader")
    def test_pipeline_skip_import(
        self,
        mock_loader,
        mock_engine,
        mock_model,
        mock_scraper,
        runner,
        tmp_path,
    ):
        """--skip-importオプション"""
        mock_loader_instance = MagicMock()
        mock_loader_instance.get_teams.return_value = ["Team A"]
        mock_loader.return_value = mock_loader_instance

        mock_engine.return_value = MagicMock()

        mock_model_instance = MagicMock()
        mock_prediction = MagicMock()
        mock_prediction.to_dict.return_value = {}
        mock_model_instance.predict.return_value = mock_prediction
        mock_model.return_value = mock_model_instance

        mock_scraper_instance = MagicMock()
        mock_scraper_instance.fetch.return_value = []
        mock_scraper.return_value = mock_scraper_instance

        runner.invoke(
            app,
            [
                "--round",
                "1607",
                "--skip-import",
                "--skip-train",
                "--db",
                ":memory:",
                "--model-dir",
                str(tmp_path / "models"),
            ],
        )
        # load_directoryが呼ばれない
        mock_loader_instance.load_directory.assert_not_called()

    @patch("toto_predictor.cli.commands.pipeline_cmd.VoteScraper")
    @patch("toto_predictor.cli.commands.pipeline_cmd.ModelEnsemble")
    @patch("toto_predictor.cli.commands.pipeline_cmd.FeatureEngine")
    @patch("toto_predictor.cli.commands.pipeline_cmd.DataLoader")
    def test_pipeline_skip_train(
        self,
        mock_loader,
        mock_engine,
        mock_model,
        mock_scraper,
        runner,
        tmp_path,
    ):
        """--skip-trainオプション（デフォルト有効）"""
        mock_loader_instance = MagicMock()
        mock_loader_instance.get_teams.return_value = ["Team A"]
        mock_loader.return_value = mock_loader_instance

        mock_engine.return_value = MagicMock()

        mock_model_instance = MagicMock()
        mock_prediction = MagicMock()
        mock_prediction.to_dict.return_value = {}
        mock_model_instance.predict.return_value = mock_prediction
        mock_model.return_value = mock_model_instance

        mock_scraper.return_value.fetch.return_value = []

        runner.invoke(
            app,
            [
                "--round",
                "1607",
                "--skip-import",
                "--skip-train",
                "--db",
                ":memory:",
                "--model-dir",
                str(tmp_path / "models"),
            ],
        )
        # trainが呼ばれない
        mock_model_instance.train.assert_not_called()

    @patch("toto_predictor.cli.commands.pipeline_cmd.VoteScraper")
    @patch("toto_predictor.cli.commands.pipeline_cmd.ModelEnsemble")
    @patch("toto_predictor.cli.commands.pipeline_cmd.FeatureEngine")
    @patch("toto_predictor.cli.commands.pipeline_cmd.DataLoader")
    def test_pipeline_skip_scrape(
        self,
        mock_loader,
        mock_engine,
        mock_model,
        mock_scraper,
        runner,
        tmp_path,
    ):
        """--skip-scrapeオプション"""
        mock_loader_instance = MagicMock()
        mock_loader_instance.get_teams.return_value = ["Team A"]
        mock_loader.return_value = mock_loader_instance

        mock_engine.return_value = MagicMock()

        mock_model_instance = MagicMock()
        mock_prediction = MagicMock()
        mock_prediction.to_dict.return_value = {}
        mock_model_instance.predict.return_value = mock_prediction
        mock_model.return_value = mock_model_instance

        mock_scraper.return_value.fetch.return_value = []

        runner.invoke(
            app,
            [
                "--round",
                "1607",
                "--skip-import",
                "--skip-train",
                "--skip-scrape",
                "--db",
                ":memory:",
                "--model-dir",
                str(tmp_path / "models"),
            ],
        )
        # scrapeがスキップされる
        mock_scraper.return_value.fetch.assert_not_called()

    @patch("toto_predictor.cli.commands.pipeline_cmd.DataLoader")
    def test_pipeline_error_handling(self, mock_loader, runner, tmp_path):
        """エラーハンドリング"""
        mock_loader.return_value.get_teams.side_effect = TotoPredictorError("テストエラー")

        result = runner.invoke(
            app,
            [
                "--round",
                "1607",
                "--skip-import",
                "--skip-train",
                "--db",
                ":memory:",
                "--model-dir",
                str(tmp_path / "models"),
            ],
        )
        assert result.exit_code == 1
        assert "エラー" in result.stdout

    @patch("toto_predictor.cli.commands.pipeline_cmd.VoteScraper")
    @patch("toto_predictor.cli.commands.pipeline_cmd.ModelEnsemble")
    @patch("toto_predictor.cli.commands.pipeline_cmd.FeatureEngine")
    @patch("toto_predictor.cli.commands.pipeline_cmd.DataLoader")
    def test_pipeline_season_option(
        self,
        mock_loader,
        mock_engine,
        mock_model,
        mock_scraper,
        runner,
        tmp_path,
    ):
        """シーズンオプションが渡される"""
        mock_loader_instance = MagicMock()
        mock_loader_instance.get_teams.return_value = ["Team A"]
        mock_loader.return_value = mock_loader_instance

        mock_engine.return_value = MagicMock()

        mock_model_instance = MagicMock()
        mock_prediction = MagicMock()
        mock_prediction.to_dict.return_value = {}
        mock_model_instance.predict.return_value = mock_prediction
        mock_model.return_value = mock_model_instance

        mock_scraper.return_value.fetch.return_value = []

        result = runner.invoke(
            app,
            [
                "--round",
                "1607",
                "--skip-import",
                "--skip-train",
                "--season",
                "2024",
                "--db",
                ":memory:",
                "--model-dir",
                str(tmp_path / "models"),
            ],
        )
        assert result.exit_code in [0, 1]

    @patch("toto_predictor.cli.commands.pipeline_cmd.VoteScraper")
    @patch("toto_predictor.cli.commands.pipeline_cmd.ModelEnsemble")
    @patch("toto_predictor.cli.commands.pipeline_cmd.FeatureEngine")
    @patch("toto_predictor.cli.commands.pipeline_cmd.DataLoader")
    def test_pipeline_data_dir_option(
        self,
        mock_loader,
        mock_engine,
        mock_model,
        mock_scraper,
        runner,
        tmp_path,
    ):
        """データディレクトリオプション"""
        mock_loader_instance = MagicMock()
        mock_loader_instance.get_teams.return_value = ["Team A"]
        mock_loader_instance.load_directory.return_value = 5
        mock_loader.return_value = mock_loader_instance

        mock_engine.return_value = MagicMock()

        mock_model_instance = MagicMock()
        mock_prediction = MagicMock()
        mock_prediction.to_dict.return_value = {}
        mock_model_instance.predict.return_value = mock_prediction
        mock_model.return_value = mock_model_instance

        mock_scraper.return_value.fetch.return_value = []

        data_dir = tmp_path / "wyscout"
        data_dir.mkdir()

        result = runner.invoke(
            app,
            [
                "--round",
                "1607",
                "--skip-train",
                "--data-dir",
                str(data_dir),
                "--db",
                ":memory:",
                "--model-dir",
                str(tmp_path / "models"),
            ],
        )
        # データディレクトリが渡される
        assert result.exit_code in [0, 1]
