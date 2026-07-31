"""チーム名マッピングモジュール

英語チーム名から日本語短縮名への変換を提供します。
"""

# J1リーグ全チームの英語名→日本語短縮名マッピング
TEAM_NAME_MAP: dict[str, str] = {
    "Kashima Antlers": "鹿島",
    "Urawa Reds": "浦和",
    "Kashiwa Reysol": "柏",
    "Tokyo": "FC東京",
    "FC Tokyo": "FC東京",
    "Kawasaki Frontale": "川崎",
    "Yokohama F. Marinos": "横浜FM",
    "Yokohama FC": "横浜FC",
    "Shonan Bellmare": "湘南",
    "Cerezo Osaka": "C大阪",
    "Gamba Osaka": "G大阪",
    "Vissel Kobe": "神戸",
    "Sanfrecce Hiroshima": "広島",
    "Avispa Fukuoka": "福岡",
    "Sagan Tosu": "鳥栖",
    "Nagoya Grampus": "名古屋",
    "Consadole Sapporo": "札幌",
    "Jubilo Iwata": "磐田",
    "Albirex Niigata": "新潟",
    "Machida Zelvia": "町田",
    "Kyoto Sanga": "京都",
    "Tokushima Vortis": "徳島",
    "Vegalta Sendai": "仙台",
    "Montedio Yamagata": "山形",
    "Shimizu S-Pulse": "清水",
    "Ventforet Kofu": "甲府",
    "Fagiano Okayama": "岡山",
    "V-Varen Nagasaki": "長崎",
    "Roasso Kumamoto": "熊本",
    "Ehime FC": "愛媛",
    "Omiya Ardija": "大宮",
    "Tochigi SC": "栃木",
    "Mito Hollyhock": "水戸",
    "Zweigen Kanazawa": "金沢",
    "Renofa Yamaguchi": "山口",
    "Blaublitz Akita": "秋田",
    "FC Ryukyu": "琉球",
}


def get_japanese_name(english_name: str) -> str:
    """英語チーム名から日本語短縮名を取得

    Args:
        english_name: 英語チーム名（例: "Kashima Antlers"）

    Returns:
        日本語短縮名（例: "鹿島"）。マッピングがない場合は英語名をそのまま返す。
    """
    return TEAM_NAME_MAP.get(english_name, english_name)
