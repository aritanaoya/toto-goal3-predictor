"""ModelEnsembleのテスト"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from toto_predictor.models.exceptions import ModelError, ModelNotTrainedError, PredictionError
from toto_predictor.models.prediction import Prediction
from toto_predictor.models.team_features import TeamFeatures
from toto_predictor.services.model_ensemble import ModelEnsemble


class TestModelEnsembleInit:
    """初期化テスト"""

    def test_init_creates_directory(self, tmp_path):
        """ディレクトリが作成される"""
        model_dir = tmp_path / "new_models"
        ModelEnsemble(str(model_dir))  # 初期化でディレクトリ作成
        assert model_dir.exists()

    def test_init_sets_defaults(self, tmp_path):
        """デフォルト値が設定される"""
        ensemble = ModelEnsemble(str(tmp_path))
        assert ensemble.poisson_model is None
        assert ensemble.xgb_model is None
        assert ensemble.calibrator is None
        assert ensemble.weights["poisson"] == 0.3
        assert ensemble.weights["xgboost"] == 0.7


class TestModelEnsembleTrain:
    """学習テスト"""

    @pytest.fixture
    def sample_data(self):
        """サンプル学習データ"""
        np.random.seed(42)
        n_samples = 100
        features = pd.DataFrame(
            {
                "goals_mean": np.random.uniform(0.5, 2.5, n_samples),
                "xg_mean": np.random.uniform(0.5, 2.0, n_samples),
                "shots_mean": np.random.uniform(8, 18, n_samples),
                "is_home": np.random.choice([0, 1], n_samples),
            }
        )
        targets = pd.Series(np.random.poisson(1.5, n_samples))
        return features, targets

    def test_train_creates_models(self, tmp_path, sample_data):
        """学習によりモデルが作成される"""
        features, targets = sample_data
        ensemble = ModelEnsemble(str(tmp_path))

        ensemble.train(features, targets, cv_folds=3)  # 学習実行

        assert ensemble.poisson_model is not None
        assert ensemble.xgb_model is not None
        assert ensemble.calibrator is not None
        assert ensemble.feature_names == list(features.columns)

    def test_train_returns_metrics(self, tmp_path, sample_data):
        """学習が評価指標を返す"""
        features, targets = sample_data
        ensemble = ModelEnsemble(str(tmp_path))

        metrics = ensemble.train(features, targets, cv_folds=3)

        assert "brier_score" in metrics
        assert "brier_score_std" in metrics
        assert "accuracy" in metrics
        assert "accuracy_std" in metrics
        assert "cv_folds" in metrics
        assert "n_samples" in metrics
        assert 0 <= metrics["brier_score"] <= 1
        assert 0 <= metrics["accuracy"] <= 1


class TestModelEnsemblePredict:
    """予測テスト"""

    @pytest.fixture
    def trained_ensemble(self, tmp_path):
        """学習済みモデル"""
        np.random.seed(42)
        n_samples = 50
        features = pd.DataFrame(
            {
                "goals_mean": np.random.uniform(0.5, 2.5, n_samples),
                "xg_mean": np.random.uniform(0.5, 2.0, n_samples),
                "shots_mean": np.random.uniform(8, 18, n_samples),
                "is_home": np.random.choice([0, 1], n_samples),
            }
        )
        targets = pd.Series(np.random.poisson(1.5, n_samples))

        ensemble = ModelEnsemble(str(tmp_path))
        ensemble.train(features, targets, cv_folds=2)
        return ensemble

    def test_predict_without_training_raises_error(self, tmp_path):
        """未学習エラー"""
        ensemble = ModelEnsemble(str(tmp_path))

        with pytest.raises(ModelNotTrainedError) as exc_info:
            ensemble.predict(pd.DataFrame({"goals_mean": [1.5]}))

        assert "モデルが学習されていません" in str(exc_info.value)

    def test_predict_with_dataframe(self, trained_ensemble):
        """DataFrameで予測"""
        features = pd.DataFrame(
            {
                "goals_mean": [1.5],
                "xg_mean": [1.2],
                "shots_mean": [12.0],
                "is_home": [1],
            }
        )

        prediction = trained_ensemble.predict(features, round_number=1607)

        assert isinstance(prediction, Prediction)
        assert prediction.team == "Unknown"
        assert prediction.round_number == 1607
        assert 0 <= prediction.prob_0 <= 1
        assert 0 <= prediction.prob_1 <= 1
        assert 0 <= prediction.prob_2 <= 1
        assert 0 <= prediction.prob_3plus <= 1
        # 確率の合計が約1
        total = prediction.prob_0 + prediction.prob_1 + prediction.prob_2 + prediction.prob_3plus
        assert abs(total - 1.0) < 0.01

    def test_predict_with_team_features(self, tmp_path):
        """TeamFeaturesで予測"""
        # TeamFeaturesの全特徴量に対応したモデルを学習
        np.random.seed(42)
        n_samples = 100
        feature_names = TeamFeatures.get_feature_names()
        features = pd.DataFrame(
            {name: np.random.uniform(0, 2, n_samples) for name in feature_names}
        )
        targets = pd.Series(np.random.poisson(1.5, n_samples))

        ensemble = ModelEnsemble(str(tmp_path))
        ensemble.train(features, targets, cv_folds=3)

        team_features = TeamFeatures(
            team="Test Team",
            goals_mean=1.5,
            xg_mean=1.2,
            shots_mean=12.0,
            possession_mean=55.0,
            ppda_mean=8.5,
        )

        prediction = ensemble.predict(team_features, round_number=1607)

        assert isinstance(prediction, Prediction)
        assert prediction.team == "Test Team"

    def test_predict_handles_missing_columns(self, trained_ensemble):
        """欠損カラムを処理"""
        # 一部カラムが欠けたデータ
        features = pd.DataFrame(
            {
                "goals_mean": [1.5],
                "xg_mean": [1.2],
            }
        )

        prediction = trained_ensemble.predict(features, round_number=1607)

        assert isinstance(prediction, Prediction)

    def test_predict_returns_prediction_with_details(self, trained_ensemble):
        """予測結果の詳細が含まれる"""
        features = pd.DataFrame(
            {
                "goals_mean": [1.5],
                "xg_mean": [1.2],
                "shots_mean": [12.0],
                "is_home": [1],
            }
        )

        prediction = trained_ensemble.predict(features, round_number=1607)

        assert prediction.poisson_lambda is not None
        assert prediction.poisson_lambda > 0
        assert prediction.xgb_probs is not None
        assert len(prediction.xgb_probs) == 6

    def test_predict_without_calibrator(self, tmp_path):
        """キャリブレーターなしで予測"""
        np.random.seed(42)
        n_samples = 50
        features = pd.DataFrame(
            {
                "goals_mean": np.random.uniform(0.5, 2.5, n_samples),
                "xg_mean": np.random.uniform(0.5, 2.0, n_samples),
                "shots_mean": np.random.uniform(8, 18, n_samples),
                "is_home": np.random.choice([0, 1], n_samples),
            }
        )
        targets = pd.Series(np.random.poisson(1.5, n_samples))

        ensemble = ModelEnsemble(str(tmp_path))
        ensemble.train(features, targets, cv_folds=2)
        ensemble.calibrator = None  # キャリブレーターを削除

        prediction = ensemble.predict(
            pd.DataFrame(
                {"goals_mean": [1.5], "xg_mean": [1.2], "shots_mean": [12.0], "is_home": [1]}
            ),
            round_number=1607,
        )

        assert isinstance(prediction, Prediction)


class TestModelEnsembleSaveLoad:
    """保存・読込テスト"""

    @pytest.fixture
    def trained_ensemble(self, tmp_path):
        """学習済みモデル"""
        np.random.seed(42)
        n_samples = 100  # キャリブレーション用に十分なサンプル数
        features = pd.DataFrame(
            {
                "goals_mean": np.random.uniform(0.5, 2.5, n_samples),
                "xg_mean": np.random.uniform(0.5, 2.0, n_samples),
                "shots_mean": np.random.uniform(8, 18, n_samples),
                "is_home": np.random.choice([0, 1], n_samples),
            }
        )
        targets = pd.Series(np.random.poisson(1.5, n_samples))

        ensemble = ModelEnsemble(str(tmp_path))
        ensemble.train(features, targets, cv_folds=3)
        return ensemble

    def test_save_creates_files(self, trained_ensemble):
        """保存がファイルを作成"""
        trained_ensemble.save()

        model_dir = trained_ensemble.model_dir
        assert (model_dir / "poisson_model.joblib").exists()
        assert (model_dir / "xgb_model.joblib").exists()
        assert (model_dir / "calibrator.joblib").exists()
        assert (model_dir / "metadata.json").exists()

    def test_save_without_model_raises_error(self, tmp_path):
        """モデルなしで保存はエラー"""
        ensemble = ModelEnsemble(str(tmp_path))

        with pytest.raises(ModelError) as exc_info:
            ensemble.save()

        assert "保存するモデルがありません" in str(exc_info.value)

    def test_load_restores_model(self, trained_ensemble, tmp_path):
        """読込がモデルを復元"""
        trained_ensemble.save()

        # 新しいインスタンスで読み込み
        new_ensemble = ModelEnsemble(str(trained_ensemble.model_dir))
        new_ensemble.load()

        assert new_ensemble.poisson_model is not None
        assert new_ensemble.xgb_model is not None
        assert new_ensemble.feature_names == trained_ensemble.feature_names

    def test_load_missing_model_raises_error(self, tmp_path):
        """モデルファイルなしで読込はエラー"""
        ensemble = ModelEnsemble(str(tmp_path))

        with pytest.raises(ModelNotTrainedError) as exc_info:
            ensemble.load()

        assert "モデルファイルが見つかりません" in str(exc_info.value)

    def test_load_without_calibrator(self, trained_ensemble):
        """キャリブレーターなしで読込"""
        trained_ensemble.save()
        # キャリブレーターファイルを削除
        (trained_ensemble.model_dir / "calibrator.joblib").unlink()

        new_ensemble = ModelEnsemble(str(trained_ensemble.model_dir))
        new_ensemble.load()

        assert new_ensemble.poisson_model is not None
        assert new_ensemble.xgb_model is not None
        assert new_ensemble.calibrator is None

    def test_load_without_metadata(self, trained_ensemble):
        """メタデータなしで読込"""
        trained_ensemble.save()
        # メタデータファイルを削除
        (trained_ensemble.model_dir / "metadata.json").unlink()

        new_ensemble = ModelEnsemble(str(trained_ensemble.model_dir))
        new_ensemble.load()

        assert new_ensemble.poisson_model is not None
        assert new_ensemble.feature_names == []


class TestModelEnsembleProbConversion:
    """確率変換テスト"""

    def test_poisson_to_toto_probs(self, tmp_path):
        """ポアソン確率変換"""
        ensemble = ModelEnsemble(str(tmp_path))

        probs = ensemble._poisson_to_toto_probs(1.5)

        assert "0" in probs
        assert "1" in probs
        assert "2" in probs
        assert "3+" in probs
        assert all(0 <= p <= 1 for p in probs.values())
        assert abs(sum(probs.values()) - 1.0) < 0.01

    def test_poisson_to_toto_probs_zero_lambda(self, tmp_path):
        """λ=0の場合"""
        ensemble = ModelEnsemble(str(tmp_path))

        probs = ensemble._poisson_to_toto_probs(0.0)

        assert probs["0"] > 0.99  # ほぼ1
        assert probs["1"] < 0.01
        assert probs["2"] < 0.01
        assert probs["3+"] < 0.01

    def test_poisson_to_toto_probs_high_lambda(self, tmp_path):
        """λが高い場合"""
        ensemble = ModelEnsemble(str(tmp_path))

        probs = ensemble._poisson_to_toto_probs(5.0)

        assert probs["3+"] > probs["0"]  # 3点以上の確率が高い

    def test_xgb_to_toto_probs(self, tmp_path):
        """XGBoost確率変換"""
        ensemble = ModelEnsemble(str(tmp_path))
        xgb_probs = np.array([0.1, 0.2, 0.25, 0.15, 0.15, 0.15])

        probs = ensemble._xgb_to_toto_probs(xgb_probs)

        assert probs["0"] == pytest.approx(0.1, abs=0.001)
        assert probs["1"] == pytest.approx(0.2, abs=0.001)
        assert probs["2"] == pytest.approx(0.25, abs=0.001)
        assert probs["3+"] == pytest.approx(0.45, abs=0.001)  # 0.15 + 0.15 + 0.15

    def test_ensemble_probs(self, tmp_path):
        """アンサンブル確率"""
        ensemble = ModelEnsemble(str(tmp_path))
        poisson_probs = {"0": 0.2, "1": 0.3, "2": 0.25, "3+": 0.25}
        xgb_probs = {"0": 0.15, "1": 0.35, "2": 0.3, "3+": 0.2}

        final = ensemble._ensemble_probs(poisson_probs, xgb_probs)

        # 重み: poisson=0.3, xgb=0.7
        expected_0 = 0.3 * 0.2 + 0.7 * 0.15
        expected_1 = 0.3 * 0.3 + 0.7 * 0.35
        assert abs(final["0"] - expected_0) < 0.001
        assert abs(final["1"] - expected_1) < 0.001


class TestModelEnsembleCrossValidate:
    """クロスバリデーションテスト"""

    def test_cross_validate_returns_metrics(self, tmp_path):
        """CVが評価指標を返す"""
        np.random.seed(42)
        n_samples = 50
        features = pd.DataFrame(
            {
                "goals_mean": np.random.uniform(0.5, 2.5, n_samples),
                "xg_mean": np.random.uniform(0.5, 2.0, n_samples),
                "shots_mean": np.random.uniform(8, 18, n_samples),
                "is_home": np.random.choice([0, 1], n_samples),
            }
        )
        targets = pd.Series(np.random.poisson(1.5, n_samples))

        ensemble = ModelEnsemble(str(tmp_path))
        metrics = ensemble._cross_validate(features, targets, cv_folds=3)

        assert "brier_score" in metrics
        assert "accuracy" in metrics
        assert metrics["cv_folds"] == 3
        assert metrics["n_samples"] == n_samples
