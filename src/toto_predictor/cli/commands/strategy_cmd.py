"""strategyコマンド

購入戦略を計算します。
"""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ...models.exceptions import TotoPredictorError
from ...models.prediction import Prediction
from ...models.vote_rate import VoteRate
from ...services.strategy_engine import StrategyEngine

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def strategy(
    round_number: int = typer.Option(
        0,
        "--round",
        "-r",
        help="toto回号",
    ),
    predictions_file: str = typer.Option(
        "",
        "--predictions",
        "-p",
        help="予測結果JSONファイル（空の場合は自動検索）",
    ),
    votes_file: str = typer.Option(
        "",
        "--votes",
        "-v",
        help="投票率JSONファイル（空の場合は自動検索）",
    ),
    output: str = typer.Option(
        "",
        "--output",
        "-o",
        help="レポート出力先（空の場合は自動生成）",
    ),
) -> None:
    """購入戦略を計算

    モデル予測と投票率を比較し、バリューベットを特定して
    購入推奨レポートを生成します。
    """
    console.print("\n[bold]購入戦略計算[/bold]")
    if round_number > 0:
        console.print(f"回号: 第{round_number}回")

    try:
        # 予測結果の読み込み
        if not predictions_file and round_number > 0:
            predictions_file = f"data/predictions/round_{round_number}.json"

        if not predictions_file or not Path(predictions_file).exists():
            console.print(
                Panel(
                    "[yellow]予測結果ファイルが見つかりません[/yellow]\n\n"
                    "先に 'toto-predictor predict' を実行してください",
                    title="ファイルが見つかりません",
                    border_style="yellow",
                )
            )
            raise typer.Exit(1)

        with open(predictions_file) as f:
            pred_data = json.load(f)
        predictions = [Prediction.from_dict(d) for d in pred_data]

        # 投票率の読み込み
        if not votes_file and round_number > 0:
            votes_file = f"data/votes/round_{round_number}.json"

        if not votes_file or not Path(votes_file).exists():
            console.print(
                Panel(
                    "[yellow]投票率ファイルが見つかりません[/yellow]\n\n"
                    "先に 'toto-predictor scrape' を実行してください",
                    title="ファイルが見つかりません",
                    border_style="yellow",
                )
            )
            raise typer.Exit(1)

        with open(votes_file) as f:
            vote_data = json.load(f)
        vote_rates = [VoteRate.from_dict(d) for d in vote_data]

        # 戦略計算
        engine = StrategyEngine()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(description="バリュースコアを計算中...", total=None)
            recommendations = engine.calculate_value_scores(predictions, vote_rates)

        # 結果表示
        _display_recommendations(recommendations, round_number)

        # レポート生成
        if output:
            report_path = output
        else:
            report_path = engine.generate_report(recommendations)

        console.print(f"\n[dim]レポートを保存しました: {report_path}[/dim]")

    except TotoPredictorError as e:
        console.print(
            Panel(
                f"[red]エラー[/red]: {e.message}",
                title="処理エラー",
                border_style="red",
            )
        )
        raise typer.Exit(1) from None


def _display_recommendations(recommendations: list, round_number: int) -> None:
    """推奨を表示"""
    console.print(f"\n[bold]第{round_number}回 GOAL3 購入戦略[/bold]\n")

    # 推奨購入（バリュースコア1.3以上）
    buy_recs = [r for r in recommendations if r.value_score >= 1.3]
    if buy_recs:
        console.print("[bold green]★ 推奨購入（バリュースコア 1.3以上）[/bold green]\n")

        table = Table()
        table.add_column("チーム", style="cyan")
        table.add_column("カテゴリ", justify="center")
        table.add_column("モデル予測", justify="right")
        table.add_column("投票率", justify="right")
        table.add_column("バリュー", justify="right")
        table.add_column("アクション", justify="center")

        for r in buy_recs[:10]:
            table.add_row(
                r.team,
                f"{r.category}点",
                f"{r.model_prob * 100:.1f}%",
                f"{r.vote_rate * 100:.1f}%",
                f"{r.value_score:.2f}",
                f"[bold]{r.action}[/bold]",
            )

        console.print(table)
        console.print()

    # 検討候補（バリュースコア1.0-1.3）
    consider_recs = [r for r in recommendations if 1.0 <= r.value_score < 1.3]
    if consider_recs:
        console.print("[bold yellow]検討候補（バリュースコア 1.0-1.3）[/bold yellow]\n")

        table = Table()
        table.add_column("チーム", style="cyan")
        table.add_column("カテゴリ", justify="center")
        table.add_column("モデル予測", justify="right")
        table.add_column("投票率", justify="right")
        table.add_column("バリュー", justify="right")
        table.add_column("アクション", justify="center")

        for r in consider_recs[:10]:
            table.add_row(
                r.team,
                f"{r.category}点",
                f"{r.model_prob * 100:.1f}%",
                f"{r.vote_rate * 100:.1f}%",
                f"{r.value_score:.2f}",
                r.action,
            )

        console.print(table)
        console.print()

    # スキップ数
    skip_recs = [r for r in recommendations if r.value_score < 1.0]
    if skip_recs:
        console.print(f"[dim]スキップ推奨: {len(skip_recs)}件[/dim]")
