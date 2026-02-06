"""戦略エンジン

このモジュールは、バリュースコアの計算と購入推奨の生成を提供します。
"""

import logging
from datetime import datetime
from pathlib import Path

from ..models.prediction import Prediction
from ..models.recommendation import (
    ActionType,
    ConfidenceLevel,
    Recommendation,
    TotoCategory,
)
from ..models.vote_rate import VoteRate

logger = logging.getLogger(__name__)


class StrategyEngine:
    """戦略計算エンジン

    モデル予測と投票率を比較し、バリューベットを特定して購入推奨を生成します。

    Attributes:
        min_rate: バリュースコア計算時の最小投票率（ゼロ除算防止）
    """

    MIN_RATE = 0.01  # 最小投票率（1%）

    def __init__(self, reports_dir: str = "reports") -> None:
        """戦略エンジンを初期化

        Args:
            reports_dir: レポート出力ディレクトリ
        """
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def calculate_value_scores(
        self,
        predictions: list[Prediction],
        vote_rates: list[VoteRate],
    ) -> list[Recommendation]:
        """バリュースコアを計算し、購入推奨を生成

        Args:
            predictions: Predictionオブジェクトのリスト
            vote_rates: VoteRateオブジェクトのリスト

        Returns:
            Recommendationオブジェクトのリスト
        """
        # チーム名でマッピング
        vote_map = {vr.team: vr for vr in vote_rates}

        recommendations = []
        for pred in predictions:
            vr = vote_map.get(pred.team)
            if vr is None:
                logger.warning(f"投票率が見つかりません: {pred.team}")
                continue

            # 各カテゴリについてバリュースコアを計算
            for cat in ("0", "1", "2", "3+"):
                category: TotoCategory = cat  # type: ignore[assignment]
                model_prob = pred.get_prob_for_category(category)
                vote_rate = vr.get_rate_for_category(category)

                # バリュースコア計算
                value_score = self._calculate_value_score(model_prob, vote_rate)

                # アクション決定
                action = self._determine_action(model_prob, value_score)

                # ケリー基準
                kelly = self._calculate_kelly(model_prob, vote_rate)

                # 信頼度
                confidence = self._determine_confidence(model_prob, value_score)

                recommendations.append(
                    Recommendation(
                        round_number=pred.round_number,
                        team=pred.team,
                        category=category,
                        model_prob=model_prob,
                        vote_rate=vote_rate,
                        value_score=value_score,
                        action=action,
                        kelly_fraction=kelly,
                        confidence=confidence,
                    )
                )

        # バリュースコア降順でソート
        recommendations.sort(key=lambda r: r.value_score, reverse=True)

        logger.info(f"{len(recommendations)}件の推奨を生成しました")
        return recommendations

    def generate_report(
        self,
        recommendations: list[Recommendation],
        output_path: str | None = None,
    ) -> str:
        """Markdownレポートを生成

        Args:
            recommendations: Recommendationオブジェクトのリスト
            output_path: 出力ファイルパス（Noneの場合は自動生成）

        Returns:
            生成したレポートのパス
        """
        if not recommendations:
            logger.warning("推奨がありません")
            return ""

        round_number = recommendations[0].round_number

        # レポート内容の生成
        lines = [
            f"# 第{round_number}回 GOAL3 購入戦略レポート",
            "",
            f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            "",
        ]

        # 推奨購入（バリュースコア1.3以上）
        buy_recommendations = [r for r in recommendations if r.value_score >= 1.3]
        if buy_recommendations:
            lines.extend(
                [
                    "## ★ 推奨購入（バリュースコア 1.3以上）",
                    "",
                    "| チーム | カテゴリ | モデル予測 | 投票率 | バリュー | アクション |",
                    "|--------|----------|-----------|--------|---------|----------|",
                ]
            )
            for r in buy_recommendations:
                lines.append(
                    f"| {r.team} | {r.category}点 | {r.model_prob * 100:.1f}% | "
                    f"{r.vote_rate * 100:.1f}% | {r.value_score:.2f} | {r.action} |"
                )
            lines.append("")

        # 検討候補（バリュースコア1.0-1.3）
        consider_recommendations = [r for r in recommendations if 1.0 <= r.value_score < 1.3]
        if consider_recommendations:
            lines.extend(
                [
                    "## 検討候補（バリュースコア 1.0-1.3）",
                    "",
                    "| チーム | カテゴリ | モデル予測 | 投票率 | バリュー | アクション |",
                    "|--------|----------|-----------|--------|---------|----------|",
                ]
            )
            for r in consider_recommendations:
                lines.append(
                    f"| {r.team} | {r.category}点 | {r.model_prob * 100:.1f}% | "
                    f"{r.vote_rate * 100:.1f}% | {r.value_score:.2f} | {r.action} |"
                )
            lines.append("")

        # スキップ推奨（バリュースコア1.0未満）
        skip_recommendations = [r for r in recommendations if r.value_score < 1.0]
        if skip_recommendations:
            lines.extend(
                [
                    "## スキップ推奨（バリュースコア 1.0未満）",
                    "",
                ]
            )
            skip_summary = []
            for r in skip_recommendations[:10]:  # 上位10件のみ表示
                skip_summary.append(f"- {r.team}: {r.category}点 (バリュー {r.value_score:.2f})")
            lines.extend(skip_summary)
            if len(skip_recommendations) > 10:
                lines.append(f"- ... 他 {len(skip_recommendations) - 10}件")
            lines.append("")

        # チーム別サマリー
        lines.extend(
            [
                "---",
                "",
                "## チーム別予測サマリー",
                "",
            ]
        )

        # チームごとにグループ化
        teams: dict[str, list[Recommendation]] = {}
        for r in recommendations:
            if r.team not in teams:
                teams[r.team] = []
            teams[r.team].append(r)

        for team, recs in teams.items():
            lines.append(f"### {team}")
            lines.append("")
            lines.append("| カテゴリ | モデル予測 | 投票率 | バリュー |")
            lines.append("|----------|-----------|--------|---------|")
            for r in sorted(recs, key=lambda x: x.category):
                value_marker = " ★" if r.value_score >= 1.3 else ""
                lines.append(
                    f"| {r.category}点 | {r.model_prob * 100:.1f}% | "
                    f"{r.vote_rate * 100:.1f}% | {r.value_score:.2f}{value_marker} |"
                )
            lines.append("")

        # 免責事項
        lines.extend(
            [
                "---",
                "",
                "## 免責事項",
                "",
                "このレポートは機械学習モデルによる予測に基づいており、",
                "購入の最終判断は自己責任で行ってください。",
                "過去のパフォーマンスは将来の結果を保証するものではありません。",
                "",
                "---",
                "",
                "*Generated by toto-predictor*",
            ]
        )

        # ファイル出力
        if output_path is None:
            output_path = str(self.reports_dir / f"round_{round_number}_strategy.md")

        content = "\n".join(lines)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"レポートを生成しました: {output_path}")
        return output_path

    def _calculate_value_score(self, model_prob: float, vote_rate: float) -> float:
        """バリュースコアを計算

        Args:
            model_prob: モデル予測確率
            vote_rate: 公衆投票率

        Returns:
            バリュースコア（model_prob / vote_rate）
        """
        return model_prob / max(vote_rate, self.MIN_RATE)

    def _determine_action(self, model_prob: float, value_score: float) -> ActionType:
        """購入アクションを決定

        購入判断マトリクス:
        - 高確率 (>=30%) + 高バリュー (>=1.5) → 必買
        - 高確率 (>=30%) + 中バリュー (>=1.0) → 買い
        - 高確率 (>=30%) + 低バリュー (<1.0) → 慎重
        - 中確率 (>=15%) + 高バリュー (>=1.5) → 買い
        - 中確率 (>=15%) + 中バリュー (>=1.0) → 検討
        - 中確率 (>=15%) + 低バリュー (<1.0) → スキップ
        - 低確率 (<15%) + 高バリュー (>=1.5) → 検討
        - 低確率 (<15%) + 中低バリュー (<1.5) → スキップ

        Args:
            model_prob: モデル予測確率
            value_score: バリュースコア

        Returns:
            アクション文字列
        """
        if model_prob >= 0.30:
            if value_score >= 1.5:
                return "必買"
            elif value_score >= 1.0:
                return "買い"
            else:
                return "慎重"
        elif model_prob >= 0.15:
            if value_score >= 1.5:
                return "買い"
            elif value_score >= 1.0:
                return "検討"
            else:
                return "スキップ"
        else:
            if value_score >= 1.5:
                return "検討"
            else:
                return "スキップ"

    def _calculate_kelly(
        self,
        model_prob: float,
        vote_rate: float,
        kelly_fraction: float = 0.25,
    ) -> float:
        """ケリー基準でベットサイズを計算

        Args:
            model_prob: モデル予測確率
            vote_rate: 公衆投票率
            kelly_fraction: フルケリーの何倍を使うか（デフォルト: 1/4）

        Returns:
            推奨ベット比率（0-0.1）
        """
        if vote_rate <= 0:
            return 0.0

        # 簡易オッズ推定（パリミュチュエル方式）
        estimated_odds = 1.0 / vote_rate

        # エッジ（期待値）
        edge = model_prob * estimated_odds - 1

        if edge <= 0:
            return 0.0

        # フルケリー
        full_kelly = edge / (estimated_odds - 1) if estimated_odds > 1 else 0

        # 分数ケリー（リスク軽減）
        return min(full_kelly * kelly_fraction, 0.1)

    def _determine_confidence(self, model_prob: float, value_score: float) -> ConfidenceLevel:
        """信頼度を決定

        Args:
            model_prob: モデル予測確率
            value_score: バリュースコア

        Returns:
            信頼度（"high", "medium", "low"）
        """
        if model_prob >= 0.30 and value_score >= 1.3:
            return "high"
        elif model_prob >= 0.20 and value_score >= 1.0:
            return "medium"
        else:
            return "low"
