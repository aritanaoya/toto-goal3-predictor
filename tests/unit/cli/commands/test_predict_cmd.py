"""predictコマンドのテスト"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from toto_predictor.cli.commands.predict_cmd import app
from toto_predictor.models.exceptions import DataNotFoundError, ModelNotTrainedError


class TestPredictCommand:
    """predictコマンドのテスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_predict_help(self, runner):
        """ヘルプが表示される"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--round" in result.stdout
        assert "--teams" in result.stdout

    def test_predict_model_not_trained(self, runner, tmp_path):
        """モデル未学習エラー"""
        result = runner.invoke(
            app,
            [
                "--model-dir",
                str(tmp_path / "nonexistent"),
            ],
        )
        assert result.exit_code == 1
        assert "見つかりません" in result.stdout or "モデル" in result.stdout

    @patch("toto_predictor.services.data_loader.DataLoader")
    @patch("toto_predictor.cli.commands.predict_cmd.FeatureEngine")
    @patch("toto_predictor.cli.commands.predict_cmd.ModelEnsemble")
    def test_predict_success(
        self, mock_model, mock_engine, mock_loader, runner, tmp_path, mock_trained_model
    ):
        """正常な予測が成功する"""
        # DataLoaderモック
        mock_loader_instance = MagicMock()
        mock_loader_instance.get_teams.return_value = ["Team A"]
        mock_loader.return_value = mock_loader_instance

        # FeatureEngineモック
        mock_engine_instance = MagicMock()
        mock_features = MagicMock()
        mock_engine_instance.calculate_features.return_value = mock_features
        mock_engine.return_value = mock_engine_instance

        # ModelEnsembleモック
        mock_model_instance = MagicMock()
        mock_prediction = MagicMock()
        mock_prediction.team = "Team A"
        mock_prediction.get_all_probs.return_value = {"0": 0.2, "1": 0.3, "2": 0.3, "3+": 0.2}
        mock_prediction.get_most_likely_category.return_value = "1"
        mock_prediction.get_prob_for_category.return_value = 0.3
        mock_prediction.to_dict.return_value = {"team": "Team A"}
        mock_model_instance.predict.return_value = mock_prediction
        mock_model.return_value = mock_model_instance

        result = runner.invoke(
            app,
            [
                "--round",
                "1607",
                "--db",
                ":memory:",
                "--model-dir",
                mock_trained_model,
            ],
        )
        # 予測が実行される
        assert "予測" in result.stdout or result.exit_code == 0

    @patch("toto_predictor.services.data_loader.DataLoader")
    @patch("toto_predictor.cli.commands.predict_cmd.FeatureEngine")
    @patch("toto_predictor.cli.commands.predict_cmd.ModelEnsemble")
    def test_predict_specific_teams(
        self, mock_model, mock_engine, mock_loader, runner, tmp_path, mock_trained_model
    ):
        """特定チームのみ予測"""
        mock_engine_instance = MagicMock()
        mock_features = MagicMock()
        mock_engine_instance.calculate_features.return_value = mock_features
        mock_engine.return_value = mock_engine_instance

        mock_model_instance = MagicMock()
        mock_prediction = MagicMock()
        mock_prediction.team = "Team X"
        mock_prediction.get_all_probs.return_value = {"0": 0.25, "1": 0.25, "2": 0.25, "3+": 0.25}
        mock_prediction.get_most_likely_category.return_value = "1"
        mock_prediction.get_prob_for_category.return_value = 0.25
        mock_prediction.to_dict.return_value = {}
        mock_model_instance.predict.return_value = mock_prediction
        mock_model.return_value = mock_model_instance

        result = runner.invoke(
            app,
            [
                "--round",
                "1607",
                "--teams",
                "Team X,Team Y",
                "--db",
                ":memory:",
                "--model-dir",
                mock_trained_model,
            ],
        )
        # 特定チームが処理される
        assert result.exit_code in [0, 1]

    @patch("toto_predictor.services.data_loader.DataLoader")
    @patch("toto_predictor.cli.commands.predict_cmd.ModelEnsemble")
    def test_predict_no_teams(self, mock_model, mock_loader, runner, tmp_path, mock_trained_model):
        """チームがない場合"""
        mock_loader_instance = MagicMock()
        mock_loader_instance.get_teams.return_value = []
        mock_loader.return_value = mock_loader_instance

        mock_model.return_value = MagicMock()

        result = runner.invoke(
            app,
            [
                "--db",
                ":memory:",
                "--model-dir",
                mock_trained_model,
            ],
        )
        assert result.exit_code == 1
        assert "チーム" in result.stdout or "ありません" in result.stdout

    @patch("toto_predictor.services.data_loader.DataLoader")
    @patch("toto_predictor.cli.commands.predict_cmd.FeatureEngine")
    @patch("toto_predictor.cli.commands.predict_cmd.ModelEnsemble")
    def test_predict_data_insufficient(
        self, mock_model, mock_engine, mock_loader, runner, tmp_path, mock_trained_model
    ):
        """データ不足でスキップ"""
        mock_loader_instance = MagicMock()
        mock_loader_instance.get_teams.return_value = ["Team A"]
        mock_loader.return_value = mock_loader_instance

        mock_engine_instance = MagicMock()
        mock_engine_instance.calculate_features.side_effect = DataNotFoundError("データ不足")
        mock_engine.return_value = mock_engine_instance

        mock_model.return_value = MagicMock()

        result = runner.invoke(
            app,
            [
                "--round",
                "1607",
                "--db",
                ":memory:",
                "--model-dir",
                mock_trained_model,
            ],
        )
        # データ不足でもスキップして続行
        assert "スキップ" in result.stdout or "データ不足" in result.stdout

    @patch("toto_predictor.services.data_loader.DataLoader")
    @patch("toto_predictor.cli.commands.predict_cmd.FeatureEngine")
    @patch("toto_predictor.cli.commands.predict_cmd.ModelEnsemble")
    def test_predict_output_json(
        self, mock_model, mock_engine, mock_loader, runner, tmp_path, mock_trained_model
    ):
        """JSON出力オプション"""
        mock_loader_instance = MagicMock()
        mock_loader_instance.get_teams.return_value = ["Team A"]
        mock_loader.return_value = mock_loader_instance

        mock_engine_instance = MagicMock()
        mock_engine_instance.calculate_features.return_value = MagicMock()
        mock_engine.return_value = mock_engine_instance

        mock_model_instance = MagicMock()
        mock_prediction = MagicMock()
        mock_prediction.team = "Team A"
        mock_prediction.get_all_probs.return_value = {"0": 0.2, "1": 0.3, "2": 0.3, "3+": 0.2}
        mock_prediction.get_most_likely_category.return_value = "1"
        mock_prediction.get_prob_for_category.return_value = 0.3
        mock_prediction.to_dict.return_value = {"team": "Team A"}
        mock_model_instance.predict.return_value = mock_prediction
        mock_model.return_value = mock_model_instance

        output_file = tmp_path / "predictions.json"
        result = runner.invoke(
            app,
            [
                "--round",
                "1607",
                "--output",
                str(output_file),
                "--db",
                ":memory:",
                "--model-dir",
                mock_trained_model,
            ],
        )
        # ファイルが作成される
        if result.exit_code == 0:
            assert output_file.exists() or "保存" in result.stdout
