"""trainコマンドのテスト"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from typer.testing import CliRunner

from toto_predictor.cli.commands.train_cmd import app


class TestTrainCommand:
    """trainコマンドのテスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_train_help(self, runner):
        """ヘルプが表示される"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--seasons" in result.stdout
        assert "--cv" in result.stdout

    @patch("toto_predictor.cli.commands.train_cmd.ModelEnsemble")
    @patch("toto_predictor.cli.commands.train_cmd.FeatureEngine")
    def test_train_success(self, mock_engine, mock_model, runner, populated_db, tmp_path):
        """正常な学習が成功する"""
        # FeatureEngineのモック
        mock_engine_instance = MagicMock()
        mock_engine_instance.prepare_training_data.return_value = (
            pd.DataFrame({"feature1": [1, 2, 3], "feature2": [4, 5, 6]}),
            pd.Series([0, 1, 2]),
        )
        mock_engine.return_value = mock_engine_instance

        # ModelEnsembleのモック
        mock_model_instance = MagicMock()
        mock_model_instance.train.return_value = {
            "brier_score": 0.15,
            "brier_score_std": 0.02,
            "accuracy": 0.45,
            "accuracy_std": 0.05,
            "n_samples": 100,
            "cv_folds": 5,
        }
        mock_model.return_value = mock_model_instance

        result = runner.invoke(
            app,
            [
                "--seasons",
                "2025",
                "--db",
                populated_db,
                "--model-dir",
                str(tmp_path / "models"),
            ],
        )
        assert result.exit_code == 0
        assert "学習完了" in result.stdout or "Brier" in result.stdout

    def test_train_data_not_found(self, runner, temp_db, tmp_path):
        """データが見つからない場合のエラー"""
        result = runner.invoke(
            app,
            [
                "--seasons",
                "2025",
                "--db",
                temp_db,
                "--model-dir",
                str(tmp_path / "models"),
            ],
        )
        assert result.exit_code == 1
        assert "見つかりません" in result.stdout or "データ" in result.stdout

    @patch("toto_predictor.cli.commands.train_cmd.ModelEnsemble")
    @patch("toto_predictor.cli.commands.train_cmd.FeatureEngine")
    def test_train_multiple_seasons(self, mock_engine, mock_model, runner, tmp_path):
        """複数シーズンでの学習"""
        mock_engine_instance = MagicMock()
        mock_engine_instance.prepare_training_data.return_value = (
            pd.DataFrame({"f1": [1, 2]}),
            pd.Series([0, 1]),
        )
        mock_engine.return_value = mock_engine_instance

        mock_model_instance = MagicMock()
        mock_model_instance.train.return_value = {
            "brier_score": 0.18,
            "brier_score_std": 0.03,
            "accuracy": 0.40,
            "accuracy_std": 0.06,
            "n_samples": 50,
            "cv_folds": 3,
        }
        mock_model.return_value = mock_model_instance

        runner.invoke(
            app,
            [
                "--seasons",
                "2024,2025",
                "--cv",
                "3",
                "--db",
                ":memory:",
                "--model-dir",
                str(tmp_path / "models"),
            ],
        )
        # 複数シーズンが解析される
        mock_engine_instance.prepare_training_data.assert_called_once()
        call_args = mock_engine_instance.prepare_training_data.call_args[0]
        assert 2024 in call_args[0] and 2025 in call_args[0]

    @patch("toto_predictor.cli.commands.train_cmd.ModelEnsemble")
    @patch("toto_predictor.cli.commands.train_cmd.FeatureEngine")
    def test_train_model_error(self, mock_engine, mock_model, runner, tmp_path):
        """モデルエラーの処理"""
        from toto_predictor.models.exceptions import ModelError

        mock_engine_instance = MagicMock()
        mock_engine_instance.prepare_training_data.return_value = (
            pd.DataFrame({"f1": [1, 2]}),
            pd.Series([0, 1]),
        )
        mock_engine.return_value = mock_engine_instance

        mock_model_instance = MagicMock()
        mock_model_instance.train.side_effect = ModelError("テストエラー")
        mock_model.return_value = mock_model_instance

        result = runner.invoke(
            app,
            [
                "--seasons",
                "2025",
                "--db",
                ":memory:",
                "--model-dir",
                str(tmp_path / "models"),
            ],
        )
        assert result.exit_code == 1
        assert "エラー" in result.stdout

    @patch("toto_predictor.cli.commands.train_cmd.ModelEnsemble")
    @patch("toto_predictor.cli.commands.train_cmd.FeatureEngine")
    def test_train_cv_folds_option(self, mock_engine, mock_model, runner, tmp_path):
        """CVフォールド数オプションが渡される"""
        mock_engine_instance = MagicMock()
        mock_engine_instance.prepare_training_data.return_value = (
            pd.DataFrame({"f1": [1, 2, 3]}),
            pd.Series([0, 1, 2]),
        )
        mock_engine.return_value = mock_engine_instance

        mock_model_instance = MagicMock()
        mock_model_instance.train.return_value = {
            "brier_score": 0.15,
            "brier_score_std": 0.02,
            "accuracy": 0.45,
            "accuracy_std": 0.05,
            "n_samples": 100,
            "cv_folds": 10,
        }
        mock_model.return_value = mock_model_instance

        runner.invoke(
            app,
            [
                "--seasons",
                "2025",
                "--cv",
                "10",
                "--db",
                ":memory:",
                "--model-dir",
                str(tmp_path / "models"),
            ],
        )
        # cv_folds=10が渡される
        mock_model_instance.train.assert_called_once()
        call_kwargs = mock_model_instance.train.call_args[1]
        assert call_kwargs.get("cv_folds") == 10
