"""featuresコマンド

チームの特徴量を表示します。
"""

from datetime import datetime

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...models.exceptions import DataNotFoundError, TotoPredictorError
from ...services.feature_engine import FeatureEngine

app = typer.Typer()
console = Console()

DEFAULT_DB_PATH = "data/processed/toto_predictor.db"


@app.callback(invoke_without_command=True)
def features(
    team: str = typer.Option(
        ...,
        "--team",
        "-t",
        help="対象チーム名",
    ),
    window: int = typer.Option(
        10,
        "--window",
        "-w",
        help="特徴量計算に使用する試合数",
    ),
    db_path: str = typer.Option(
        DEFAULT_DB_PATH,
        "--db",
        help="データベースファイルのパス",
    ),
    compare: str = typer.Option(
        "",
        "--compare",
        "-c",
        help="比較対象チーム名（オプション）",
    ),
) -> None:
    """チームの特徴量を表示

    デバッグや分析用に、指定チームの特徴量を確認できます。

    例:
        toto-predictor features --team "Yokohama F. Marinos" --window 10
    """
    console.print(f"\n[bold]チーム特徴量: {team}[/bold]")
    console.print(f"ウィンドウサイズ: {window}試合\n")

    try:
        engine = FeatureEngine(db_path)

        # 特徴量を計算
        feat = engine.calculate_features(
            team,
            as_of_date=datetime.now(),
            window_sizes=[5, window, 20],
        )

        # 攻撃系特徴量テーブル
        attack_table = Table(title="攻撃系特徴量", show_header=True)
        attack_table.add_column("項目", style="cyan")
        attack_table.add_column("値", justify="right")
        attack_table.add_column("説明", style="dim")

        attack_table.add_row("得点平均", f"{feat.goals_mean:.2f}", "goals_mean")
        attack_table.add_row("得点標準偏差", f"{feat.goals_std:.2f}", "goals_std")
        attack_table.add_row("xG平均", f"{feat.xg_mean:.2f}", "xg_mean")
        attack_table.add_row("xG標準偏差", f"{feat.xg_std:.2f}", "xg_std")
        attack_table.add_row("シュート平均", f"{feat.shots_mean:.2f}", "shots_mean")
        attack_table.add_row(
            "枠内シュート平均", f"{feat.shots_on_target_mean:.2f}", "shots_on_target_mean"
        )
        attack_table.add_row("シュート決定率", f"{feat.shot_conversion:.1%}", "shot_conversion")
        attack_table.add_row("xG超過", f"{feat.xg_overperformance:+.2f}", "xg_overperformance")

        console.print(attack_table)

        # 守備系特徴量テーブル
        defense_table = Table(title="守備系特徴量", show_header=True)
        defense_table.add_column("項目", style="cyan")
        defense_table.add_column("値", justify="right")
        defense_table.add_column("説明", style="dim")

        defense_table.add_row("失点平均", f"{feat.conceded_mean:.2f}", "conceded_mean")
        defense_table.add_row("失点標準偏差", f"{feat.conceded_std:.2f}", "conceded_std")
        defense_table.add_row("xGA平均", f"{feat.xg_against_mean:.2f}", "xg_against_mean")
        defense_table.add_row("PPDA平均", f"{feat.ppda_mean:.2f}", "ppda_mean")
        defense_table.add_row(
            "インターセプト平均", f"{feat.interceptions_mean:.2f}", "interceptions_mean"
        )

        console.print(defense_table)

        # その他特徴量テーブル
        other_table = Table(title="その他特徴量", show_header=True)
        other_table.add_column("項目", style="cyan")
        other_table.add_column("値", justify="right")
        other_table.add_column("説明", style="dim")

        other_table.add_row("ポゼッション平均", f"{feat.possession_mean:.1f}%", "possession_mean")
        other_table.add_row("パス平均", f"{feat.passes_mean:.1f}", "passes_mean")
        other_table.add_row("パス精度", f"{feat.pass_accuracy:.1f}%", "pass_accuracy")
        other_table.add_row("ファウル平均", f"{feat.fouls_mean:.2f}", "fouls_mean")
        other_table.add_row("イエロー平均", f"{feat.yellow_cards_mean:.2f}", "yellow_cards_mean")
        other_table.add_row("コーナー平均", f"{feat.corners_mean:.2f}", "corners_mean")

        console.print(other_table)

        # トレンド特徴量テーブル
        trend_table = Table(title="トレンド特徴量（短期 vs 長期）", show_header=True)
        trend_table.add_column("項目", style="cyan")
        trend_table.add_column("値", justify="right")
        trend_table.add_column("傾向", justify="center")

        xg_trend_icon = "↑" if feat.xg_trend > 0 else "↓" if feat.xg_trend < 0 else "→"
        goals_trend_icon = "↑" if feat.goals_trend > 0 else "↓" if feat.goals_trend < 0 else "→"

        trend_table.add_row("xGトレンド", f"{feat.xg_trend:+.2f}", xg_trend_icon)
        trend_table.add_row("得点トレンド", f"{feat.goals_trend:+.2f}", goals_trend_icon)
        trend_table.add_row("ホーム得点平均", f"{feat.home_goals_mean:.2f}", "home_goals_mean")
        trend_table.add_row("アウェイ得点平均", f"{feat.away_goals_mean:.2f}", "away_goals_mean")

        console.print(trend_table)

        # 比較対象がある場合
        if compare:
            console.print(f"\n[bold]対戦時特徴量: {team} vs {compare}[/bold]\n")

            try:
                opponent_features = engine.calculate_opponent_features(team, compare)

                vs_table = Table(title="対戦分析", show_header=True)
                vs_table.add_column("項目", style="cyan")
                vs_table.add_column("値", justify="right")

                vs_table.add_row("チーム得点平均", f"{opponent_features['team_goals_mean']:.2f}")
                vs_table.add_row("チームxG平均", f"{opponent_features['team_xg_mean']:.2f}")
                vs_table.add_row("チーム決定率", f"{opponent_features['team_shot_conversion']:.1%}")
                vs_table.add_row(
                    "相手失点平均", f"{opponent_features['opponent_conceded_mean']:.2f}"
                )
                vs_table.add_row(
                    "相手xGA平均", f"{opponent_features['opponent_xg_against_mean']:.2f}"
                )
                vs_table.add_row(
                    "攻撃力 vs 守備力", f"{opponent_features['attack_vs_defense']:+.2f}"
                )

                console.print(vs_table)

            except DataNotFoundError:
                console.print(f"[yellow]比較チーム '{compare}' のデータが不足しています[/yellow]")

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

    except TotoPredictorError as e:
        console.print(
            Panel(
                f"[red]エラー[/red]: {e.message}",
                title="処理エラー",
                border_style="red",
            )
        )
        raise typer.Exit(1) from None
