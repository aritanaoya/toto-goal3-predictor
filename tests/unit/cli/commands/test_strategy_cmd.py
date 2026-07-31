"""strategyコマンドのテスト"""

import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from toto_predictor.cli.commands.strategy_cmd import app
from toto_predictor.models.exceptions import TotoPredictorError


class TestStrategyCommand:
    """strategyコマンドのテスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_strategy_help(self, runner):
        """ヘルプが表示される"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--round" in result.stdout
        assert "--predictions" in result.stdout
        assert "--votes" in result.stdout

    def test_strategy_predictions_not_found(self, runner, tmp_path):
        """予測ファイルが見つからない"""
        result = runner.invoke(
            app,
            [
                "--round",
                "1607",
                "--predictions",
                str(tmp_path / "nonexistent.json"),
            ],
        )
        assert result.exit_code == 1
        assert "見つかりません" in result.stdout or "ファイル" in result.stdout

    def test_strategy_votes_not_found(self, runner, tmp_path, sample_prediction):
        """投票率ファイルが見つからない"""
        pred_file = tmp_path / "predictions.json"
        pred_file.write_text(json.dumps([sample_prediction.to_dict()]))

        result = runner.invoke(
            app,
            [
                "--predictions",
                str(pred_file),
                "--votes",
                str(tmp_path / "nonexistent.json"),
            ],
        )
        assert result.exit_code == 1

    @patch("toto_predictor.cli.commands.strategy_cmd.StrategyEngine")
    def test_strategy_success(
        self, mock_engine, runner, tmp_path, sample_prediction, sample_vote_rate
    ):
        """正常な戦略計算が成功する"""
        # ファイル作成
        pred_file = tmp_path / "predictions.json"
        pred_file.write_text(json.dumps([sample_prediction.to_dict()]))

        vote_file = tmp_path / "votes.json"
        vote_file.write_text(json.dumps([sample_vote_rate.to_dict()]))

        # モック設定
        mock_engine_instance = MagicMock()
        mock_recommendation = MagicMock()
        mock_recommendation.team = "Yokohama F. Marinos"
        mock_recommendation.category = "1"
        mock_recommendation.model_prob = 0.32
        mock_recommendation.vote_rate = 0.35
        mock_recommendation.value_score = 0.91
        mock_recommendation.action = "スキップ"
        mock_engine_instance.calculate_value_scores.return_value = [mock_recommendation]
        mock_engine_instance.generate_report.return_value = str(tmp_path / "report.md")
        mock_engine.return_value = mock_engine_instance

        result = runner.invoke(
            app,
            [
                "--round",
                "1607",
                "--predictions",
                str(pred_file),
                "--votes",
                str(vote_file),
            ],
        )
        assert result.exit_code == 0
        assert "購入戦略" in result.stdout or "レポート" in result.stdout

    @patch("toto_predictor.cli.commands.strategy_cmd.StrategyEngine")
    def test_strategy_with_output_option(
        self, mock_engine, runner, tmp_path, sample_prediction, sample_vote_rate
    ):
        """出力先オプション"""
        pred_file = tmp_path / "predictions.json"
        pred_file.write_text(json.dumps([sample_prediction.to_dict()]))

        vote_file = tmp_path / "votes.json"
        vote_file.write_text(json.dumps([sample_vote_rate.to_dict()]))

        output_file = tmp_path / "custom_report.md"

        mock_engine_instance = MagicMock()
        mock_engine_instance.calculate_value_scores.return_value = []
        mock_engine_instance.generate_report.return_value = str(output_file)
        mock_engine.return_value = mock_engine_instance

        result = runner.invoke(
            app,
            [
                "--round",
                "1607",
                "--predictions",
                str(pred_file),
                "--votes",
                str(vote_file),
                "--output",
                str(output_file),
            ],
        )
        # カスタム出力先が使用される
        assert result.exit_code == 0

    @patch("toto_predictor.cli.commands.strategy_cmd.StrategyEngine")
    def test_strategy_buy_recommendations(
        self, mock_engine, runner, tmp_path, sample_prediction, sample_vote_rate
    ):
        """推奨購入が表示される"""
        pred_file = tmp_path / "predictions.json"
        pred_file.write_text(json.dumps([sample_prediction.to_dict()]))

        vote_file = tmp_path / "votes.json"
        vote_file.write_text(json.dumps([sample_vote_rate.to_dict()]))

        mock_engine_instance = MagicMock()
        mock_rec = MagicMock()
        mock_rec.team = "Test Team"
        mock_rec.category = "1"
        mock_rec.model_prob = 0.40
        mock_rec.vote_rate = 0.25
        mock_rec.value_score = 1.6
        mock_rec.action = "必買"
        mock_engine_instance.calculate_value_scores.return_value = [mock_rec]
        mock_engine_instance.generate_report.return_value = str(tmp_path / "report.md")
        mock_engine.return_value = mock_engine_instance

        result = runner.invoke(
            app,
            [
                "--round",
                "1607",
                "--predictions",
                str(pred_file),
                "--votes",
                str(vote_file),
            ],
        )
        # 推奨購入が表示される
        assert "推奨購入" in result.stdout or "バリュー" in result.stdout

    @patch("toto_predictor.cli.commands.strategy_cmd.StrategyEngine")
    def test_strategy_error_handling(
        self, mock_engine, runner, tmp_path, sample_prediction, sample_vote_rate
    ):
        """エラーハンドリング"""
        pred_file = tmp_path / "predictions.json"
        pred_file.write_text(json.dumps([sample_prediction.to_dict()]))

        vote_file = tmp_path / "votes.json"
        vote_file.write_text(json.dumps([sample_vote_rate.to_dict()]))

        mock_engine_instance = MagicMock()
        mock_engine_instance.calculate_value_scores.side_effect = TotoPredictorError("テストエラー")
        mock_engine.return_value = mock_engine_instance

        result = runner.invoke(
            app,
            [
                "--predictions",
                str(pred_file),
                "--votes",
                str(vote_file),
            ],
        )
        assert result.exit_code == 1
        assert "エラー" in result.stdout

    def test_strategy_auto_file_detection(self, runner, tmp_path):
        """ファイル自動検出（round指定時）"""
        # round指定時にdata/predictions/round_X.jsonを探す
        result = runner.invoke(
            app,
            [
                "--round",
                "9999",  # 存在しない回号
            ],
        )
        assert result.exit_code == 1
        # ファイルが見つからないエラー
        assert "見つかりません" in result.stdout
