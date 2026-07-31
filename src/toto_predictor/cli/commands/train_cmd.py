"""trainコマンド

予測モデルを学習します。
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...models.exceptions import DataNotFoundError, ModelError, TotoPredictorError
from ...services.feature_engine import FeatureEngine
from ...services.model_ensemble import ModelEnsemble

app = typer.Typer()
console = Console()

DEFAULT_DB_PATH = "data/processed/toto_predictor.db"
DEFAULT_MODEL_DIR = "models"


@app.callback(invoke_without_command=True)
def train_model(
    seasons: str = typer.Option(
        "2025",
        "--seasons",
        "-s",
        help="学習に使用するシーズン（カンマ区切り、例: 2024,2025）",
    ),
    cv_folds: int = typer.Option(
        5,
        "--cv",
        "-c",
        help="クロスバリデーションのフォールド数",
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
        help="モデル保存ディレクトリ",
    ),
) -> None:
    """予測モデルを学習

    指定シーズンのデータを使用して、Poisson Regression + XGBoost の
    アンサンブルモデルを学習します。
    """
    # シーズンリストの解析
    season_list = [int(s.strip()) for s in seasons.split(",")]

    console.print("\n[bold]モデル学習[/bold]")
    console.print(f"対象シーズン: {season_list}")
    console.print(f"CVフォールド数: {cv_folds}")
    console.print(f"モデル保存先: {model_dir}\n")

    try:
        # 特徴量エンジンとモデルの初期化
        feature_engine = FeatureEngine(db_path)
        model = ModelEnsemble(model_dir)

        # 学習データの準備
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(description="学習データを準備中...", total=None)
            x_train, y_train = feature_engine.prepare_training_data(season_list)

            progress.update(task, description="モデルを学習中...")
            metrics = model.train(x_train, y_train, cv_folds=cv_folds)

            progress.update(task, description="モデルを保存中...")
            model.save()

        # 結果表示
        brier_status = "✓" if metrics["brier_score"] < 0.20 else "✗"
        accuracy_status = "✓" if metrics["accuracy"] > 0.40 else "✗"

        console.print(
            Panel(
                f"[green]学習完了[/green]\n\n"
                f"サンプル数: {metrics['n_samples']}\n"
                f"CVフォールド: {metrics['cv_folds']}\n\n"
                f"[bold]評価指標:[/bold]\n"
                f"  Brier Score: {metrics['brier_score']:.4f} (±{metrics['brier_score_std']:.4f}) {brier_status} (目標: < 0.20)\n"
                f"  的中率: {metrics['accuracy'] * 100:.1f}% (±{metrics['accuracy_std'] * 100:.1f}%) {accuracy_status} (目標: > 40%)\n\n"
                f"モデル保存先: {model_dir}/",
                title="学習結果",
                border_style="green",
            )
        )

    except DataNotFoundError as e:
        console.print(
            Panel(
                f"[red]エラー[/red]: {e.message}\n\n"
                "[yellow]ヒント[/yellow]: 先に 'toto-predictor import' でデータをインポートしてください",
                title="データが見つかりません",
                border_style="red",
            )
        )
        raise typer.Exit(1) from None

    except ModelError as e:
        console.print(
            Panel(
                f"[red]エラー[/red]: {e.message}",
                title="モデルエラー",
                border_style="red",
            )
        )
        raise typer.Exit(1) from None

    except TotoPredictorError as e:
        console.print(
            Panel(
                f"[red]エラー[/red]: {e.message}",
                title="処理エラー",
                border_style="red",
            )
        )
        raise typer.Exit(1) from None
