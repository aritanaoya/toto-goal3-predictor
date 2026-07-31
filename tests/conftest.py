"""テスト用共通フィクスチャ"""

import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from toto_predictor.db.database import Database
from toto_predictor.db.repositories.match_repository import MatchRepository
from toto_predictor.db.repositories.team_stats_repository import TeamStatsRepository
from toto_predictor.models.match import Match
from toto_predictor.models.team_stats import TeamStats


@pytest.fixture
def temp_db():
    """テスト用一時データベース"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    Database(db_path)  # テーブル初期化
    yield db_path

    # クリーンアップ
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def memory_db():
    """インメモリデータベース"""
    return Database(":memory:")


@pytest.fixture
def sample_match():
    """サンプル試合データ"""
    return Match(
        date=datetime(2025, 12, 1),
        season=2025,
        competition="Japan. J1 League",
        home_team="Yokohama F. Marinos",
        away_team="Kawasaki Frontale",
        home_goals=2,
        away_goals=1,
        duration=90,
    )


@pytest.fixture
def sample_team_stats(sample_match):
    """サンプルチーム統計データ"""
    return TeamStats(
        match_id=sample_match.id,
        team="Yokohama F. Marinos",
        is_home=True,
        goals=2,
        xg=1.8,
        shots=15,
        shots_on_target=8,
        possession=55.0,
        passes=450,
        passes_accurate=380,
        crosses=20,
        crosses_accurate=8,
        pen_area_entries=25,
        conceded_goals=1,
        xg_against=0.9,
        shots_against=10,
        shots_against_on_target=4,
        ppda=8.5,
        interceptions=15,
        fouls=12,
        yellow_cards=2,
        red_cards=0,
        corners=6,
    )


@pytest.fixture
def populated_db(temp_db):
    """サンプルデータが入ったデータベース"""
    db = Database(temp_db)
    match_repo = MatchRepository(db)
    stats_repo = TeamStatsRepository(db)

    # 複数の試合を追加
    teams = ["Yokohama F. Marinos", "Kawasaki Frontale", "Kashima Antlers", "Urawa Reds"]

    for i in range(20):
        home_idx = i % len(teams)
        away_idx = (i + 1) % len(teams)

        match = Match(
            date=datetime(2025, 1, 1 + i),
            season=2025,
            competition="Japan. J1 League",
            home_team=teams[home_idx],
            away_team=teams[away_idx],
            home_goals=i % 4,
            away_goals=(i + 1) % 3,
            duration=90,
        )
        match_repo.save(match)

        # ホームチーム統計
        home_stats = TeamStats(
            match_id=match.id,
            team=teams[home_idx],
            is_home=True,
            goals=i % 4,
            xg=1.0 + (i % 10) / 10,
            shots=10 + i % 10,
            shots_on_target=5 + i % 5,
            possession=50 + i % 10,
            passes=400 + i * 10,
            passes_accurate=350 + i * 8,
            ppda=8.0 + i % 5,
            conceded_goals=(i + 1) % 3,
            interceptions=10 + i % 5,
        )
        stats_repo.save(home_stats)

        # アウェイチーム統計
        away_stats = TeamStats(
            match_id=match.id,
            team=teams[away_idx],
            is_home=False,
            goals=(i + 1) % 3,
            xg=0.8 + (i % 10) / 10,
            shots=8 + i % 8,
            shots_on_target=4 + i % 4,
            possession=50 - i % 10,
            passes=380 + i * 8,
            passes_accurate=320 + i * 6,
            ppda=10.0 + i % 5,
            conceded_goals=i % 4,
            interceptions=8 + i % 5,
        )
        stats_repo.save(away_stats)

    return temp_db


@pytest.fixture
def sample_excel_path(tmp_path):
    """サンプルExcelファイルを作成"""
    excel_path = tmp_path / "Team Stats Test Team.xlsx"

    # Wyscout形式のデータを作成
    data = {
        "Date": ["Test Team", "Opponents"] + [f"2025-12-{i:02d}" for i in range(1, 11)],
        "Match": [None, None]
        + [f"Home Team {i} - Away Team {i} {i}:{i - 1}" for i in range(1, 11)],
        "Competition": [None, None] + ["Japan. J1 League"] * 10,
        "Duration": [None, None] + [90] * 10,
        "Team": [None, None] + ["Test Team"] * 10,
        "Scheme": [None, None] + ["4-4-2 (100%)"] * 10,
        "Goals": [None, None] + list(range(1, 11)),
        "xG": [None, None] + [0.5 + i * 0.1 for i in range(10)],
        "Shots / on target": [None, None] + [10] * 10,
    }

    df = pd.DataFrame(data)
    df.to_excel(excel_path, index=False, engine="openpyxl")

    return str(excel_path)


@pytest.fixture
def temp_model_dir(tmp_path):
    """テスト用モデルディレクトリ"""
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    return str(model_dir)


@pytest.fixture
def cli_runner():
    """Typer CLIテスト用のCliRunner"""
    from typer.testing import CliRunner

    return CliRunner()


@pytest.fixture
def sample_prediction():
    """サンプル予測データ"""
    from toto_predictor.models.prediction import Prediction

    return Prediction(
        round_number=1607,
        team="Yokohama F. Marinos",
        prob_0=0.18,
        prob_1=0.32,
        prob_2=0.28,
        prob_3plus=0.22,
    )


@pytest.fixture
def sample_vote_rate():
    """サンプル投票率データ"""
    from toto_predictor.models.vote_rate import VoteRate

    return VoteRate(
        round_number=1607,
        team="Yokohama F. Marinos",
        vote_0=0.22,
        vote_1=0.35,
        vote_2=0.25,
        vote_3plus=0.18,
    )


@pytest.fixture
def mock_trained_model(tmp_path):
    """軽量な学習済みモデルのモック"""
    import json

    import joblib
    import numpy as np
    from sklearn.linear_model import PoissonRegressor
    from xgboost import XGBClassifier

    model_dir = tmp_path / "models"
    model_dir.mkdir(exist_ok=True)

    # 最小限のPoissonモデル
    poisson = PoissonRegressor(max_iter=10)
    x_dummy = np.array([[1, 2, 3, 4], [2, 3, 4, 5], [3, 4, 5, 6]])
    y_poisson = np.array([1, 2, 1])
    poisson.fit(x_dummy, y_poisson)
    joblib.dump(poisson, model_dir / "poisson_model.joblib")

    # 最小限のXGBoostモデル（クラスは0から始める必要がある）
    y_xgb = np.array([0, 1, 0])
    xgb = XGBClassifier(
        n_estimators=2, max_depth=2, use_label_encoder=False, eval_metric="mlogloss"
    )
    xgb.fit(x_dummy, y_xgb)
    joblib.dump(xgb, model_dir / "xgb_model.joblib")

    # メタデータ
    metadata = {
        "feature_names": ["goals_mean", "xg_mean", "shots_mean", "is_home"],
        "weights": {"poisson": 0.3, "xgboost": 0.7},
    }
    with open(model_dir / "metadata.json", "w") as f:
        json.dump(metadata, f)

    return str(model_dir)


@pytest.fixture
def sample_html_vote_rates():
    """投票率HTML（totoONE構造を模倣）"""
    return """
    <html>
    <body>
        <div class="goal3-prediction">
            <section id="goal3">
                <table>
                    <tr class="team-row">
                        <td class="team-name">Yokohama F. Marinos</td>
                        <td class="vote-rate">22.5%</td>
                        <td class="vote-rate">35.0%</td>
                        <td class="vote-rate">25.0%</td>
                        <td class="vote-rate">17.5%</td>
                    </tr>
                    <tr class="team-row">
                        <td class="team-name">Kawasaki Frontale</td>
                        <td class="vote-rate">20.0%</td>
                        <td class="vote-rate">30.0%</td>
                        <td class="vote-rate">28.0%</td>
                        <td class="vote-rate">22.0%</td>
                    </tr>
                </table>
            </section>
        </div>
    </body>
    </html>
    """
