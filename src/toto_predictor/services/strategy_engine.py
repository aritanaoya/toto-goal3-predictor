"""戦略エンジン

このモジュールは、バリュースコアの計算と購入推奨の生成を提供します。
"""

import logging
from datetime import datetime
from pathlib import Path

from ..models.match_schedule import MatchSchedule
from ..models.prediction import Prediction
from ..models.recommendation import (
    ActionType,
    ConfidenceLevel,
    Recommendation,
    TotoCategory,
)
from ..models.team_names import get_japanese_name
from ..models.ticket import PAYOUT_RATE, TeamPick, TicketRecommendation
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

    def calculate_ev_scores(
        self,
        predictions: list[Prediction],
        vote_rates: list[VoteRate],
    ) -> list[Recommendation]:
        """EV（期待値）ベースでバリュースコアを計算

        Args:
            predictions: Predictionオブジェクトのリスト
            vote_rates: VoteRateオブジェクトのリスト

        Returns:
            EV・逆張りスコア付きのRecommendationリスト
        """
        vote_map = {vr.team: vr for vr in vote_rates}
        recommendations = []

        for pred in predictions:
            vr = vote_map.get(pred.team)
            if vr is None:
                logger.warning(f"投票率が見つかりません: {pred.team}")
                continue

            team_recs: list[Recommendation] = []
            for cat in ("0", "1", "2", "3+"):
                category: TotoCategory = cat  # type: ignore[assignment]
                model_prob = pred.get_prob_for_category(category)
                vote_rate = vr.get_rate_for_category(category)
                safe_vote = max(vote_rate, self.MIN_RATE)

                # EV計算: model_prob × (PAYOUT_RATE / vote_rate) - 1
                ev = model_prob * (PAYOUT_RATE / safe_vote) - 1

                # 逆張りスコア: (model_prob - vote_rate) / vote_rate
                contrarian_score = (model_prob - vote_rate) / safe_vote

                value_score = self._calculate_value_score(model_prob, vote_rate)
                action = self._determine_action(model_prob, value_score)
                kelly = self._calculate_kelly(model_prob, vote_rate)
                confidence = self._determine_confidence(model_prob, value_score)

                rec = Recommendation(
                    round_number=pred.round_number,
                    team=pred.team,
                    category=category,
                    model_prob=model_prob,
                    vote_rate=vote_rate,
                    value_score=value_score,
                    action=action,
                    kelly_fraction=kelly,
                    confidence=confidence,
                    ev=ev,
                    contrarian_score=contrarian_score,
                )
                team_recs.append(rec)

            # 各チームの最高EVカテゴリを特定
            best_ev_rec = max(team_recs, key=lambda r: r.ev)
            best_ev_rec.is_best_ev_for_team = True

            recommendations.extend(team_recs)

        recommendations.sort(key=lambda r: r.ev, reverse=True)
        logger.info(f"EVベースで{len(recommendations)}件の推奨を生成しました")
        return recommendations

    def generate_tickets(
        self,
        predictions: list[Prediction],
        vote_rates: list[VoteRate],
        num_tickets: int = 5,
        schedule: MatchSchedule | None = None,
    ) -> list[TicketRecommendation]:
        """チケット推奨を生成

        Args:
            predictions: Predictionオブジェクトのリスト
            vote_rates: VoteRateオブジェクトのリスト
            num_tickets: 生成するチケット数（本命+対抗+穴の合計目安）
            schedule: 対戦カードスケジュール（match_index等をTeamPickに設定）

        Returns:
            TicketRecommendationのリスト
        """
        vote_map = {vr.team: vr for vr in vote_rates}
        pred_map = {p.team: p for p in predictions}
        tickets: list[TicketRecommendation] = []

        # 各チームのカテゴリ別分析を構築
        team_analysis: dict[str, dict[str, dict]] = {}
        for pred in predictions:
            vr = vote_map.get(pred.team)
            if vr is None:
                continue

            team_analysis[pred.team] = {}
            for cat in ("0", "1", "2", "3+"):
                model_prob = pred.get_prob_for_category(cat)
                vote_rate = vr.get_rate_for_category(cat)
                safe_vote = max(vote_rate, self.MIN_RATE)
                ev = model_prob * (PAYOUT_RATE / safe_vote) - 1
                contrarian_score = (model_prob - vote_rate) / safe_vote

                team_analysis[pred.team][cat] = {
                    "model_prob": model_prob,
                    "vote_rate": vote_rate,
                    "ev": ev,
                    "contrarian_score": contrarian_score,
                }

        if not team_analysis:
            return []

        teams = list(team_analysis.keys())

        def _enrich_pick(pick: TeamPick) -> TeamPick:
            """scheduleとprediction情報をTeamPickに付与"""
            if schedule:
                team_info = schedule.get_team_info(pick.team)
                if team_info:
                    pick.match_index = team_info[0]
                    pick.opponent = team_info[1]
                    pick.is_home = team_info[2]
            pred = pred_map.get(pick.team)
            if pred:
                pick.all_probs = pred.get_all_probs()
            return pick

        # 本命チケット: 各チーム最頻カテゴリ
        honmei_picks = []
        for team in teams:
            analysis = team_analysis[team]
            best_cat = max(analysis.keys(), key=lambda c: analysis[c]["model_prob"])
            info = analysis[best_cat]
            pick = TeamPick(
                team=team,
                category=best_cat,  # type: ignore[arg-type]
                model_prob=info["model_prob"],
                vote_rate=info["vote_rate"],
                ev_contribution=info["ev"],
            )
            honmei_picks.append(_enrich_pick(pick))
        tickets.append(TicketRecommendation(ticket_type="本命", picks=honmei_picks))

        # 対抗チケット: EV最大カテゴリが最頻と異なるチーム1-2を差替
        taikou_picks = list(honmei_picks)  # コピー
        ev_diff_teams = []
        for team in teams:
            analysis = team_analysis[team]
            best_prob_cat = max(analysis.keys(), key=lambda c: analysis[c]["model_prob"])
            best_ev_cat = max(analysis.keys(), key=lambda c: analysis[c]["ev"])
            if best_prob_cat != best_ev_cat:
                ev_diff_teams.append(
                    (team, best_ev_cat, analysis[best_ev_cat]["ev"] - analysis[best_prob_cat]["ev"])
                )

        ev_diff_teams.sort(key=lambda x: x[2], reverse=True)
        swap_count = min(2, len(ev_diff_teams))
        if swap_count > 0:
            taikou_picks = []
            swap_teams = {t[0]: t[1] for t in ev_diff_teams[:swap_count]}
            for pick in honmei_picks:
                if pick.team in swap_teams:
                    new_cat = swap_teams[pick.team]
                    info = team_analysis[pick.team][new_cat]
                    new_pick = TeamPick(
                        team=pick.team,
                        category=new_cat,  # type: ignore[arg-type]
                        model_prob=info["model_prob"],
                        vote_rate=info["vote_rate"],
                        ev_contribution=info["ev"],
                    )
                    taikou_picks.append(_enrich_pick(new_pick))
                else:
                    taikou_picks.append(pick)
            tickets.append(TicketRecommendation(ticket_type="対抗", picks=taikou_picks))

        # 穴チケット: contrarian_score上位3-4チームを逆張り
        contrarian_teams = []
        for team in teams:
            analysis = team_analysis[team]
            best_prob_cat = max(analysis.keys(), key=lambda c: analysis[c]["model_prob"])
            # 逆張り候補: 最頻以外でcontrarian_scoreが最も高いカテゴリ
            other_cats = [c for c in analysis.keys() if c != best_prob_cat]
            if other_cats:
                best_contrarian_cat = max(other_cats, key=lambda c: analysis[c]["contrarian_score"])
                contrarian_teams.append(
                    (team, best_contrarian_cat, analysis[best_contrarian_cat]["contrarian_score"])
                )

        contrarian_teams.sort(key=lambda x: x[2], reverse=True)
        ana_swap_count = min(4, len(contrarian_teams))
        if ana_swap_count > 0:
            ana_picks = []
            swap_teams_ana = {t[0]: t[1] for t in contrarian_teams[:ana_swap_count]}
            for pick in honmei_picks:
                if pick.team in swap_teams_ana:
                    new_cat = swap_teams_ana[pick.team]
                    info = team_analysis[pick.team][new_cat]
                    new_pick = TeamPick(
                        team=pick.team,
                        category=new_cat,  # type: ignore[arg-type]
                        model_prob=info["model_prob"],
                        vote_rate=info["vote_rate"],
                        ev_contribution=info["ev"],
                        is_contrarian=True,
                    )
                    ana_picks.append(_enrich_pick(new_pick))
                else:
                    ana_picks.append(pick)
            tickets.append(TicketRecommendation(ticket_type="穴", picks=ana_picks))

        logger.info(f"{len(tickets)}枚のチケット推奨を生成しました")
        return tickets

    def generate_enhanced_report(
        self,
        recommendations: list[Recommendation],
        tickets: list[TicketRecommendation],
        output_path: str | None = None,
    ) -> str:
        """拡張レポートを生成

        Args:
            recommendations: EV付きRecommendationリスト
            tickets: TicketRecommendationリスト
            output_path: 出力ファイルパス

        Returns:
            生成したレポートのパス
        """
        if not recommendations:
            logger.warning("推奨がありません")
            return ""

        round_number = recommendations[0].round_number

        lines = [
            f"# 第{round_number}回 GOAL3 拡張購入戦略レポート",
            "",
            f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            "",
        ]

        # 推奨チケット表
        if tickets:
            lines.extend(["## 推奨チケット", ""])
            for ticket in tickets:
                lines.extend(
                    [
                        f"### {ticket.ticket_type}チケット",
                        "",
                        f"- 的中確率: {ticket.ticket_prob:.2e}",
                        f"- 推定払戻: ¥{ticket.estimated_payout:,.0f}",
                        f"- 推定EV: ¥{ticket.estimated_ev:,.0f}",
                        f"- 逆張り数: {ticket.contrarian_count}",
                        "",
                        "| チーム | 選択 | モデル予測 | 投票率 | 逆張り |",
                        "|--------|------|-----------|--------|--------|",
                    ]
                )
                for pick in ticket.picks:
                    contrarian_mark = "★" if pick.is_contrarian else ""
                    lines.append(
                        f"| {pick.team} | {pick.category}点 | "
                        f"{pick.model_prob * 100:.1f}% | "
                        f"{pick.vote_rate * 100:.1f}% | {contrarian_mark} |"
                    )
                lines.append("")

        # チーム別EV分析
        lines.extend(["---", "", "## チーム別EV分析", ""])
        teams: dict[str, list[Recommendation]] = {}
        for r in recommendations:
            if r.team not in teams:
                teams[r.team] = []
            teams[r.team].append(r)

        for team, recs in teams.items():
            lines.append(f"### {team}")
            lines.append("")
            lines.append("| カテゴリ | モデル予測 | 投票率 | EV | 逆張りS | 最高EV |")
            lines.append("|----------|-----------|--------|-----|---------|--------|")
            for r in sorted(recs, key=lambda x: x.category):
                best_mark = "★" if r.is_best_ev_for_team else ""
                lines.append(
                    f"| {r.category}点 | {r.model_prob * 100:.1f}% | "
                    f"{r.vote_rate * 100:.1f}% | {r.ev:+.3f} | "
                    f"{r.contrarian_score:+.3f} | {best_mark} |"
                )
            lines.append("")

        # 逆張り機会ハイライト
        contrarian_recs = sorted(
            [r for r in recommendations if r.contrarian_score > 0],
            key=lambda r: r.contrarian_score,
            reverse=True,
        )
        if contrarian_recs:
            lines.extend(["---", "", "## 逆張り機会ハイライト", ""])
            for r in contrarian_recs[:10]:
                lines.append(
                    f"- {r.team} {r.category}点: "
                    f"モデル{r.model_prob * 100:.1f}% vs 投票{r.vote_rate * 100:.1f}% "
                    f"(逆張りS={r.contrarian_score:+.3f})"
                )
            lines.append("")

        # 投資サマリー
        if tickets:
            total_cost = sum(t.cost for t in tickets)
            total_ev = sum(t.estimated_ev for t in tickets)
            lines.extend(
                [
                    "---",
                    "",
                    "## 投資サマリー",
                    "",
                    f"- チケット枚数: {len(tickets)}枚",
                    f"- 合計購入額: ¥{total_cost:,}",
                    f"- 合計推定EV: ¥{total_ev:,.0f}",
                    "",
                ]
            )

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
                "*Generated by toto-predictor (enhanced)*",
            ]
        )

        # ファイル出力
        if output_path is None:
            output_path = str(self.reports_dir / f"round_{round_number}_enhanced_strategy.md")

        content = "\n".join(lines)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"拡張レポートを生成しました: {output_path}")
        return output_path

    def generate_marksheet_report(
        self,
        tickets: list[TicketRecommendation],
        output_path: str | None = None,
        round_number: int = 0,
    ) -> str:
        """マークシート風Markdownレポートを生成

        Args:
            tickets: TicketRecommendationリスト
            output_path: 出力ファイルパス
            round_number: toto回号

        Returns:
            生成したレポートのパス
        """
        if not tickets:
            logger.warning("チケットがありません")
            return ""

        if round_number == 0 and tickets:
            # チケットから回号を推定
            round_number = 0

        lines = [
            f"# 第{round_number}回 GOAL3 マークシート",
            "",
            f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            "",
        ]

        for ticket in tickets:
            lines.extend(
                [
                    f"## {ticket.ticket_type}チケット（¥{ticket.cost}）",
                    "",
                    "|  | 0点 | 1点 | 2点 | 3+点 |",
                    "|--|-----|-----|-----|------|",
                ]
            )

            # match_indexでソートし、試合単位でグループ化
            sorted_picks = sorted(ticket.picks, key=lambda p: (p.match_index, not p.is_home))
            current_match = 0
            for pick in sorted_picks:
                if pick.match_index > 0 and pick.match_index != current_match:
                    current_match = pick.match_index
                    lines.append(f"| **第{current_match}試合** | | | | |")

                jp_name = get_japanese_name(pick.team)
                ha_mark = "(H)" if pick.is_home else "(A)"
                display_name = f"{jp_name}{ha_mark}"

                # 全確率表示（選択カテゴリに◉マーク）
                probs = pick.all_probs or {}
                cells = []
                for cat in ("0", "1", "2", "3+"):
                    prob = probs.get(cat, 0.0)
                    pct = f"{prob * 100:.0f}%"
                    if cat == pick.category:
                        cells.append(f"**◉{pct}**")
                    else:
                        cells.append(pct)

                lines.append(f"| {display_name} | {' | '.join(cells)} |")

            lines.extend(
                [
                    "",
                    f"- 的中確率: {ticket.ticket_prob:.2e}",
                    f"- 推定払戻: ¥{ticket.estimated_payout:,.0f}",
                    f"- 推定EV: ¥{ticket.estimated_ev:,.0f}",
                    "",
                ]
            )

        # 免責事項
        lines.extend(
            [
                "---",
                "",
                "*Generated by toto-predictor (marksheet)*",
            ]
        )

        # ファイル出力
        if output_path is None:
            output_path = str(self.reports_dir / f"round_{round_number}_marksheet.md")

        content = "\n".join(lines)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"マークシートレポートを生成しました: {output_path}")
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
