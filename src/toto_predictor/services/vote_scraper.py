"""投票率スクレイパー

このモジュールは、totoONEから投票率データをPlaywrightでスクレイピングします。
totoONEはSPA構造のため、JavaScriptレンダリング後のHTMLを取得する必要があります。
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from playwright.sync_api import sync_playwright

from ..models.exceptions import NetworkError, ParseError
from ..models.match_schedule import MatchPair, MatchSchedule
from ..models.vote_rate import VoteRate

logger = logging.getLogger(__name__)


class VoteScraper:
    """totoONE投票率スクレイパー（Playwright対応）

    totoONEから GOAL3 の投票率データを取得します。
    SPA構造に対応するため、Playwrightでブラウザレンダリング後のHTMLを解析します。

    Attributes:
        base_url: totoONEのベースURL
        cache_dir: キャッシュ保存ディレクトリ
        max_retries: 最大リトライ回数
        timeout: リクエストタイムアウト（ミリ秒）
        headless: ヘッドレスモードで実行するかどうか
    """

    BASE_URL = "https://www.totoone.jp/prediction"
    USER_AGENT = "toto-predictor/1.0 (educational purposes)"

    def __init__(
        self,
        cache_dir: str = "data/votes",
        max_retries: int = 3,
        timeout: int = 30,
        headless: bool = True,
    ) -> None:
        """スクレイパーを初期化

        Args:
            cache_dir: キャッシュ保存ディレクトリ
            max_retries: 最大リトライ回数
            timeout: リクエストタイムアウト（秒）
            headless: ヘッドレスモードで実行するかどうか
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self.timeout = timeout
        self.headless = headless

    def fetch(self, round_number: int | None = None) -> list[VoteRate]:
        """投票率を取得

        Args:
            round_number: toto回号（Noneの場合は最新回）

        Returns:
            VoteRateオブジェクトのリスト（6チーム分）

        Raises:
            ScrapingError: スクレイピングに失敗した場合
        """
        # URLの構築
        if round_number:
            url = f"{self.BASE_URL}/{round_number}"
        else:
            url = self.BASE_URL

        logger.info(f"投票率を取得中（Playwright）: {url}")

        # Playwrightでレンダリング済みHTMLを取得
        html = self._retry_fetch(url)

        # HTML解析
        vote_rates = self._parse_html(html, round_number or 0)

        # キャッシュに保存
        if vote_rates:
            actual_round = vote_rates[0].round_number
            self._save_cache(vote_rates, actual_round)

        logger.info(f"{len(vote_rates)}チームの投票率を取得しました")
        return vote_rates

    def get_cached(self, round_number: int) -> list[VoteRate] | None:
        """キャッシュから投票率を取得

        Args:
            round_number: toto回号

        Returns:
            VoteRateオブジェクトのリスト、キャッシュがなければNone
        """
        cache_path = self.cache_dir / f"round_{round_number}.json"
        if not cache_path.exists():
            return None

        try:
            with open(cache_path) as f:
                data = json.load(f)
            return [VoteRate.from_dict(d) for d in data]
        except Exception as e:
            logger.warning(f"キャッシュの読み込みに失敗: {e}")
            return None

    def fetch_schedule(self, round_number: int) -> MatchSchedule | None:
        """totoONEから対戦カードスケジュールを取得

        Args:
            round_number: toto回号

        Returns:
            MatchScheduleオブジェクト。取得失敗時はNone。
        """
        # キャッシュ確認
        schedule_dir = self.cache_dir.parent / "schedules"
        schedule_dir.mkdir(parents=True, exist_ok=True)
        cache_path = schedule_dir / f"round_{round_number}.json"

        if cache_path.exists():
            try:
                schedule = MatchSchedule.from_json(str(cache_path))
                logger.info(f"キャッシュから対戦カードを取得: {cache_path}")
                return schedule
            except Exception as e:
                logger.warning(f"スケジュールキャッシュの読み込みに失敗: {e}")

        # totoONEからスクレイピング
        try:
            url = f"{self.BASE_URL}/{round_number}"
            logger.info(f"対戦カードを取得中: {url}")
            html = self._retry_fetch(url)
            parsed = self._parse_schedule_html(html, round_number)

            if parsed and parsed.matches:
                parsed.to_json(str(cache_path))
                logger.info(f"{len(parsed.matches)}試合の対戦カードを取得しました")
                return parsed

        except Exception as e:
            logger.warning(f"対戦カードの取得に失敗: {e}")

        return None

    def _parse_schedule_html(self, html: str, round_number: int) -> MatchSchedule | None:
        """HTMLから対戦カード情報を抽出

        Args:
            html: HTMLコンテンツ
            round_number: toto回号

        Returns:
            MatchScheduleオブジェクト。解析失敗時はNone。
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            matches: list[MatchPair] = []

            # GOAL3セクションを探す
            goal3_section = soup.find("div", class_="goal3-prediction")
            if goal3_section is None:
                goal3_section = soup.find("section", id="goal3")
            if goal3_section is None:
                goal3_section = soup.find("div", class_="prediction-table")

            if goal3_section is None or not isinstance(goal3_section, Tag):
                logger.warning("GOAL3セクションが見つかりません")
                return None

            # 対戦カード行を探す
            match_rows = goal3_section.find_all("div", class_="match-pair")
            if not match_rows:
                # team-row から対戦カードを推定（2チームずつペアリング）
                team_rows = goal3_section.find_all("tr", class_="team-row")
                team_names = []
                for row in team_rows:
                    name_td = row.find("td", class_="team-name")
                    if name_td:
                        team_names.append(name_td.get_text(strip=True))

                for i in range(0, len(team_names) - 1, 2):
                    matches.append(
                        MatchPair(
                            match_index=i // 2 + 1,
                            home_team=team_names[i],
                            away_team=team_names[i + 1],
                        )
                    )
            else:
                for i, row in enumerate(match_rows, start=1):
                    teams = row.find_all("span", class_="team-name")
                    if len(teams) >= 2:
                        matches.append(
                            MatchPair(
                                match_index=i,
                                home_team=teams[0].get_text(strip=True),
                                away_team=teams[1].get_text(strip=True),
                            )
                        )

            if matches:
                return MatchSchedule(round_number=round_number, matches=matches)

        except Exception as e:
            logger.warning(f"対戦カードHTMLの解析に失敗: {e}")

        return None

    def _retry_fetch(self, url: str) -> str:
        """リトライ付きでPlaywrightによるHTMLレンダリングを実行

        Args:
            url: 取得するURL

        Returns:
            レンダリング済みHTMLコンテンツ

        Raises:
            NetworkError: ネットワークエラーが発生した場合
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=self.headless)
                    context = browser.new_context(
                        user_agent=self.USER_AGENT,
                    )
                    page = context.new_page()

                    # ページにアクセス
                    page.goto(url, timeout=self.timeout * 1000)

                    # JavaScriptレンダリング完了を待機
                    # GOAL3のセクションが表示されるまで待つ
                    try:
                        page.wait_for_selector(
                            ".goal3-prediction, #goal3, .vote-rate, .prediction-table",
                            timeout=self.timeout * 1000,
                        )
                    except Exception:
                        # セレクタが見つからない場合でもHTMLを取得して解析を試みる
                        logger.warning(
                            "投票率セクションの待機がタイムアウト、HTMLを取得して解析を試みます"
                        )

                    # レンダリング済みHTMLを取得
                    html = page.content()

                    browser.close()
                    return html

            except Exception as e:
                last_error = e
                wait_time = 2**attempt
                logger.warning(
                    f"Playwright取得エラー (試行 {attempt + 1}/{self.max_retries}), "
                    f"{wait_time}秒後にリトライ: {e}"
                )
                time.sleep(wait_time)

        raise NetworkError(
            f"totoONEへの接続に失敗しました（Playwright、{self.max_retries}回リトライ）",
            details={"url": url, "last_error": str(last_error)},
        )

    def _parse_html(self, html: str, round_number: int) -> list[VoteRate]:
        """HTMLから投票率を抽出

        Args:
            html: HTMLコンテンツ
            round_number: toto回号

        Returns:
            VoteRateオブジェクトのリスト

        Raises:
            ParseError: HTML解析に失敗した場合
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # GOAL3のセクションを探す
            vote_rates: list[VoteRate] = []

            # 投票率テーブルを探す（複数のセレクタを試行）
            goal3_section = soup.find("div", class_="goal3-prediction")
            if goal3_section is None:
                goal3_section = soup.find("section", id="goal3")
            if goal3_section is None:
                goal3_section = soup.find("div", class_="prediction-table")

            if goal3_section is None or not isinstance(goal3_section, Tag):
                raise ParseError(
                    "GOAL3セクションが見つかりません。"
                    "サイト構造が変更された可能性があります。"
                    "キャッシュファイルを手動で用意するか、get_mock_data()を使用してください。",
                    details={
                        "round_number": round_number,
                        "hint": f"data/votes/round_{round_number}.json にキャッシュを配置",
                    },
                )

            # 各チームの投票率を抽出
            team_rows = goal3_section.find_all("tr", class_="team-row")
            for row in team_rows:
                team_name = row.find("td", class_="team-name")
                if team_name is None:
                    continue

                rates = row.find_all("td", class_="vote-rate")
                if len(rates) < 4:
                    continue

                vote_rate = VoteRate(
                    round_number=round_number,
                    team=team_name.get_text(strip=True),
                    vote_0=self._parse_percentage(rates[0].get_text()),
                    vote_1=self._parse_percentage(rates[1].get_text()),
                    vote_2=self._parse_percentage(rates[2].get_text()),
                    vote_3plus=self._parse_percentage(rates[3].get_text()),
                )
                vote_rates.append(vote_rate)

            if not vote_rates:
                raise ParseError(
                    "投票率データが抽出できませんでした。サイト構造が変更された可能性があります。",
                    details={
                        "round_number": round_number,
                        "hint": f"data/votes/round_{round_number}.json にキャッシュを配置",
                    },
                )

            return vote_rates

        except ParseError:
            # ParseErrorはそのまま再スロー
            raise
        except Exception as e:
            raise ParseError(
                f"HTML解析に失敗しました: {e}",
                details={"round_number": round_number},
            ) from e

    def _parse_percentage(self, text: str) -> float:
        """パーセント文字列を0-1の小数に変換

        Args:
            text: パーセント文字列（例: "25.5%"）

        Returns:
            小数値（例: 0.255）
        """
        try:
            cleaned = text.strip().replace("%", "").replace(",", "")
            return float(cleaned) / 100
        except (ValueError, AttributeError):
            return 0.0

    def _save_cache(self, vote_rates: list[VoteRate], round_number: int) -> None:
        """投票率をキャッシュに保存

        Args:
            vote_rates: VoteRateオブジェクトのリスト
            round_number: toto回号
        """
        cache_path = self.cache_dir / f"round_{round_number}.json"
        try:
            data = [vr.to_dict() for vr in vote_rates]
            with open(cache_path, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"投票率をキャッシュに保存: {cache_path}")
        except Exception as e:
            logger.warning(f"キャッシュの保存に失敗: {e}")

    def get_mock_data(self, round_number: int) -> list[VoteRate]:
        """開発用モックデータを返す

        サイトのスクレイピングが不可能な場合に、開発・テスト用途で使用できます。
        本番環境では、キャッシュファイルを手動で用意することを推奨します。

        Args:
            round_number: toto回号

        Returns:
            モックVoteRateオブジェクトのリスト
        """
        logger.warning("モックデータを使用しています（開発・テスト用）")
        teams = [
            "Yokohama F. Marinos",
            "Kawasaki Frontale",
            "Kashima Antlers",
            "Urawa Reds",
            "Tokyo",
            "Machida Zelvia",
        ]

        mock_rates = []
        for team in teams:
            # ランダムな投票率を生成（合計100%になるように）
            import random

            rates = [random.random() for _ in range(4)]
            total = sum(rates)
            rates = [r / total for r in rates]

            mock_rates.append(
                VoteRate(
                    round_number=round_number,
                    team=team,
                    vote_0=rates[0],
                    vote_1=rates[1],
                    vote_2=rates[2],
                    vote_3plus=rates[3],
                    fetched_at=datetime.now(),
                )
            )

        return mock_rates
