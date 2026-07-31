"""VoteScraperのテスト"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from toto_predictor.models.exceptions import NetworkError, ParseError
from toto_predictor.models.vote_rate import VoteRate
from toto_predictor.services.vote_scraper import VoteScraper


class TestVoteScraperInit:
    """初期化テスト"""

    def test_init_creates_cache_directory(self, tmp_path):
        """キャッシュディレクトリが作成される"""
        cache_dir = tmp_path / "cache"
        VoteScraper(cache_dir=str(cache_dir))  # 初期化でディレクトリ作成
        assert cache_dir.exists()

    def test_init_sets_defaults(self, tmp_path):
        """デフォルト値が設定される"""
        scraper = VoteScraper(cache_dir=str(tmp_path))
        assert scraper.max_retries == 3
        assert scraper.timeout == 30
        assert scraper.headless is True

    def test_init_headless_option(self, tmp_path):
        """ヘッドレスモードの設定"""
        scraper = VoteScraper(cache_dir=str(tmp_path), headless=False)
        assert scraper.headless is False


class TestVoteScraperFetch:
    """fetch()テスト"""

    @patch.object(VoteScraper, "_retry_fetch")
    @patch.object(VoteScraper, "_parse_html")
    def test_fetch_success(self, mock_parse, mock_fetch, tmp_path):
        """正常なフェッチ"""
        mock_fetch.return_value = "<html></html>"
        mock_vote = VoteRate(
            round_number=1607,
            team="Test Team",
            vote_0=0.2,
            vote_1=0.3,
            vote_2=0.25,
            vote_3plus=0.25,
        )
        mock_parse.return_value = [mock_vote]

        scraper = VoteScraper(cache_dir=str(tmp_path))
        result = scraper.fetch(round_number=1607)

        assert len(result) == 1
        assert result[0].team == "Test Team"
        mock_fetch.assert_called_once()
        mock_parse.assert_called_once()

    @patch.object(VoteScraper, "_retry_fetch")
    @patch.object(VoteScraper, "_parse_html")
    def test_fetch_without_round_number(self, mock_parse, mock_fetch, tmp_path):
        """回号なしでフェッチ（最新）"""
        mock_fetch.return_value = "<html></html>"
        mock_parse.return_value = []

        scraper = VoteScraper(cache_dir=str(tmp_path))
        scraper.fetch()

        # ベースURLが使用される
        mock_fetch.assert_called_with(VoteScraper.BASE_URL)

    @patch.object(VoteScraper, "_retry_fetch")
    @patch.object(VoteScraper, "_parse_html")
    def test_fetch_with_round_number(self, mock_parse, mock_fetch, tmp_path):
        """回号指定でフェッチ"""
        mock_fetch.return_value = "<html></html>"
        mock_parse.return_value = []

        scraper = VoteScraper(cache_dir=str(tmp_path))
        scraper.fetch(round_number=1607)

        # 回号付きURLが使用される
        mock_fetch.assert_called_with(f"{VoteScraper.BASE_URL}/1607")

    @patch.object(VoteScraper, "_retry_fetch")
    @patch.object(VoteScraper, "_parse_html")
    @patch.object(VoteScraper, "_save_cache")
    def test_fetch_saves_cache(self, mock_save, mock_parse, mock_fetch, tmp_path):
        """フェッチ後にキャッシュ保存"""
        mock_fetch.return_value = "<html></html>"
        mock_vote = VoteRate(
            round_number=1607,
            team="Test Team",
            vote_0=0.2,
            vote_1=0.3,
            vote_2=0.25,
            vote_3plus=0.25,
        )
        mock_parse.return_value = [mock_vote]

        scraper = VoteScraper(cache_dir=str(tmp_path))
        scraper.fetch(round_number=1607)

        mock_save.assert_called_once()


def _create_mock_playwright():
    """Playwright のモックを生成するヘルパー"""
    mock_page = MagicMock()
    mock_page.content.return_value = "<html>test</html>"

    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mock_chromium = MagicMock()
    mock_chromium.launch.return_value = mock_browser

    mock_pw = MagicMock()
    mock_pw.chromium = mock_chromium

    return mock_pw, mock_browser, mock_page


class TestVoteScraperRetryFetch:
    """_retry_fetch()テスト（Playwright版）"""

    @patch("toto_predictor.services.vote_scraper.sync_playwright")
    def test_retry_fetch_success(self, mock_sync_pw, tmp_path):
        """正常取得"""
        mock_pw, mock_browser, mock_page = _create_mock_playwright()
        mock_sync_pw.return_value.__enter__ = MagicMock(return_value=mock_pw)
        mock_sync_pw.return_value.__exit__ = MagicMock(return_value=False)

        scraper = VoteScraper(cache_dir=str(tmp_path))
        result = scraper._retry_fetch("https://example.com")

        assert result == "<html>test</html>"
        mock_page.goto.assert_called_once()
        mock_browser.close.assert_called_once()

    @patch("toto_predictor.services.vote_scraper.sync_playwright")
    @patch("toto_predictor.services.vote_scraper.time.sleep")
    def test_retry_fetch_error_then_success(self, mock_sleep, mock_sync_pw, tmp_path):
        """エラー後にリトライして成功"""
        mock_pw_fail = MagicMock()
        mock_pw_fail.chromium.launch.side_effect = Exception("Browser launch failed")

        mock_pw_ok, mock_browser, mock_page = _create_mock_playwright()

        call_count = [0]

        def side_effect_enter(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 1:
                return mock_pw_fail
            return mock_pw_ok

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(side_effect=side_effect_enter)
        mock_cm.__exit__ = MagicMock(return_value=False)
        mock_sync_pw.return_value = mock_cm

        scraper = VoteScraper(cache_dir=str(tmp_path), max_retries=3)
        result = scraper._retry_fetch("https://example.com")

        assert result == "<html>test</html>"
        assert mock_sleep.call_count == 1

    @patch("toto_predictor.services.vote_scraper.sync_playwright")
    @patch("toto_predictor.services.vote_scraper.time.sleep")
    def test_retry_fetch_max_retries_exceeded(self, mock_sleep, mock_sync_pw, tmp_path):
        """最大リトライ超過"""
        mock_pw = MagicMock()
        mock_pw.chromium.launch.side_effect = Exception("Browser launch failed")

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_pw)
        mock_cm.__exit__ = MagicMock(return_value=False)
        mock_sync_pw.return_value = mock_cm

        scraper = VoteScraper(cache_dir=str(tmp_path), max_retries=3)

        with pytest.raises(NetworkError) as exc_info:
            scraper._retry_fetch("https://example.com")

        assert "totoONEへの接続に失敗しました" in str(exc_info.value)

    @patch("toto_predictor.services.vote_scraper.sync_playwright")
    def test_retry_fetch_passes_headless_option(self, mock_sync_pw, tmp_path):
        """headlessオプションがPlaywrightに渡される"""
        mock_pw, mock_browser, mock_page = _create_mock_playwright()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_pw)
        mock_cm.__exit__ = MagicMock(return_value=False)
        mock_sync_pw.return_value = mock_cm

        scraper = VoteScraper(cache_dir=str(tmp_path), headless=False)
        scraper._retry_fetch("https://example.com")

        mock_pw.chromium.launch.assert_called_with(headless=False)

    @patch("toto_predictor.services.vote_scraper.sync_playwright")
    def test_retry_fetch_waits_for_selector(self, mock_sync_pw, tmp_path):
        """セレクタ待機が実行される"""
        mock_pw, mock_browser, mock_page = _create_mock_playwright()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_pw)
        mock_cm.__exit__ = MagicMock(return_value=False)
        mock_sync_pw.return_value = mock_cm

        scraper = VoteScraper(cache_dir=str(tmp_path))
        scraper._retry_fetch("https://example.com")

        mock_page.wait_for_selector.assert_called_once()

    @patch("toto_predictor.services.vote_scraper.sync_playwright")
    def test_retry_fetch_selector_timeout_still_returns_html(self, mock_sync_pw, tmp_path):
        """セレクタ待機タイムアウトでもHTMLを返す"""
        mock_pw, mock_browser, mock_page = _create_mock_playwright()
        mock_page.wait_for_selector.side_effect = Exception("Timeout")
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_pw)
        mock_cm.__exit__ = MagicMock(return_value=False)
        mock_sync_pw.return_value = mock_cm

        scraper = VoteScraper(cache_dir=str(tmp_path))
        result = scraper._retry_fetch("https://example.com")

        # セレクタタイムアウトでもHTMLは取得できる
        assert result == "<html>test</html>"


class TestVoteScraperCache:
    """キャッシュテスト"""

    def test_get_cached_not_found(self, tmp_path):
        """キャッシュなし"""
        scraper = VoteScraper(cache_dir=str(tmp_path))
        result = scraper.get_cached(round_number=9999)
        assert result is None

    def test_get_cached_success(self, tmp_path):
        """キャッシュ取得成功"""
        # キャッシュファイルを作成
        cache_data = [
            {
                "round_number": 1607,
                "team": "Test Team",
                "vote_0": 0.2,
                "vote_1": 0.3,
                "vote_2": 0.25,
                "vote_3plus": 0.25,
            }
        ]
        cache_file = tmp_path / "round_1607.json"
        with open(cache_file, "w") as f:
            json.dump(cache_data, f)

        scraper = VoteScraper(cache_dir=str(tmp_path))
        result = scraper.get_cached(round_number=1607)

        assert result is not None
        assert len(result) == 1
        assert result[0].team == "Test Team"

    def test_get_cached_corrupted_file(self, tmp_path):
        """破損キャッシュファイル"""
        cache_file = tmp_path / "round_1607.json"
        with open(cache_file, "w") as f:
            f.write("not valid json")

        scraper = VoteScraper(cache_dir=str(tmp_path))
        result = scraper.get_cached(round_number=1607)

        assert result is None

    def test_save_cache(self, tmp_path):
        """キャッシュ保存"""
        vote_rates = [
            VoteRate(
                round_number=1607,
                team="Test Team",
                vote_0=0.2,
                vote_1=0.3,
                vote_2=0.25,
                vote_3plus=0.25,
            )
        ]

        scraper = VoteScraper(cache_dir=str(tmp_path))
        scraper._save_cache(vote_rates, round_number=1607)

        cache_file = tmp_path / "round_1607.json"
        assert cache_file.exists()

        with open(cache_file) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["team"] == "Test Team"


class TestVoteScraperParseHtml:
    """HTML解析テスト"""

    def test_parse_html_with_goal3_section(self, tmp_path, sample_html_vote_rates):
        """GOAL3セクションあり"""
        scraper = VoteScraper(cache_dir=str(tmp_path))
        result = scraper._parse_html(sample_html_vote_rates, round_number=1607)

        assert len(result) == 2
        assert result[0].team == "Yokohama F. Marinos"
        assert result[0].vote_0 == pytest.approx(0.225, abs=0.001)

    def test_parse_html_no_goal3_section(self, tmp_path):
        """GOAL3セクションなし（ParseError発生）"""
        html = "<html><body><div>No GOAL3 here</div></body></html>"

        scraper = VoteScraper(cache_dir=str(tmp_path))

        # ParseErrorが発生することを確認
        with pytest.raises(ParseError) as exc_info:
            scraper._parse_html(html, round_number=1607)

        assert "GOAL3セクションが見つかりません" in str(exc_info.value)

    def test_parse_html_with_section_but_no_teams(self, tmp_path):
        """GOAL3セクションあるがチームなし（ParseError発生）"""
        html = """
        <html><body>
            <div class="goal3-prediction">
                <table></table>
            </div>
        </body></html>
        """

        scraper = VoteScraper(cache_dir=str(tmp_path))

        # ParseErrorが発生することを確認
        with pytest.raises(ParseError) as exc_info:
            scraper._parse_html(html, round_number=1607)

        assert "投票率データが抽出できませんでした" in str(exc_info.value)


class TestVoteScraperParsePercentage:
    """パーセント解析テスト"""

    def test_parse_percentage_normal(self, tmp_path):
        """通常のパーセント"""
        scraper = VoteScraper(cache_dir=str(tmp_path))

        assert scraper._parse_percentage("25.5%") == pytest.approx(0.255, abs=0.001)
        assert scraper._parse_percentage("100%") == pytest.approx(1.0, abs=0.001)
        assert scraper._parse_percentage("0%") == pytest.approx(0.0, abs=0.001)

    def test_parse_percentage_with_whitespace(self, tmp_path):
        """空白付き"""
        scraper = VoteScraper(cache_dir=str(tmp_path))

        assert scraper._parse_percentage("  25.5%  ") == pytest.approx(0.255, abs=0.001)

    def test_parse_percentage_with_comma(self, tmp_path):
        """カンマ付き"""
        scraper = VoteScraper(cache_dir=str(tmp_path))

        assert scraper._parse_percentage("1,234.5%") == pytest.approx(12.345, abs=0.001)

    def test_parse_percentage_invalid(self, tmp_path):
        """無効な値"""
        scraper = VoteScraper(cache_dir=str(tmp_path))

        assert scraper._parse_percentage("invalid") == 0.0
        assert scraper._parse_percentage("") == 0.0


class TestVoteScraperParseHtmlEdgeCases:
    """HTML解析のエッジケーステスト"""

    def test_parse_html_error_contains_round_number(self, tmp_path):
        """ParseErrorにround_numberが含まれる"""
        html = "<html><body><div>No GOAL3</div></body></html>"
        scraper = VoteScraper(cache_dir=str(tmp_path))

        with pytest.raises(ParseError) as exc_info:
            scraper._parse_html(html, round_number=1607)

        # エラー詳細にround_numberが含まれる
        assert exc_info.value.details is not None
        assert exc_info.value.details.get("round_number") == 1607

    def test_parse_html_error_contains_hint(self, tmp_path):
        """ParseErrorにキャッシュファイルのhintが含まれる"""
        html = "<html><body><div>No GOAL3</div></body></html>"
        scraper = VoteScraper(cache_dir=str(tmp_path))

        with pytest.raises(ParseError) as exc_info:
            scraper._parse_html(html, round_number=1607)

        # hintが含まれる
        assert exc_info.value.details is not None
        assert "hint" in exc_info.value.details
        assert "round_1607.json" in exc_info.value.details["hint"]

    def test_parse_html_with_alternative_selector(self, tmp_path):
        """代替セレクタ（section#goal3）でも解析できる"""
        html = """
        <html><body>
            <section id="goal3">
                <table>
                    <tr class="team-row">
                        <td class="team-name">Team A</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">30%</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">20%</td>
                    </tr>
                </table>
            </section>
        </body></html>
        """
        scraper = VoteScraper(cache_dir=str(tmp_path))
        result = scraper._parse_html(html, round_number=1607)

        assert len(result) == 1
        assert result[0].team == "Team A"

    def test_parse_html_incomplete_vote_rates(self, tmp_path):
        """投票率が不完全な行はスキップされる"""
        html = """
        <html><body>
            <div class="goal3-prediction">
                <table>
                    <tr class="team-row">
                        <td class="team-name">Complete Team</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">30%</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">20%</td>
                    </tr>
                    <tr class="team-row">
                        <td class="team-name">Incomplete Team</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">30%</td>
                    </tr>
                </table>
            </div>
        </body></html>
        """
        scraper = VoteScraper(cache_dir=str(tmp_path))
        result = scraper._parse_html(html, round_number=1607)

        # 完全なデータを持つチームのみ
        assert len(result) == 1
        assert result[0].team == "Complete Team"

    def test_parse_html_missing_team_name(self, tmp_path):
        """チーム名がない行はスキップされる"""
        html = """
        <html><body>
            <div class="goal3-prediction">
                <table>
                    <tr class="team-row">
                        <td class="team-name">Valid Team</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">30%</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">20%</td>
                    </tr>
                    <tr class="team-row">
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">30%</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">20%</td>
                    </tr>
                </table>
            </div>
        </body></html>
        """
        scraper = VoteScraper(cache_dir=str(tmp_path))
        result = scraper._parse_html(html, round_number=1607)

        # チーム名があるもののみ
        assert len(result) == 1
        assert result[0].team == "Valid Team"


class TestVoteScraperMockData:
    """モックデータテスト"""

    def test_get_mock_data(self, tmp_path):
        """モックデータ生成"""
        scraper = VoteScraper(cache_dir=str(tmp_path))
        result = scraper.get_mock_data(round_number=1607)

        assert len(result) == 6
        for vr in result:
            assert isinstance(vr, VoteRate)
            assert vr.round_number == 1607
            # 確率の合計が約1
            total = vr.vote_0 + vr.vote_1 + vr.vote_2 + vr.vote_3plus
            assert abs(total - 1.0) < 0.01

    def test_get_mock_data_different_rounds(self, tmp_path):
        """異なる回号でモックデータ生成"""
        scraper = VoteScraper(cache_dir=str(tmp_path))

        result_1600 = scraper.get_mock_data(round_number=1600)
        result_1607 = scraper.get_mock_data(round_number=1607)

        assert all(vr.round_number == 1600 for vr in result_1600)
        assert all(vr.round_number == 1607 for vr in result_1607)


class TestVoteScraperFetchSchedule:
    """fetch_schedule()テスト"""

    def test_fetch_schedule_from_cache(self, tmp_path):
        """キャッシュからスケジュール取得"""
        schedule_dir = tmp_path / "schedules"
        schedule_dir.mkdir()
        cache_data = {
            "round_number": 1608,
            "matches": [
                {"match_index": 1, "home_team": "Team A", "away_team": "Team B"},
                {"match_index": 2, "home_team": "Team C", "away_team": "Team D"},
            ],
        }
        with open(schedule_dir / "round_1608.json", "w") as f:
            json.dump(cache_data, f)

        # cache_dirをvotes/に設定し、親ディレクトリ/schedulesにキャッシュがある構造
        votes_dir = tmp_path / "votes"
        votes_dir.mkdir()
        # schedulesディレクトリはcache_dir.parent / "schedules" = tmp_path / "schedules"
        scraper = VoteScraper(cache_dir=str(votes_dir))
        result = scraper.fetch_schedule(1608)

        assert result is not None
        assert result.round_number == 1608
        assert len(result.matches) == 2

    @patch.object(VoteScraper, "_retry_fetch")
    def test_fetch_schedule_from_html(self, mock_fetch, tmp_path):
        """HTMLから対戦カードスクレイピング"""
        html = """
        <html><body>
            <div class="goal3-prediction">
                <table>
                    <tr class="team-row">
                        <td class="team-name">Kashima Antlers</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">30%</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">20%</td>
                    </tr>
                    <tr class="team-row">
                        <td class="team-name">Kawasaki Frontale</td>
                        <td class="vote-rate">20%</td>
                        <td class="vote-rate">35%</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">20%</td>
                    </tr>
                    <tr class="team-row">
                        <td class="team-name">Machida Zelvia</td>
                        <td class="vote-rate">22%</td>
                        <td class="vote-rate">33%</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">20%</td>
                    </tr>
                    <tr class="team-row">
                        <td class="team-name">Tokyo</td>
                        <td class="vote-rate">24%</td>
                        <td class="vote-rate">31%</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">20%</td>
                    </tr>
                </table>
            </div>
        </body></html>
        """
        mock_fetch.return_value = html

        scraper = VoteScraper(cache_dir=str(tmp_path))
        result = scraper.fetch_schedule(1608)

        assert result is not None
        assert len(result.matches) == 2
        assert result.matches[0].home_team == "Kashima Antlers"
        assert result.matches[0].away_team == "Kawasaki Frontale"
        assert result.matches[1].home_team == "Machida Zelvia"
        assert result.matches[1].away_team == "Tokyo"

    @patch.object(VoteScraper, "_retry_fetch")
    def test_fetch_schedule_returns_none_on_failure(self, mock_fetch, tmp_path):
        """取得失敗時にNoneが返ること"""
        mock_fetch.side_effect = Exception("Network error")

        cache_dir = tmp_path / "votes_fail"
        cache_dir.mkdir()
        scraper = VoteScraper(cache_dir=str(cache_dir))
        result = scraper.fetch_schedule(1609)

        assert result is None

    @patch.object(VoteScraper, "_retry_fetch")
    def test_fetch_schedule_no_goal3_section(self, mock_fetch, tmp_path):
        """GOAL3セクションが見つからない場合にNoneが返ること"""
        mock_fetch.return_value = "<html><body><div>No GOAL3</div></body></html>"

        cache_dir = tmp_path / "votes_no_goal3"
        cache_dir.mkdir()
        scraper = VoteScraper(cache_dir=str(cache_dir))
        result = scraper.fetch_schedule(1610)

        assert result is None

    @patch.object(VoteScraper, "_retry_fetch")
    def test_fetch_schedule_saves_cache(self, mock_fetch, tmp_path):
        """スケジュール取得後にキャッシュが保存されること"""
        html = """
        <html><body>
            <div class="goal3-prediction">
                <table>
                    <tr class="team-row">
                        <td class="team-name">Team A</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">30%</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">20%</td>
                    </tr>
                    <tr class="team-row">
                        <td class="team-name">Team B</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">30%</td>
                        <td class="vote-rate">25%</td>
                        <td class="vote-rate">20%</td>
                    </tr>
                </table>
            </div>
        </body></html>
        """
        mock_fetch.return_value = html

        scraper = VoteScraper(cache_dir=str(tmp_path))
        scraper.fetch_schedule(1608)

        cache_path = tmp_path.parent / "schedules" / "round_1608.json"
        assert cache_path.exists()
