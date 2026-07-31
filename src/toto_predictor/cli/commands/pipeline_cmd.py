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
from ...models.match_schedule import MatchSchedule
from ...services.data_loader import DataLoader
from ...services.feature_engine import FeatureEngine
from ...services.model_ensemble import ModelEnsemble
from ...services.strategy_engine import StrategyEngine
from ...services.vote_scraper import VoteScraper
from .strategy_cmd import _display_marksheet

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
    matches: str = typer.Option(
        "",
        "--matches",
        help="対戦カード（例: 'チームA:チームB,チームC:チームD'）。指定時は対戦相手考慮の予測",
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
                task = progress.add_task(description="[1/6] データをインポート中...", total=None)
                loader = DataLoader(db_path)
                try:
                    count = loader.load_directory(data_dir, season)
                    console.print(f"  ✓ {count}件の試合データをインポート")
                except Exception as e:
                    console.print(f"  [yellow]⚠ インポートをスキップ: {e}[/yellow]")
                progress.remove_task(task)

            # 2. モデル学習（または読み込み）
            task = progress.add_task(description="[2/6] モデルを準備中...", total=None)
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
            task = progress.add_task(description="[3/6] 予測を実行中...", total=None)
            feature_engine = FeatureEngine(db_path)
            scraper = VoteScraper()

            # スケジュール解決
            schedule: MatchSchedule | None = None
            if matches:
                schedule = MatchSchedule.from_matches_str(matches, round_number)
            else:
                # --matches未指定時はtotoONEから自動取得を試行
                try:
                    schedule = scraper.fetch_schedule(round_number)
                    if schedule and schedule.matches:
                        console.print(f"  ✓ 対戦カードを自動取得（{len(schedule.matches)}試合）")
                except Exception:
                    pass

            predictions = []
            if schedule and schedule.matches:
                # 対戦カードモード
                for match_pair in schedule.matches:
                    for team, opponent, is_home in [
                        (match_pair.home_team, match_pair.away_team, True),
                        (match_pair.away_team, match_pair.home_team, False),
                    ]:
                        try:
                            matchup = feature_engine.calculate_matchup_features(
                                team, opponent, is_home=is_home, as_of_date=datetime.now()
                            )
                            pred = model.predict(matchup, round_number)
                            predictions.append(pred)
                        except Exception:
                            pass
            else:
                # 従来モード（対戦カードなし）
                loader = DataLoader(db_path)
                teams = loader.get_teams()
                for team in teams:
                    try:
                        features = feature_engine.calculate_features(
                            team, datetime.now(), [5, 10, 20]
                        )
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
            task = progress.add_task(description="[4/6] 投票率を取得中...", total=None)

            if not skip_scrape:
                vote_rates = scraper.fetch(round_number)
            else:
                # キャッシュまたはモックを使用
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

            # 5. 従来戦略計算
            task = progress.add_task(description="[5/6] バリュースコアを計算中...", total=None)
            engine = StrategyEngine()
            recommendations = engine.calculate_value_scores(predictions, vote_rates)
            report_path = engine.generate_report(recommendations)

            console.print(f"  ✓ {len(recommendations)}件の推奨を生成")
            progress.remove_task(task)

            # 6. チケット戦略・拡張レポート生成
            task = progress.add_task(description="[6/6] チケット戦略を生成中...", total=None)
            ev_recs = engine.calculate_ev_scores(predictions, vote_rates)
            ticket_recs = engine.generate_tickets(predictions, vote_rates, schedule=schedule)
            enhanced_report_path = engine.generate_enhanced_report(ev_recs, ticket_recs)

            # マークシートレポート生成
            marksheet_path = ""
            if schedule and ticket_recs:
                marksheet_path = engine.generate_marksheet_report(
                    ticket_recs, round_number=round_number
                )

            console.print(f"  ✓ {len(ticket_recs)}枚のチケット推奨を生成")
            progress.remove_task(task)

        # マークシート風表示（scheduleがある場合）
        if schedule and ticket_recs:
            _display_marksheet(ticket_recs, round_number)

        # 結果サマリー
        buy_count = sum(1 for r in recommendations if r.value_score >= 1.3)
        consider_count = sum(1 for r in recommendations if 1.0 <= r.value_score < 1.3)

        report_info = f"レポート: {report_path}"
        if enhanced_report_path:
            report_info += f"\n拡張レポート: {enhanced_report_path}"
        if marksheet_path:
            report_info += f"\nマークシート: {marksheet_path}"

        console.print(
            Panel(
                f"[green]パイプライン完了[/green]\n\n"
                f"予測チーム数: {len(predictions)}\n"
                f"推奨購入: {buy_count}件\n"
                f"検討候補: {consider_count}件\n"
                f"チケット推奨: {len(ticket_recs)}枚\n\n"
                f"{report_info}",
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
