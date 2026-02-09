"""predictコマンド

得点分布を予測します。
"""

import json
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ...models.exceptions import DataNotFoundError, ModelNotTrainedError, TotoPredictorError
from ...services.feature_engine import FeatureEngine
from ...services.model_ensemble import ModelEnsemble

app = typer.Typer()
console = Console()

DEFAULT_DB_PATH = "data/processed/toto_predictor.db"
DEFAULT_MODEL_DIR = "models"


@app.callback(invoke_without_command=True)
def predict(
    round_number: int = typer.Option(
        0,
        "--round",
        "-r",
        help="toto回号",
    ),
    teams: str = typer.Option(
        "",
        "--teams",
        "-t",
        help="予測対象チーム（カンマ区切り）。空の場合は全チーム",
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
    matches: str = typer.Option(
        "",
        "--matches",
        help="対戦カード（例: 'チームA:チームB,チームC:チームD'）。指定時は対戦相手考慮の予測",
    ),
    output: str = typer.Option(
        "",
        "--output",
        "-o",
        help="予測結果の保存先（JSON）",
    ),
) -> None:
    """得点分布を予測

    学習済みモデルを使用して、各チームの得点確率分布を予測します。
    """
    console.print("\n[bold]得点分布予測[/bold]")
    if round_number > 0:
        console.print(f"回号: 第{round_number}回")

    try:
        # モデルとエンジンの初期化
        model = ModelEnsemble(model_dir)
        model.load()

        feature_engine = FeatureEngine(db_path)

        # 対戦カードモードか判定
        use_matchup = bool(matches)

        if use_matchup:
            # 対戦カードから予測対象を構築
            match_pairs = []
            for pair in matches.split(","):
                pair = pair.strip()
                if ":" not in pair:
                    console.print(
                        f"[yellow]無効な対戦カード形式: {pair} ('チームA:チームB'の形式で指定)[/yellow]"
                    )
                    continue
                home, away = pair.split(":", 1)
                match_pairs.append((home.strip(), away.strip()))

            if not match_pairs:
                console.print("[yellow]有効な対戦カードがありません[/yellow]")
                raise typer.Exit(1)

            console.print(f"対戦カード: {len(match_pairs)}試合（対戦相手考慮モード）\n")

            predictions = []
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(description="予測中...", total=len(match_pairs) * 2)

                for home, away in match_pairs:
                    # ホームチーム予測
                    progress.update(task, description=f"予測中: {home} (vs {away})")
                    try:
                        matchup = feature_engine.calculate_matchup_features(
                            home, away, is_home=True, as_of_date=datetime.now()
                        )
                        pred = model.predict(matchup, round_number)
                        predictions.append(pred)
                    except DataNotFoundError:
                        console.print(f"[yellow]スキップ: {home} (データ不足)[/yellow]")
                    progress.advance(task)

                    # アウェイチーム予測
                    progress.update(task, description=f"予測中: {away} (vs {home})")
                    try:
                        matchup = feature_engine.calculate_matchup_features(
                            away, home, is_home=False, as_of_date=datetime.now()
                        )
                        pred = model.predict(matchup, round_number)
                        predictions.append(pred)
                    except DataNotFoundError:
                        console.print(f"[yellow]スキップ: {away} (データ不足)[/yellow]")
                    progress.advance(task)
        else:
            # 従来モード：チーム単体の特徴量で予測
            if teams:
                team_list = [t.strip() for t in teams.split(",")]
            else:
                # DBから全チームを取得
                from ...services.data_loader import DataLoader

                loader = DataLoader(db_path)
                team_list = loader.get_teams()

            if not team_list:
                console.print("[yellow]予測対象チームがありません[/yellow]")
                raise typer.Exit(1)

            console.print(f"対象チーム: {len(team_list)}チーム\n")

            predictions = []
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(description="予測中...", total=len(team_list))

                for team in team_list:
                    progress.update(task, description=f"予測中: {team}")
                    try:
                        features = feature_engine.calculate_features(
                            team, datetime.now(), window_sizes=[5, 10, 20]
                        )
                        pred = model.predict(features, round_number)
                        predictions.append(pred)
                    except DataNotFoundError:
                        console.print(f"[yellow]スキップ: {team} (データ不足)[/yellow]")
                    progress.advance(task)

        # 結果表示
        console.print(f"\n[bold]第{round_number}回 GOAL3 予測結果[/bold]\n")

        for pred in predictions:
            table = Table(title=pred.team)
            table.add_column("カテゴリ", style="cyan")
            table.add_column("予測確率", justify="right")
            table.add_column("信頼度バー", justify="left")

            for cat, prob in pred.get_all_probs().items():
                bar = "█" * int(prob * 20) + "░" * (20 - int(prob * 20))
                table.add_row(f"{cat}点", f"{prob * 100:.1f}%", bar)

            console.print(table)
            console.print(
                f"最頻予測: [bold]{pred.get_most_likely_category()}点[/bold] "
                f"({pred.get_prob_for_category(pred.get_most_likely_category()) * 100:.1f}%)\n"
            )

        # JSON出力
        if output or round_number > 0:
            if not output:
                output = f"data/predictions/round_{round_number}.json"
            Path(output).parent.mkdir(parents=True, exist_ok=True)

            data = [p.to_dict() for p in predictions]
            with open(output, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            console.print(f"[dim]予測結果を保存しました: {output}[/dim]")

    except ModelNotTrainedError as e:
        console.print(
            Panel(
                f"[red]エラー[/red]: {e.message}\n\n"
                "[yellow]ヒント[/yellow]: 先に 'toto-predictor train' でモデルを学習してください",
                title="モデルが見つかりません",
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
