"""CLIエントリーポイント

このモジュールは、toto-predictor CLIのメインエントリーポイントを提供します。
"""

import logging
import sys

import typer
from rich.console import Console
from rich.panel import Panel

from .commands import (
    features_cmd,
    import_cmd,
    pipeline_cmd,
    predict_cmd,
    scrape_cmd,
    strategy_cmd,
    train_cmd,
)

# アプリケーション設定
app = typer.Typer(
    name="toto-predictor",
    help="toto GOAL3 購入戦略システム - 機械学習ベースの予測ツール",
    add_completion=False,
)

console = Console()

# サブコマンドの登録
app.add_typer(import_cmd.app, name="import", help="Wyscoutデータをインポート")
app.add_typer(train_cmd.app, name="train", help="予測モデルを学習")
app.add_typer(predict_cmd.app, name="predict", help="得点分布を予測")
app.add_typer(scrape_cmd.app, name="scrape", help="投票率を取得")
app.add_typer(strategy_cmd.app, name="strategy", help="購入戦略を計算")
app.add_typer(pipeline_cmd.app, name="pipeline", help="パイプライン全体を実行")
app.add_typer(features_cmd.app, name="features", help="チームの特徴量を表示")


def setup_logging(verbose: bool = False) -> None:
    """ロギングを設定

    Args:
        verbose: 詳細ログを出力するかどうか
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/toto-predictor.log", encoding="utf-8"),
        ],
    )


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="詳細ログを出力"),
) -> None:
    """toto GOAL3 Predictor - 機械学習ベースの購入戦略システム"""
    # ログディレクトリの作成
    import os

    os.makedirs("logs", exist_ok=True)
    setup_logging(verbose)


@app.command()
def version() -> None:
    """バージョン情報を表示"""
    console.print(
        Panel(
            "[bold]toto-predictor[/bold] v0.1.0\n\n機械学習ベースのtoto GOAL3購入戦略システム",
            title="Version Info",
            border_style="blue",
        )
    )


@app.command()
def info() -> None:
    """システム情報を表示"""
    import platform

    import numpy
    import pandas
    import sklearn
    import xgboost

    console.print(
        Panel(
            f"[bold]システム情報[/bold]\n\n"
            f"Python: {platform.python_version()}\n"
            f"OS: {platform.system()} {platform.release()}\n\n"
            f"[bold]ライブラリバージョン[/bold]\n\n"
            f"pandas: {pandas.__version__}\n"
            f"numpy: {numpy.__version__}\n"
            f"scikit-learn: {sklearn.__version__}\n"
            f"xgboost: {xgboost.__version__}",
            title="System Info",
            border_style="green",
        )
    )


if __name__ == "__main__":
    app()
