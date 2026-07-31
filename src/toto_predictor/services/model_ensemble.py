"""モデルアンサンブル

このモジュールは、Poisson Regression + XGBoostのアンサンブルモデルを提供します。
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import PoissonRegressor
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier

from ..models.exceptions import ModelError, ModelNotTrainedError, PredictionError
from ..models.matchup_features import MatchupFeatures
from ..models.prediction import Prediction
from ..models.team_features import TeamFeatures

logger = logging.getLogger(__name__)


class ModelEnsemble:
    """Poisson + XGBoostアンサンブルモデル

    得点分布予測のためのアンサンブルモデルを提供します。
    - Poisson Regression: 期待得点（λ）を予測し、確率分布に変換
    - XGBoost: 得点カテゴリを直接分類

    Attributes:
        model_dir: モデル保存ディレクトリ
        poisson_model: Poisson Regressionモデル
        xgb_model: XGBoostモデル
        calibrator: キャリブレーター
        weights: アンサンブル重み
    """

    POISSON_WEIGHT = 0.3
    XGB_WEIGHT = 0.7

    def __init__(self, model_dir: str) -> None:
        """モデルアンサンブルを初期化

        Args:
            model_dir: モデル保存ディレクトリのパス
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.poisson_model: PoissonRegressor | None = None
        self.xgb_model: XGBClassifier | None = None
        self.calibrator: CalibratedClassifierCV | None = None
        self.feature_names: list[str] = []
        self.weights = {"poisson": self.POISSON_WEIGHT, "xgboost": self.XGB_WEIGHT}

    def train(
        self,
        features: pd.DataFrame,
        targets: pd.Series,
        cv_folds: int = 5,
    ) -> dict[str, Any]:
        """モデルを学習

        Args:
            features: 特徴量DataFrame
            targets: 目的変数（得点）
            cv_folds: 時系列クロスバリデーションのフォールド数

        Returns:
            検証結果の辞書（Brier Score、的中率など）
        """
        logger.info(f"モデル学習開始: {len(features)}サンプル, {len(features.columns)}特徴量")

        self.feature_names = list(features.columns)

        # 1. Poisson Regression
        logger.info("Poisson Regressionを学習中...")
        self.poisson_model = PoissonRegressor(alpha=0.1, max_iter=1000)
        self.poisson_model.fit(features, targets)

        # 2. XGBoost (得点を0-3にクリップして4クラス分類)
        logger.info("XGBoostを学習中...")
        targets_clipped = targets.clip(upper=3)
        self.xgb_model = XGBClassifier(
            objective="multi:softprob",
            num_class=4,
            max_depth=6,
            learning_rate=0.05,
            n_estimators=500,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            use_label_encoder=False,
            eval_metric="mlogloss",
        )
        self.xgb_model.fit(features, targets_clipped)

        # 3. キャリブレーション
        logger.info("キャリブレーションを実行中...")
        # XGBoostに対してキャリブレーションを適用
        self.calibrator = CalibratedClassifierCV(
            estimator=XGBClassifier(
                objective="multi:softprob",
                num_class=4,
                max_depth=6,
                learning_rate=0.05,
                n_estimators=200,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                use_label_encoder=False,
                eval_metric="mlogloss",
            ),
            method="isotonic",
            cv=min(cv_folds, 3),
        )
        self.calibrator.fit(features, targets_clipped)

        # 4. クロスバリデーションによる評価
        logger.info("クロスバリデーションを実行中...")
        metrics = self._cross_validate(features, targets, cv_folds)

        logger.info(
            f"学習完了: Brier Score={metrics['brier_score']:.4f}, "
            f"的中率={metrics['accuracy'] * 100:.1f}%"
        )

        return metrics

    def predict(
        self,
        features: TeamFeatures | MatchupFeatures | pd.DataFrame,
        round_number: int = 0,
    ) -> Prediction:
        """得点分布を予測

        Args:
            features: TeamFeatures、MatchupFeatures、または特徴量DataFrame
            round_number: toto回号

        Returns:
            Predictionオブジェクト

        Raises:
            ModelNotTrainedError: モデルが学習されていない場合
            PredictionError: 予測に失敗した場合
        """
        if self.poisson_model is None or self.xgb_model is None:
            raise ModelNotTrainedError(
                "モデルが学習されていません。先にtrain()を実行してください。"
            )

        try:
            # 特徴量の準備
            if isinstance(features, MatchupFeatures):
                team_name = features.team
                features_df = pd.DataFrame([features.to_dict()])
                features_df = features_df.drop(
                    columns=["team", "opponent", "calculated_at"], errors="ignore"
                )
                # is_homeをintに変換
                if "is_home" in features_df.columns:
                    features_df["is_home"] = features_df["is_home"].astype(int)
            elif isinstance(features, TeamFeatures):
                team_name = features.team
                features_df = pd.DataFrame([features.to_dict()])
                features_df = features_df.drop(columns=["team", "calculated_at"], errors="ignore")
                # is_homeがない場合は追加（デフォルト: 0）
                if "is_home" not in features_df.columns:
                    features_df["is_home"] = 0
            else:
                team_name = "Unknown"
                features_df = features

            # 特徴量の順序を合わせる
            missing_cols = set(self.feature_names) - set(features_df.columns)
            for col in missing_cols:
                features_df[col] = 0
            features_df = features_df[self.feature_names]

            # 1. Poisson予測
            poisson_lambda = float(self.poisson_model.predict(features_df)[0])
            poisson_probs = self._poisson_to_toto_probs(poisson_lambda)

            # 2. XGBoost予測
            if self.calibrator is not None:
                xgb_raw_probs = self.calibrator.predict_proba(features_df)[0]
            else:
                xgb_raw_probs = self.xgb_model.predict_proba(features_df)[0]
            xgb_probs = self._xgb_to_toto_probs(xgb_raw_probs)

            # 3. アンサンブル
            final_probs = self._ensemble_probs(poisson_probs, xgb_probs)

            return Prediction(
                round_number=round_number,
                team=team_name,
                prob_0=final_probs["0"],
                prob_1=final_probs["1"],
                prob_2=final_probs["2"],
                prob_3plus=final_probs["3+"],
                poisson_lambda=poisson_lambda,
                xgb_probs=list(xgb_raw_probs),
            )

        except Exception as e:
            raise PredictionError(f"予測に失敗しました: {e}") from e

    def save(self) -> None:
        """モデルをファイルに保存

        Raises:
            ModelError: 保存に失敗した場合
        """
        if self.poisson_model is None or self.xgb_model is None:
            raise ModelError("保存するモデルがありません")

        try:
            joblib.dump(self.poisson_model, self.model_dir / "poisson_model.joblib")
            joblib.dump(self.xgb_model, self.model_dir / "xgb_model.joblib")

            if self.calibrator is not None:
                joblib.dump(self.calibrator, self.model_dir / "calibrator.joblib")

            # メタデータ保存
            metadata = {
                "feature_names": self.feature_names,
                "weights": self.weights,
                "saved_at": datetime.now().isoformat(),
            }
            with open(self.model_dir / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"モデルを保存しました: {self.model_dir}")

        except Exception as e:
            raise ModelError(f"モデルの保存に失敗しました: {e}") from e

    def load(self) -> None:
        """保存済みモデルを読み込み

        Raises:
            ModelNotTrainedError: モデルファイルが見つからない場合
        """
        poisson_path = self.model_dir / "poisson_model.joblib"
        xgb_path = self.model_dir / "xgb_model.joblib"

        if not poisson_path.exists() or not xgb_path.exists():
            raise ModelNotTrainedError(
                f"モデルファイルが見つかりません: {self.model_dir}",
                details={"model_dir": str(self.model_dir)},
            )

        try:
            self.poisson_model = joblib.load(poisson_path)
            self.xgb_model = joblib.load(xgb_path)

            calibrator_path = self.model_dir / "calibrator.joblib"
            if calibrator_path.exists():
                self.calibrator = joblib.load(calibrator_path)

            # メタデータ読み込み
            metadata_path = self.model_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
                    self.feature_names = metadata.get("feature_names", [])
                    self.weights = metadata.get("weights", self.weights)

            logger.info(f"モデルを読み込みました: {self.model_dir}")

        except Exception as e:
            raise ModelNotTrainedError(f"モデルの読み込みに失敗しました: {e}") from e

    def _poisson_to_toto_probs(self, lambda_: float) -> dict[str, float]:
        """ポアソンλからtotoカテゴリ確率に変換

        Args:
            lambda_: ポアソン分布のλ（期待得点）

        Returns:
            カテゴリと確率の辞書
        """
        p_0 = poisson.pmf(0, lambda_)
        p_1 = poisson.pmf(1, lambda_)
        p_2 = poisson.pmf(2, lambda_)
        p_3plus = 1 - p_0 - p_1 - p_2

        return {"0": p_0, "1": p_1, "2": p_2, "3+": p_3plus}

    def _xgb_to_toto_probs(self, probs: np.ndarray) -> dict[str, float]:
        """XGBoost出力をtotoカテゴリに変換

        Args:
            probs: XGBoostの確率出力（4クラス: 0, 1, 2, 3+）

        Returns:
            カテゴリと確率の辞書
        """
        return {
            "0": float(probs[0]),
            "1": float(probs[1]),
            "2": float(probs[2]),
            "3+": float(probs[3]) if len(probs) > 3 else float(1 - probs[:3].sum()),
        }

    def _ensemble_probs(
        self, poisson_probs: dict[str, float], xgb_probs: dict[str, float]
    ) -> dict[str, float]:
        """アンサンブル予測

        Args:
            poisson_probs: Poissonモデルの確率
            xgb_probs: XGBoostモデルの確率

        Returns:
            重み付き平均確率
        """
        final = {}
        for cat in ["0", "1", "2", "3+"]:
            final[cat] = (
                self.weights["poisson"] * poisson_probs[cat]
                + self.weights["xgboost"] * xgb_probs[cat]
            )
        return final

    def _cross_validate(
        self, features: pd.DataFrame, targets: pd.Series, cv_folds: int
    ) -> dict[str, Any]:
        """時系列クロスバリデーションで評価

        Args:
            features: 特徴量DataFrame
            targets: 目的変数
            cv_folds: フォールド数

        Returns:
            評価指標の辞書
        """
        tscv = TimeSeriesSplit(n_splits=cv_folds)
        brier_scores = []
        accuracies = []

        for train_idx, val_idx in tscv.split(features):
            feat_train = features.iloc[train_idx]
            tgt_train = targets.iloc[train_idx]

            # Poissonモデル
            poisson = PoissonRegressor(alpha=0.1, max_iter=1000)
            poisson.fit(feat_train, tgt_train)

            # XGBoostモデル
            tgt_train_clipped = tgt_train.clip(upper=3)
            xgb = XGBClassifier(
                objective="multi:softprob",
                num_class=4,
                max_depth=6,
                learning_rate=0.05,
                n_estimators=200,
                random_state=42,
                use_label_encoder=False,
                eval_metric="mlogloss",
            )
            xgb.fit(feat_train, tgt_train_clipped)

            # 予測
            for idx in val_idx:
                feat_sample = features.iloc[[idx]]
                y_true = targets.iloc[idx]

                # アンサンブル予測
                poisson_lambda = poisson.predict(feat_sample)[0]
                poisson_probs = self._poisson_to_toto_probs(poisson_lambda)
                xgb_probs = self._xgb_to_toto_probs(xgb.predict_proba(feat_sample)[0])
                final_probs = self._ensemble_probs(poisson_probs, xgb_probs)

                # totoカテゴリに変換
                true_cat = (
                    "0" if y_true == 0 else "1" if y_true == 1 else "2" if y_true == 2 else "3+"
                )

                # Brier Scoreの計算
                brier = sum(
                    (final_probs[cat] - (1 if cat == true_cat else 0)) ** 2
                    for cat in ["0", "1", "2", "3+"]
                )
                brier_scores.append(brier / 4)  # 4カテゴリで正規化

                # 的中判定
                pred_cat = max(final_probs, key=final_probs.get)  # type: ignore
                accuracies.append(1 if pred_cat == true_cat else 0)

        return {
            "brier_score": np.mean(brier_scores),
            "brier_score_std": np.std(brier_scores),
            "accuracy": np.mean(accuracies),
            "accuracy_std": np.std(accuracies),
            "cv_folds": cv_folds,
            "n_samples": len(targets),
        }
