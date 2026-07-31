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
from ...models.team_names import get_japanese_name
from ...models.ticket import TicketRecommendation
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
    tickets: bool = typer.Option(
        False,
        "--tickets",
        help="チケット戦略モード（EV分析 + 本命/対抗/穴チケット推奨）",
    ),
    num_tickets: int = typer.Option(
        5,
        "--num-tickets",
        help="生成するチケット数（--ticketsモード時）",
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

        if tickets:
            # チケット戦略モード
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(description="EV分析を計算中...", total=None)
                recommendations = engine.calculate_ev_scores(predictions, vote_rates)
                ticket_recs = engine.generate_tickets(
                    predictions, vote_rates, num_tickets=num_tickets
                )

            # チケット表示
            _display_tickets(ticket_recs, round_number)

            # 拡張レポート生成
            report_path = engine.generate_enhanced_report(
                recommendations, ticket_recs, output_path=output or None
            )
        else:
            # 従来モード
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
            report_path = output if output else engine.generate_report(recommendations)

        if report_path:
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


def _display_tickets(ticket_recs: list[TicketRecommendation], round_number: int) -> None:
    """チケット推奨を表示"""
    console.print(f"\n[bold]第{round_number}回 GOAL3 チケット戦略[/bold]\n")

    if not ticket_recs:
        console.print("[yellow]チケット推奨がありません[/yellow]")
        return

    for ticket in ticket_recs:
        style = {"本命": "green", "対抗": "yellow", "穴": "red"}.get(ticket.ticket_type, "white")
        console.print(f"[bold {style}]【{ticket.ticket_type}チケット】[/bold {style}]")

        table = Table()
        table.add_column("チーム", style="cyan")
        table.add_column("選択", justify="center")
        table.add_column("モデル予測", justify="right")
        table.add_column("投票率", justify="right")
        table.add_column("逆張り", justify="center")

        for pick in ticket.picks:
            contrarian_mark = "[red]★[/red]" if pick.is_contrarian else ""
            table.add_row(
                pick.team,
                f"{pick.category}点",
                f"{pick.model_prob * 100:.1f}%",
                f"{pick.vote_rate * 100:.1f}%",
                contrarian_mark,
            )

        console.print(table)
        console.print(
            f"  的中確率: {ticket.ticket_prob * 100:.2f}% | "
            f"投票シェア: {ticket.ticket_vote_share * 100:.4f}% | "
            f"推定払戻: ¥{ticket.estimated_payout:,.0f} | "
            f"推定EV: {ticket.estimated_ev:.2f}"
        )
        console.print()


def _display_marksheet(ticket_recs: list[TicketRecommendation], round_number: int) -> None:
    """マークシート風にチケット推奨を表示"""
    console.print(f"\n[bold]第{round_number}回 GOAL3 マークシート[/bold]\n")

    if not ticket_recs:
        console.print("[yellow]チケット推奨がありません[/yellow]")
        return

    for ticket in ticket_recs:
        style = {"本命": "green", "対抗": "yellow", "穴": "red"}.get(ticket.ticket_type, "white")

        console.print(
            f"[bold {style}]━━━ {ticket.ticket_type}チケット（¥{ticket.cost}）━━━[/bold {style}]"
        )

        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        table.add_column("", min_width=14)
        table.add_column("0点", justify="right", min_width=8)
        table.add_column("1点", justify="right", min_width=8)
        table.add_column("2点", justify="right", min_width=8)
        table.add_column("3+点", justify="right", min_width=8)

        # match_indexでソートし試合単位でグループ化
        sorted_picks = sorted(ticket.picks, key=lambda p: (p.match_index, not p.is_home))
        current_match = 0
        for pick in sorted_picks:
            if pick.match_index > 0 and pick.match_index != current_match:
                current_match = pick.match_index
                table.add_row(f"[bold]第{current_match}試合[/bold]", "", "", "", "")

            jp_name = get_japanese_name(pick.team)
            ha_mark = "(H)" if pick.is_home else "(A)"
            display_name = f"  {jp_name}{ha_mark}"

            probs = pick.all_probs or {}
            cells = []
            for cat in ("0", "1", "2", "3+"):
                prob = probs.get(cat, 0.0)
                pct = f"{prob * 100:.0f}%"
                if cat == pick.category:
                    cells.append(f"[bold {style}]◉{pct}[/bold {style}]")
                else:
                    cells.append(f"[dim]{pct}[/dim]")

            table.add_row(display_name, *cells)

        console.print(table)
        console.print(
            f"[dim]━━━[/dim]\n"
            f"  的中確率: {ticket.ticket_prob:.2e} | "
            f"推定払戻: ¥{ticket.estimated_payout:,.0f} | "
            f"推定EV: ¥{ticket.estimated_ev:,.0f}"
        )
        console.print()
