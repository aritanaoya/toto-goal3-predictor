"""チーム名マッピングのテスト"""

from toto_predictor.models.team_names import TEAM_NAME_MAP, get_japanese_name


class TestGetJapaneseName:
    """get_japanese_name()のテスト"""

    def test_known_team_returns_japanese_name(self):
        """既知のチーム名が日本語短縮名に変換されること"""
        assert get_japanese_name("Kashima Antlers") == "鹿島"
        assert get_japanese_name("Kawasaki Frontale") == "川崎"
        assert get_japanese_name("Yokohama F. Marinos") == "横浜FM"

    def test_unknown_team_returns_english_name(self):
        """未知のチーム名は英語名がそのまま返ること"""
        assert get_japanese_name("Unknown FC") == "Unknown FC"

    def test_all_j1_teams_mapped(self):
        """主要J1チームがマッピングに含まれること"""
        j1_teams = [
            "Kashima Antlers",
            "Urawa Reds",
            "Kawasaki Frontale",
            "Yokohama F. Marinos",
            "Cerezo Osaka",
            "Gamba Osaka",
            "Vissel Kobe",
            "Sanfrecce Hiroshima",
            "Machida Zelvia",
            "Nagoya Grampus",
        ]
        for team in j1_teams:
            assert team in TEAM_NAME_MAP
