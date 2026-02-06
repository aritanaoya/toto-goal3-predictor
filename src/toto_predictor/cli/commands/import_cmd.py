"""importコマンド

Wyscout Excelファイルをデータベースにインポートします。
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...models.exceptions import DataFormatError, DataNotFoundError, TotoPredictorError
from ...services.data_loader import DataLoader

app = typer.Typer()
console = Console()

DEFAULT_DB_PATH = "data/processed/toto_predictor.db"


@app.callback(invoke_without_command=True)
def import_data(
    directory: str = typer.Option(
        "data/wyscout/2025",
        "--dir",
        "-d",
        help="Wyscout Excelファイルが格納されたディレクトリ",
    ),
    season: int = typer.Option(
        2025,
        "--season",
        "-s",
        help="シーズン年（例: 2024, 2025）",
    ),
    db_path: str = typer.Option(
        DEFAULT_DB_PATH,
        "--db",
        help="データベースファイルのパス",
    ),
) -> None:
    """Wyscout Excelファイルをデータベースにインポート

    指定ディレクトリ内のExcelファイル（Team Stats *.xlsx）を読み込み、
    SQLiteデータベースに保存します。
    """
    console.print(f"\n[bold]データインポート[/bold] - シーズン {season}")
    console.print(f"ディレクトリ: {directory}")
    console.print(f"データベース: {db_path}\n")

    try:
        loader = DataLoader(db_path)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(description="インポート中...", total=None)
            count = loader.load_directory(directory, season)

        # 結果表示
        console.print(
            Panel(
                f"[green]インポート完了[/green]\n\n"
                f"追加試合数: {count}件\n"
                f"登録チーム: {len(loader.get_teams())}チーム",
                title="結果",
                border_style="green",
            )
        )

        # チーム一覧
        teams = loader.get_teams()
        if teams:
            console.print("\n[bold]登録チーム一覧:[/bold]")
            for team in teams:
                console.print(f"  - {team}")

    except DataNotFoundError as e:
        console.print(
            Panel(
                f"[red]エラー[/red]: {e.message}",
                title="データが見つかりません",
                border_style="red",
            )
        )
        raise typer.Exit(1) from None

    except DataFormatError as e:
        console.print(
            Panel(
                f"[red]エラー[/red]: {e.message}",
                title="データ形式エラー",
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
