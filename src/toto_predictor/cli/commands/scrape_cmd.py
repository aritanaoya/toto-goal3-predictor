"""scrapeコマンド

totoONEから投票率を取得します。
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ...models.exceptions import ScrapingError, TotoPredictorError
from ...services.vote_scraper import VoteScraper

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def scrape(
    round_number: int = typer.Option(
        0,
        "--round",
        "-r",
        help="toto回号（0の場合は最新回）",
    ),
    use_cache: bool = typer.Option(
        False,
        "--cache",
        "-c",
        help="キャッシュを使用する",
    ),
    cache_dir: str = typer.Option(
        "data/votes",
        "--cache-dir",
        help="キャッシュディレクトリ",
    ),
) -> None:
    """totoONEから投票率を取得

    GOAL3の投票率データをスクレイピングして表示します。
    """
    console.print("\n[bold]投票率取得[/bold]")
    if round_number > 0:
        console.print(f"回号: 第{round_number}回")
    else:
        console.print("回号: 最新")

    try:
        scraper = VoteScraper(cache_dir=cache_dir)

        # キャッシュチェック
        if use_cache and round_number > 0:
            cached = scraper.get_cached(round_number)
            if cached:
                console.print("[dim]キャッシュを使用しています[/dim]\n")
                _display_vote_rates(cached)
                return

        # スクレイピング実行
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(description="投票率を取得中...", total=None)
            vote_rates = scraper.fetch(round_number if round_number > 0 else None)

        _display_vote_rates(vote_rates)

    except ScrapingError as e:
        console.print(
            Panel(
                f"[red]エラー[/red]: {e.message}\n\n"
                "[yellow]ヒント[/yellow]: ネットワーク接続を確認し、しばらく待ってから再試行してください",
                title="スクレイピングエラー",
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


def _display_vote_rates(vote_rates: list) -> None:
    """投票率を表示"""
    if not vote_rates:
        console.print("[yellow]投票率データがありません[/yellow]")
        return

    round_number = vote_rates[0].round_number
    console.print(f"\n[bold]第{round_number}回 GOAL3 投票率[/bold]\n")

    for vr in vote_rates:
        table = Table(title=vr.team)
        table.add_column("カテゴリ", style="cyan")
        table.add_column("投票率", justify="right")
        table.add_column("分布バー", justify="left")

        for cat, rate in vr.get_all_rates().items():
            bar = "█" * int(rate * 20) + "░" * (20 - int(rate * 20))
            table.add_row(f"{cat}点", f"{rate * 100:.1f}%", bar)

        console.print(table)
        console.print(
            f"最多投票: [bold]{vr.get_most_voted_category()}点[/bold] "
            f"({vr.get_rate_for_category(vr.get_most_voted_category()) * 100:.1f}%)\n"
        )

    console.print(f"[dim]取得日時: {vote_rates[0].fetched_at.strftime('%Y-%m-%d %H:%M')}[/dim]")
