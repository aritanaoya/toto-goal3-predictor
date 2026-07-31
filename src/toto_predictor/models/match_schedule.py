"""対戦カードスケジュールデータモデル

toto GOAL3の3試合分の対戦カード情報を表すデータクラスを定義します。
"""

import json
from dataclasses import dataclass, field
from typing import Any, Self


@dataclass
class MatchPair:
    """1試合の対戦カードを表すデータクラス

    Attributes:
        match_index: 試合番号（1-3）
        home_team: ホームチーム名（英語）
        away_team: アウェイチーム名（英語）
    """

    match_index: int
    home_team: str
    away_team: str

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換"""
        return {
            "match_index": self.match_index,
            "home_team": self.home_team,
            "away_team": self.away_team,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """辞書からMatchPairを生成"""
        return cls(
            match_index=data["match_index"],
            home_team=data["home_team"],
            away_team=data["away_team"],
        )


@dataclass
class MatchSchedule:
    """GOAL3の対戦カードスケジュールを表すデータクラス

    Attributes:
        round_number: toto回号
        matches: 対戦カードリスト（3試合）
    """

    round_number: int
    matches: list[MatchPair] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換"""
        return {
            "round_number": self.round_number,
            "matches": [m.to_dict() for m in self.matches],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """辞書からMatchScheduleを生成"""
        return cls(
            round_number=data["round_number"],
            matches=[MatchPair.from_dict(m) for m in data.get("matches", [])],
        )

    def to_json(self, path: str) -> None:
        """JSONファイルに保存

        Args:
            path: 出力ファイルパス
        """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, path: str) -> Self:
        """JSONファイルから読み込み

        Args:
            path: 入力ファイルパス

        Returns:
            MatchScheduleオブジェクト
        """
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_matches_str(cls, matches_str: str, round_number: int = 0) -> Self:
        """--matches文字列からMatchScheduleを生成

        Args:
            matches_str: 対戦カード文字列（例: "TeamA:TeamB,TeamC:TeamD,TeamE:TeamF"）
            round_number: toto回号

        Returns:
            MatchScheduleオブジェクト
        """
        pairs = []
        for i, pair_str in enumerate(matches_str.split(","), start=1):
            pair_str = pair_str.strip()
            if ":" not in pair_str:
                continue
            home, away = pair_str.split(":", 1)
            pairs.append(
                MatchPair(
                    match_index=i,
                    home_team=home.strip(),
                    away_team=away.strip(),
                )
            )
        return cls(round_number=round_number, matches=pairs)

    def get_team_info(self, team: str) -> tuple[int, str, bool] | None:
        """チーム名から試合情報を取得

        Args:
            team: チーム名

        Returns:
            (match_index, opponent, is_home) のタプル。見つからない場合はNone。
        """
        for match in self.matches:
            if match.home_team == team:
                return (match.match_index, match.away_team, True)
            if match.away_team == team:
                return (match.match_index, match.home_team, False)
        return None
