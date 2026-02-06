"""VoteScraperのテスト"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

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


class TestVoteScraperRetryFetch:
    """_retry_fetch()テスト"""

    @patch("toto_predictor.services.vote_scraper.requests.get")
    def test_retry_fetch_success(self, mock_get, tmp_path):
        """正常取得"""
        mock_response = MagicMock()
        mock_response.text = "<html>test</html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        scraper = VoteScraper(cache_dir=str(tmp_path))
        result = scraper._retry_fetch("https://example.com")

        assert result == "<html>test</html>"

    @patch("toto_predictor.services.vote_scraper.requests.get")
    @patch("toto_predictor.services.vote_scraper.time.sleep")
    def test_retry_fetch_timeout_retry(self, mock_sleep, mock_get, tmp_path):
        """タイムアウト時にリトライ"""
        mock_get.side_effect = [
            requests.Timeout("Timeout"),
            requests.Timeout("Timeout"),
            MagicMock(text="<html></html>", raise_for_status=MagicMock()),
        ]

        scraper = VoteScraper(cache_dir=str(tmp_path), max_retries=3)
        result = scraper._retry_fetch("https://example.com")

        assert result == "<html></html>"
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("toto_predictor.services.vote_scraper.requests.get")
    @patch("toto_predictor.services.vote_scraper.time.sleep")
    def test_retry_fetch_max_retries_exceeded(self, mock_sleep, mock_get, tmp_path):
        """最大リトライ超過"""
        mock_get.side_effect = requests.Timeout("Timeout")

        scraper = VoteScraper(cache_dir=str(tmp_path), max_retries=3)

        with pytest.raises(NetworkError) as exc_info:
            scraper._retry_fetch("https://example.com")

        assert "totoONEへの接続に失敗しました" in str(exc_info.value)
        assert mock_get.call_count == 3

    @patch("toto_predictor.services.vote_scraper.requests.get")
    def test_retry_fetch_http_4xx_no_retry(self, mock_get, tmp_path):
        """4xxエラーはリトライしない"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_error = requests.HTTPError()
        mock_error.response = mock_response
        mock_get.side_effect = mock_error

        scraper = VoteScraper(cache_dir=str(tmp_path), max_retries=3)

        with pytest.raises(NetworkError) as exc_info:
            scraper._retry_fetch("https://example.com")

        assert "HTTPエラー: 404" in str(exc_info.value)
        assert mock_get.call_count == 1  # リトライしない

    @patch("toto_predictor.services.vote_scraper.requests.get")
    @patch("toto_predictor.services.vote_scraper.time.sleep")
    def test_retry_fetch_http_5xx_retry(self, mock_sleep, mock_get, tmp_path):
        """5xxエラーはリトライ"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_error = requests.HTTPError()
        mock_error.response = mock_response

        success_response = MagicMock()
        success_response.text = "<html></html>"
        success_response.raise_for_status.return_value = None

        mock_get.side_effect = [mock_error, success_response]

        scraper = VoteScraper(cache_dir=str(tmp_path), max_retries=3)
        result = scraper._retry_fetch("https://example.com")

        assert result == "<html></html>"
        assert mock_get.call_count == 2

    @patch("toto_predictor.services.vote_scraper.requests.get")
    @patch("toto_predictor.services.vote_scraper.time.sleep")
    def test_retry_fetch_connection_error_retry(self, mock_sleep, mock_get, tmp_path):
        """接続エラーでリトライ"""
        success_response = MagicMock()
        success_response.text = "<html></html>"
        success_response.raise_for_status.return_value = None

        mock_get.side_effect = [
            requests.ConnectionError("Connection failed"),
            success_response,
        ]

        scraper = VoteScraper(cache_dir=str(tmp_path), max_retries=3)
        result = scraper._retry_fetch("https://example.com")

        assert result == "<html></html>"
        assert mock_get.call_count == 2


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
