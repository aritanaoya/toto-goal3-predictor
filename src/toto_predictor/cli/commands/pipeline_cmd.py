"""pipelineコマンド

週次パイプライン全体を実行します。
"""

import json
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...models.exceptions import TotoPredictorError
from ...services.data_loader import DataLoader
from ...services.feature_engine import FeatureEngine
from ...services.model_ensemble import ModelEnsemble
from ...services.strategy_engine import StrategyEngine
from ...services.vote_scraper import VoteScraper

app = typer.Typer()
console = Console()

DEFAULT_DB_PATH = "data/processed/toto_predictor.db"
DEFAULT_MODEL_DIR = "models"


@app.callback(invoke_without_command=True)
def pipeline(
    round_number: int = typer.Option(
        ...,
        "--round",
        "-r",
        help="toto回号",
    ),
    skip_import: bool = typer.Option(
        False,
        "--skip-import",
        help="データインポートをスキップ",
    ),
    skip_train: bool = typer.Option(
        True,
        "--skip-train",
        help="モデル学習をスキップ（デフォルト: True）",
    ),
    skip_scrape: bool = typer.Option(
        False,
        "--skip-scrape",
        help="投票率取得をスキップ",
    ),
    db_path: str = typer.Option(
        DEFAULT_DB_PATH,
        "--db",
        help="データベースファイルのパス",
    ),
    model_dir: str = typer.Option(
        DEFAULT_MODEL_DIR,
        "--model-dir",
        "-m",
        help="モデルディレクトリ",
    ),
    data_dir: str = typer.Option(
        "data/wyscout/2025",
        "--data-dir",
        "-d",
        help="Wyscoutデータディレクトリ",
    ),
    season: int = typer.Option(
        2025,
        "--season",
        "-s",
        help="シーズン年",
    ),
) -> None:
    """週次パイプライン全体を実行

    データインポート → モデル学習 → 予測 → 投票率取得 → 戦略計算 → レポート生成
    の一連のパイプラインを実行します。
    """
    console.print(
        Panel(
            f"[bold]第{round_number}回 GOAL3 パイプライン実行[/bold]\n\n"
            f"シーズン: {season}\n"
            f"データ: {data_dir}\n"
            f"モデル: {model_dir}",
            title="パイプライン開始",
            border_style="blue",
        )
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # 1. データインポート
            if not skip_import:
                task = progress.add_task(description="[1/5] データをインポート中...", total=None)
                loader = DataLoader(db_path)
                try:
                    count = loader.load_directory(data_dir, season)
                    console.print(f"  ✓ {count}件の試合データをインポート")
                except Exception as e:
                    console.print(f"  [yellow]⚠ インポートをスキップ: {e}[/yellow]")
                progress.remove_task(task)

            # 2. モデル学習（または読み込み）
            task = progress.add_task(description="[2/5] モデルを準備中...", total=None)
            model = ModelEnsemble(model_dir)

            if not skip_train:
                feature_engine = FeatureEngine(db_path)
                x_train, y_train = feature_engine.prepare_training_data([season])
                metrics = model.train(x_train, y_train)
                model.save()
                console.print(f"  ✓ モデル学習完了 (Brier: {metrics['brier_score']:.4f})")
            else:
                model.load()
                console.print("  ✓ 学習済みモデルを読み込み")
            progress.remove_task(task)

            # 3. 予測実行
            task = progress.add_task(description="[3/5] 予測を実行中...", total=None)
            feature_engine = FeatureEngine(db_path)
            loader = DataLoader(db_path)
            teams = loader.get_teams()

            predictions = []
            for team in teams:
                try:
                    features = feature_engine.calculate_features(team, datetime.now(), [5, 10, 20])
                    pred = model.predict(features, round_number)
                    predictions.append(pred)
                except Exception:
                    pass

            # 予測結果を保存
            pred_path = Path(f"data/predictions/round_{round_number}.json")
            pred_path.parent.mkdir(parents=True, exist_ok=True)
            with open(pred_path, "w") as f:
                json.dump([p.to_dict() for p in predictions], f, indent=2, ensure_ascii=False)

            console.print(f"  ✓ {len(predictions)}チームの予測完了")
            progress.remove_task(task)

            # 4. 投票率取得
            task = progress.add_task(description="[4/5] 投票率を取得中...", total=None)

            if not skip_scrape:
                scraper = VoteScraper()
                vote_rates = scraper.fetch(round_number)
            else:
                # キャッシュまたはモックを使用
                scraper = VoteScraper()
                cached = scraper.get_cached(round_number)
                if cached:
                    vote_rates = cached
                    console.print("  ✓ キャッシュから投票率を取得")
                else:
                    vote_rates = scraper.get_mock_data(round_number)
                    console.print("  ⚠ モックデータを使用")

            # 投票率を保存
            vote_path = Path(f"data/votes/round_{round_number}.json")
            vote_path.parent.mkdir(parents=True, exist_ok=True)
            with open(vote_path, "w") as f:
                json.dump([v.to_dict() for v in vote_rates], f, indent=2, ensure_ascii=False)

            console.print(f"  ✓ {len(vote_rates)}チームの投票率取得")
            progress.remove_task(task)

            # 5. 戦略計算・レポート生成
            task = progress.add_task(description="[5/5] 戦略を計算中...", total=None)
            engine = StrategyEngine()
            recommendations = engine.calculate_value_scores(predictions, vote_rates)
            report_path = engine.generate_report(recommendations)

            console.print(f"  ✓ {len(recommendations)}件の推奨を生成")
            progress.remove_task(task)

        # 結果サマリー
        buy_count = sum(1 for r in recommendations if r.value_score >= 1.3)
        consider_count = sum(1 for r in recommendations if 1.0 <= r.value_score < 1.3)

        console.print(
            Panel(
                f"[green]パイプライン完了[/green]\n\n"
                f"予測チーム数: {len(predictions)}\n"
                f"推奨購入: {buy_count}件\n"
                f"検討候補: {consider_count}件\n\n"
                f"レポート: {report_path}",
                title="結果サマリー",
                border_style="green",
            )
        )

    except TotoPredictorError as e:
        console.print(
            Panel(
                f"[red]エラー[/red]: {e.message}",
                title="パイプラインエラー",
                border_style="red",
            )
        )
        raise typer.Exit(1) from None
