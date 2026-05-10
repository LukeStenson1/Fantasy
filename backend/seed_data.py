"""Seed NFL fantasy data — top fantasy-relevant players with realistic stats across 3 seasons.

Stats are approximations of real player production for 2022, 2023, 2024 seasons. Used to power
the fantasy reference site. Calls populate_db() during startup if collection is empty.
"""
from datetime import datetime, timezone
import uuid


def _fp(rec: dict, scoring: str = "half_ppr") -> float:
    """Compute fantasy points from a season record."""
    pts = 0.0
    pts += rec.get("pass_yds", 0) / 25.0
    pts += rec.get("pass_td", 0) * 4
    pts -= rec.get("pass_int", 0) * 2
    pts += rec.get("rush_yds", 0) / 10.0
    pts += rec.get("rush_td", 0) * 6
    pts += rec.get("rec_yds", 0) / 10.0
    pts += rec.get("rec_td", 0) * 6
    rec_count = rec.get("receptions", 0)
    if scoring == "ppr":
        pts += rec_count * 1.0
    elif scoring == "half_ppr":
        pts += rec_count * 0.5
    pts -= rec.get("fumbles_lost", 0) * 2
    return round(pts, 2)


def _enrich_season(s: dict) -> dict:
    games = s.get("games", 17)
    s["total_yards"] = s.get("pass_yds", 0) + s.get("rush_yds", 0) + s.get("rec_yds", 0)
    s["total_tds"] = s.get("pass_td", 0) + s.get("rush_td", 0) + s.get("rec_td", 0)
    s["fpts_standard"] = _fp(s, "standard")
    s["fpts_half_ppr"] = _fp(s, "half_ppr")
    s["fpts_ppr"] = _fp(s, "ppr")
    s["fpts_per_game_standard"] = round(s["fpts_standard"] / max(games, 1), 2)
    s["fpts_per_game_half_ppr"] = round(s["fpts_half_ppr"] / max(games, 1), 2)
    s["fpts_per_game_ppr"] = round(s["fpts_ppr"] / max(games, 1), 2)
    return s


def _player(name, pos, team, age, exp, seasons, news=None, tag=None, headshot=None):
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "position": pos,
        "team": team,
        "age": age,
        "experience": exp,
        "headshot": headshot or "",
        "tag": tag,
        "seasons": [_enrich_season({**s}) for s in seasons],
        "news": news or [],
    }


def _news(date, headline, snippet, source, sentiment="neutral", url=""):
    return {"date": date, "headline": headline, "snippet": snippet, "source": source, "sentiment": sentiment, "url": url}


PLAYERS = [
    # ===== QUARTERBACKS =====
    _player("Josh Allen", "QB", "BUF", 28, 7,
        [{"season": 2022, "games": 16, "pass_yds": 4283, "pass_td": 35, "pass_int": 14, "rush_yds": 762, "rush_td": 7, "fumbles_lost": 5},
         {"season": 2023, "games": 17, "pass_yds": 4306, "pass_td": 29, "pass_int": 18, "rush_yds": 524, "rush_td": 15, "fumbles_lost": 4},
         {"season": 2024, "games": 17, "pass_yds": 3731, "pass_td": 28, "pass_int": 6, "rush_yds": 531, "rush_td": 12, "fumbles_lost": 3}],
        news=[_news("2025-01-26", "Allen wins MVP after stellar 2024 campaign", "League's only player with 28+ pass TDs and 12+ rush TDs.", "ESPN", "positive")],
        tag="elite"),
    _player("Patrick Mahomes", "QB", "KC", 29, 8,
        [{"season": 2022, "games": 17, "pass_yds": 5250, "pass_td": 41, "pass_int": 12, "rush_yds": 358, "rush_td": 4, "fumbles_lost": 3},
         {"season": 2023, "games": 16, "pass_yds": 4183, "pass_td": 27, "pass_int": 14, "rush_yds": 389, "rush_td": 0, "fumbles_lost": 2},
         {"season": 2024, "games": 16, "pass_yds": 3928, "pass_td": 26, "pass_int": 11, "rush_yds": 307, "rush_td": 2, "fumbles_lost": 4}],
        news=[_news("2024-12-12", "Mahomes adjusts to revamped WR room", "New deep threats reshape KC offensive identity.", "NFL.com", "positive")]),
    _player("Lamar Jackson", "QB", "BAL", 28, 7,
        [{"season": 2022, "games": 12, "pass_yds": 2242, "pass_td": 17, "pass_int": 7, "rush_yds": 764, "rush_td": 3, "fumbles_lost": 4},
         {"season": 2023, "games": 16, "pass_yds": 3678, "pass_td": 24, "pass_int": 7, "rush_yds": 821, "rush_td": 5, "fumbles_lost": 2},
         {"season": 2024, "games": 17, "pass_yds": 4172, "pass_td": 41, "pass_int": 4, "rush_yds": 915, "rush_td": 4, "fumbles_lost": 4}],
        tag="elite"),
    _player("Jalen Hurts", "QB", "PHI", 26, 5,
        [{"season": 2022, "games": 15, "pass_yds": 3701, "pass_td": 22, "pass_int": 6, "rush_yds": 760, "rush_td": 13, "fumbles_lost": 4},
         {"season": 2023, "games": 17, "pass_yds": 3858, "pass_td": 23, "pass_int": 15, "rush_yds": 605, "rush_td": 15, "fumbles_lost": 5},
         {"season": 2024, "games": 15, "pass_yds": 2903, "pass_td": 18, "pass_int": 5, "rush_yds": 630, "rush_td": 14, "fumbles_lost": 4}]),
    _player("Joe Burrow", "QB", "CIN", 28, 5,
        [{"season": 2022, "games": 16, "pass_yds": 4475, "pass_td": 35, "pass_int": 12, "rush_yds": 257, "rush_td": 5, "fumbles_lost": 5},
         {"season": 2023, "games": 10, "pass_yds": 2309, "pass_td": 15, "pass_int": 6, "rush_yds": 117, "rush_td": 1, "fumbles_lost": 2},
         {"season": 2024, "games": 17, "pass_yds": 4918, "pass_td": 43, "pass_int": 9, "rush_yds": 201, "rush_td": 2, "fumbles_lost": 3}]),
    _player("Jayden Daniels", "QB", "WAS", 24, 1,
        [{"season": 2024, "games": 17, "pass_yds": 3568, "pass_td": 25, "pass_int": 9, "rush_yds": 891, "rush_td": 6, "fumbles_lost": 3}],
        news=[_news("2025-01-18", "Daniels named Offensive Rookie of the Year", "Dual-threat phenom changes WAS outlook for years.", "ESPN", "positive")],
        tag="breakout"),
    _player("C.J. Stroud", "QB", "HOU", 23, 2,
        [{"season": 2023, "games": 15, "pass_yds": 4108, "pass_td": 23, "pass_int": 5, "rush_yds": 167, "rush_td": 3, "fumbles_lost": 1},
         {"season": 2024, "games": 17, "pass_yds": 3727, "pass_td": 20, "pass_int": 12, "rush_yds": 220, "rush_td": 1, "fumbles_lost": 2}]),
    _player("Dak Prescott", "QB", "DAL", 31, 9,
        [{"season": 2022, "games": 12, "pass_yds": 2860, "pass_td": 23, "pass_int": 15, "rush_yds": 182, "rush_td": 6, "fumbles_lost": 0},
         {"season": 2023, "games": 17, "pass_yds": 4516, "pass_td": 36, "pass_int": 9, "rush_yds": 242, "rush_td": 2, "fumbles_lost": 4},
         {"season": 2024, "games": 8, "pass_yds": 1978, "pass_td": 11, "pass_int": 8, "rush_yds": 47, "rush_td": 1, "fumbles_lost": 1}]),
    _player("Justin Herbert", "QB", "LAC", 27, 5,
        [{"season": 2022, "games": 17, "pass_yds": 4739, "pass_td": 25, "pass_int": 10, "rush_yds": 147, "rush_td": 0, "fumbles_lost": 3},
         {"season": 2023, "games": 13, "pass_yds": 3134, "pass_td": 20, "pass_int": 7, "rush_yds": 228, "rush_td": 3, "fumbles_lost": 2},
         {"season": 2024, "games": 17, "pass_yds": 3870, "pass_td": 23, "pass_int": 3, "rush_yds": 306, "rush_td": 2, "fumbles_lost": 3}]),
    _player("Jared Goff", "QB", "DET", 30, 9,
        [{"season": 2022, "games": 17, "pass_yds": 4438, "pass_td": 29, "pass_int": 7, "rush_yds": 33, "rush_td": 0, "fumbles_lost": 1},
         {"season": 2023, "games": 17, "pass_yds": 4575, "pass_td": 30, "pass_int": 12, "rush_yds": 21, "rush_td": 1, "fumbles_lost": 1},
         {"season": 2024, "games": 17, "pass_yds": 4629, "pass_td": 37, "pass_int": 12, "rush_yds": -7, "rush_td": 0, "fumbles_lost": 4}]),
    _player("Baker Mayfield", "QB", "TB", 30, 7,
        [{"season": 2023, "games": 17, "pass_yds": 4044, "pass_td": 28, "pass_int": 10, "rush_yds": 163, "rush_td": 1, "fumbles_lost": 4},
         {"season": 2024, "games": 17, "pass_yds": 4500, "pass_td": 41, "pass_int": 16, "rush_yds": 378, "rush_td": 3, "fumbles_lost": 7}]),
    _player("Kyler Murray", "QB", "ARI", 27, 6,
        [{"season": 2023, "games": 8, "pass_yds": 1799, "pass_td": 10, "pass_int": 5, "rush_yds": 244, "rush_td": 3, "fumbles_lost": 0},
         {"season": 2024, "games": 17, "pass_yds": 3851, "pass_td": 21, "pass_int": 11, "rush_yds": 572, "rush_td": 5, "fumbles_lost": 3}]),
    _player("Brock Purdy", "QB", "SF", 25, 3,
        [{"season": 2023, "games": 16, "pass_yds": 4280, "pass_td": 31, "pass_int": 11, "rush_yds": 144, "rush_td": 2, "fumbles_lost": 3},
         {"season": 2024, "games": 15, "pass_yds": 3864, "pass_td": 20, "pass_int": 12, "rush_yds": 323, "rush_td": 5, "fumbles_lost": 4}]),
    _player("Bo Nix", "QB", "DEN", 25, 1,
        [{"season": 2024, "games": 17, "pass_yds": 3775, "pass_td": 29, "pass_int": 12, "rush_yds": 430, "rush_td": 4, "fumbles_lost": 3}],
        tag="sleeper"),
    _player("Caleb Williams", "QB", "CHI", 23, 1,
        [{"season": 2024, "games": 17, "pass_yds": 3541, "pass_td": 20, "pass_int": 6, "rush_yds": 489, "rush_td": 0, "fumbles_lost": 6}]),

    # ===== RUNNING BACKS =====
    _player("Christian McCaffrey", "RB", "SF", 28, 8,
        [{"season": 2022, "games": 17, "rush_yds": 1139, "rush_td": 8, "receptions": 85, "rec_yds": 741, "rec_td": 5, "fumbles_lost": 1},
         {"season": 2023, "games": 16, "rush_yds": 1459, "rush_td": 14, "receptions": 67, "rec_yds": 564, "rec_td": 7, "fumbles_lost": 2},
         {"season": 2024, "games": 4, "rush_yds": 202, "rush_td": 0, "receptions": 15, "rec_yds": 146, "rec_td": 0, "fumbles_lost": 1}],
        news=[_news("2024-11-08", "McCaffrey suffers Achilles tendinitis setback", "Limited 2024 raises questions about workhorse role going forward.", "NFL.com", "negative")],
        tag="risk"),
    _player("Saquon Barkley", "RB", "PHI", 28, 7,
        [{"season": 2022, "games": 16, "rush_yds": 1312, "rush_td": 10, "receptions": 57, "rec_yds": 338, "rec_td": 0, "fumbles_lost": 3},
         {"season": 2023, "games": 14, "rush_yds": 962, "rush_td": 6, "receptions": 41, "rec_yds": 280, "rec_td": 4, "fumbles_lost": 0},
         {"season": 2024, "games": 16, "rush_yds": 2005, "rush_td": 13, "receptions": 33, "rec_yds": 278, "rec_td": 2, "fumbles_lost": 1}],
        news=[_news("2025-01-04", "Barkley becomes 9th player ever to rush for 2,000 yards", "Eagles' line + scheme produced career year.", "ESPN", "positive")],
        tag="elite"),
    _player("Derrick Henry", "RB", "BAL", 31, 9,
        [{"season": 2022, "games": 16, "rush_yds": 1538, "rush_td": 13, "receptions": 33, "rec_yds": 398, "rec_td": 0, "fumbles_lost": 1},
         {"season": 2023, "games": 17, "rush_yds": 1167, "rush_td": 12, "receptions": 28, "rec_yds": 214, "rec_td": 0, "fumbles_lost": 2},
         {"season": 2024, "games": 17, "rush_yds": 1921, "rush_td": 16, "receptions": 19, "rec_yds": 193, "rec_td": 2, "fumbles_lost": 2}],
        news=[_news("2024-09-15", "Henry thrives in BAL's new run-heavy scheme", "Pairing with Lamar gives DET-level run game.", "ESPN", "positive")]),
    _player("Bijan Robinson", "RB", "ATL", 23, 2,
        [{"season": 2023, "games": 17, "rush_yds": 976, "rush_td": 4, "receptions": 58, "rec_yds": 487, "rec_td": 4, "fumbles_lost": 1},
         {"season": 2024, "games": 17, "rush_yds": 1456, "rush_td": 14, "receptions": 61, "rec_yds": 431, "rec_td": 1, "fumbles_lost": 2}],
        tag="elite"),
    _player("Jahmyr Gibbs", "RB", "DET", 23, 2,
        [{"season": 2023, "games": 15, "rush_yds": 945, "rush_td": 10, "receptions": 52, "rec_yds": 316, "rec_td": 1, "fumbles_lost": 2},
         {"season": 2024, "games": 17, "rush_yds": 1412, "rush_td": 16, "receptions": 52, "rec_yds": 517, "rec_td": 4, "fumbles_lost": 0}]),
    _player("Jonathan Taylor", "RB", "IND", 26, 5,
        [{"season": 2022, "games": 11, "rush_yds": 861, "rush_td": 4, "receptions": 28, "rec_yds": 197, "rec_td": 0, "fumbles_lost": 2},
         {"season": 2023, "games": 10, "rush_yds": 741, "rush_td": 7, "receptions": 19, "rec_yds": 153, "rec_td": 1, "fumbles_lost": 2},
         {"season": 2024, "games": 14, "rush_yds": 1431, "rush_td": 11, "receptions": 18, "rec_yds": 136, "rec_td": 1, "fumbles_lost": 1}]),
    _player("Josh Jacobs", "RB", "GB", 27, 6,
        [{"season": 2022, "games": 17, "rush_yds": 1653, "rush_td": 12, "receptions": 53, "rec_yds": 400, "rec_td": 0, "fumbles_lost": 1},
         {"season": 2023, "games": 13, "rush_yds": 805, "rush_td": 6, "receptions": 37, "rec_yds": 296, "rec_td": 0, "fumbles_lost": 4},
         {"season": 2024, "games": 16, "rush_yds": 1329, "rush_td": 15, "receptions": 36, "rec_yds": 342, "rec_td": 1, "fumbles_lost": 2}]),
    _player("Kyren Williams", "RB", "LAR", 24, 3,
        [{"season": 2023, "games": 12, "rush_yds": 1144, "rush_td": 12, "receptions": 32, "rec_yds": 206, "rec_td": 3, "fumbles_lost": 1},
         {"season": 2024, "games": 16, "rush_yds": 1299, "rush_td": 14, "receptions": 34, "rec_yds": 182, "rec_td": 0, "fumbles_lost": 5}]),
    _player("De'Von Achane", "RB", "MIA", 23, 2,
        [{"season": 2023, "games": 11, "rush_yds": 800, "rush_td": 8, "receptions": 27, "rec_yds": 197, "rec_td": 3, "fumbles_lost": 1},
         {"season": 2024, "games": 17, "rush_yds": 907, "rush_td": 6, "receptions": 78, "rec_yds": 592, "rec_td": 1, "fumbles_lost": 1}]),
    _player("Joe Mixon", "RB", "HOU", 28, 8,
        [{"season": 2023, "games": 14, "rush_yds": 1034, "rush_td": 9, "receptions": 52, "rec_yds": 376, "rec_td": 3, "fumbles_lost": 0},
         {"season": 2024, "games": 14, "rush_yds": 1016, "rush_td": 11, "receptions": 36, "rec_yds": 309, "rec_td": 1, "fumbles_lost": 1}]),
    _player("Alvin Kamara", "RB", "NO", 29, 8,
        [{"season": 2022, "games": 15, "rush_yds": 897, "rush_td": 4, "receptions": 57, "rec_yds": 490, "rec_td": 2, "fumbles_lost": 2},
         {"season": 2023, "games": 13, "rush_yds": 694, "rush_td": 5, "receptions": 75, "rec_yds": 466, "rec_td": 1, "fumbles_lost": 0},
         {"season": 2024, "games": 14, "rush_yds": 950, "rush_td": 6, "receptions": 68, "rec_yds": 543, "rec_td": 2, "fumbles_lost": 2}]),
    _player("James Cook", "RB", "BUF", 25, 3,
        [{"season": 2023, "games": 16, "rush_yds": 1122, "rush_td": 2, "receptions": 44, "rec_yds": 445, "rec_td": 4, "fumbles_lost": 1},
         {"season": 2024, "games": 16, "rush_yds": 1009, "rush_td": 16, "receptions": 32, "rec_yds": 258, "rec_td": 2, "fumbles_lost": 1}]),
    _player("Breece Hall", "RB", "NYJ", 24, 3,
        [{"season": 2022, "games": 7, "rush_yds": 463, "rush_td": 4, "receptions": 19, "rec_yds": 218, "rec_td": 1, "fumbles_lost": 1},
         {"season": 2023, "games": 17, "rush_yds": 994, "rush_td": 5, "receptions": 76, "rec_yds": 591, "rec_td": 4, "fumbles_lost": 2},
         {"season": 2024, "games": 16, "rush_yds": 876, "rush_td": 5, "receptions": 57, "rec_yds": 483, "rec_td": 3, "fumbles_lost": 0}]),
    _player("Aaron Jones", "RB", "MIN", 30, 8,
        [{"season": 2023, "games": 11, "rush_yds": 656, "rush_td": 2, "receptions": 30, "rec_yds": 233, "rec_td": 1, "fumbles_lost": 2},
         {"season": 2024, "games": 17, "rush_yds": 1138, "rush_td": 5, "receptions": 51, "rec_yds": 408, "rec_td": 2, "fumbles_lost": 4}]),
    _player("Chuba Hubbard", "RB", "CAR", 25, 4,
        [{"season": 2023, "games": 15, "rush_yds": 902, "rush_td": 5, "receptions": 25, "rec_yds": 233, "rec_td": 1, "fumbles_lost": 0},
         {"season": 2024, "games": 15, "rush_yds": 1195, "rush_td": 10, "receptions": 43, "rec_yds": 171, "rec_td": 1, "fumbles_lost": 2}],
        tag="sleeper"),
    _player("Bucky Irving", "RB", "TB", 22, 1,
        [{"season": 2024, "games": 17, "rush_yds": 1122, "rush_td": 8, "receptions": 47, "rec_yds": 392, "rec_td": 0, "fumbles_lost": 0}],
        tag="breakout"),
    _player("D'Andre Swift", "RB", "CHI", 26, 5,
        [{"season": 2023, "games": 16, "rush_yds": 1049, "rush_td": 5, "receptions": 39, "rec_yds": 214, "rec_td": 1, "fumbles_lost": 0},
         {"season": 2024, "games": 17, "rush_yds": 959, "rush_td": 6, "receptions": 42, "rec_yds": 386, "rec_td": 0, "fumbles_lost": 2}]),
    _player("Najee Harris", "RB", "PIT", 26, 4,
        [{"season": 2023, "games": 17, "rush_yds": 1035, "rush_td": 8, "receptions": 29, "rec_yds": 170, "rec_td": 1, "fumbles_lost": 1},
         {"season": 2024, "games": 17, "rush_yds": 1043, "rush_td": 6, "receptions": 36, "rec_yds": 283, "rec_td": 0, "fumbles_lost": 0}]),
    _player("Tony Pollard", "RB", "TEN", 27, 6,
        [{"season": 2023, "games": 17, "rush_yds": 1005, "rush_td": 6, "receptions": 55, "rec_yds": 311, "rec_td": 0, "fumbles_lost": 1},
         {"season": 2024, "games": 16, "rush_yds": 1079, "rush_td": 5, "receptions": 41, "rec_yds": 238, "rec_td": 0, "fumbles_lost": 1}]),

    # ===== WIDE RECEIVERS =====
    _player("Justin Jefferson", "WR", "MIN", 25, 5,
        [{"season": 2022, "games": 17, "receptions": 128, "rec_yds": 1809, "rec_td": 8, "fumbles_lost": 0},
         {"season": 2023, "games": 10, "receptions": 68, "rec_yds": 1074, "rec_td": 5, "fumbles_lost": 1},
         {"season": 2024, "games": 17, "receptions": 103, "rec_yds": 1533, "rec_td": 10, "fumbles_lost": 1}],
        tag="elite"),
    _player("Ja'Marr Chase", "WR", "CIN", 25, 4,
        [{"season": 2022, "games": 12, "receptions": 87, "rec_yds": 1046, "rec_td": 9, "fumbles_lost": 1},
         {"season": 2023, "games": 16, "receptions": 100, "rec_yds": 1216, "rec_td": 7, "fumbles_lost": 1},
         {"season": 2024, "games": 17, "receptions": 127, "rec_yds": 1708, "rec_td": 17, "fumbles_lost": 0}],
        news=[_news("2025-01-05", "Chase wins triple crown: receptions, yards, TDs", "First WR triple crown since 2005.", "ESPN", "positive")],
        tag="elite"),
    _player("CeeDee Lamb", "WR", "DAL", 25, 5,
        [{"season": 2022, "games": 17, "receptions": 107, "rec_yds": 1359, "rec_td": 9, "fumbles_lost": 1},
         {"season": 2023, "games": 17, "receptions": 135, "rec_yds": 1749, "rec_td": 12, "fumbles_lost": 0},
         {"season": 2024, "games": 15, "receptions": 101, "rec_yds": 1194, "rec_td": 6, "fumbles_lost": 0}]),
    _player("Tyreek Hill", "WR", "MIA", 30, 9,
        [{"season": 2022, "games": 17, "receptions": 119, "rec_yds": 1710, "rec_td": 7, "fumbles_lost": 0},
         {"season": 2023, "games": 16, "receptions": 119, "rec_yds": 1799, "rec_td": 13, "fumbles_lost": 0},
         {"season": 2024, "games": 17, "receptions": 81, "rec_yds": 959, "rec_td": 6, "fumbles_lost": 1}],
        news=[_news("2024-12-30", "Hill expresses frustration with MIA offense", "Offseason departure rumors raise outlook concerns.", "ESPN", "negative")],
        tag="risk"),
    _player("Amon-Ra St. Brown", "WR", "DET", 25, 4,
        [{"season": 2022, "games": 16, "receptions": 106, "rec_yds": 1161, "rec_td": 6, "fumbles_lost": 0},
         {"season": 2023, "games": 16, "receptions": 119, "rec_yds": 1515, "rec_td": 10, "fumbles_lost": 0},
         {"season": 2024, "games": 17, "receptions": 115, "rec_yds": 1263, "rec_td": 12, "fumbles_lost": 0}]),
    _player("Puka Nacua", "WR", "LAR", 24, 2,
        [{"season": 2023, "games": 17, "receptions": 105, "rec_yds": 1486, "rec_td": 6, "fumbles_lost": 0},
         {"season": 2024, "games": 11, "receptions": 79, "rec_yds": 990, "rec_td": 3, "fumbles_lost": 0}]),
    _player("Davante Adams", "WR", "NYJ", 32, 11,
        [{"season": 2022, "games": 17, "receptions": 100, "rec_yds": 1516, "rec_td": 14, "fumbles_lost": 0},
         {"season": 2023, "games": 17, "receptions": 103, "rec_yds": 1144, "rec_td": 8, "fumbles_lost": 1},
         {"season": 2024, "games": 14, "receptions": 85, "rec_yds": 1063, "rec_td": 8, "fumbles_lost": 0}]),
    _player("Mike Evans", "WR", "TB", 31, 11,
        [{"season": 2022, "games": 15, "receptions": 77, "rec_yds": 1124, "rec_td": 6, "fumbles_lost": 0},
         {"season": 2023, "games": 17, "receptions": 79, "rec_yds": 1255, "rec_td": 13, "fumbles_lost": 0},
         {"season": 2024, "games": 14, "receptions": 74, "rec_yds": 1004, "rec_td": 11, "fumbles_lost": 0}]),
    _player("A.J. Brown", "WR", "PHI", 27, 6,
        [{"season": 2022, "games": 17, "receptions": 88, "rec_yds": 1496, "rec_td": 11, "fumbles_lost": 0},
         {"season": 2023, "games": 17, "receptions": 106, "rec_yds": 1456, "rec_td": 7, "fumbles_lost": 0},
         {"season": 2024, "games": 13, "receptions": 67, "rec_yds": 1079, "rec_td": 7, "fumbles_lost": 0}]),
    _player("Drake London", "WR", "ATL", 23, 3,
        [{"season": 2023, "games": 16, "receptions": 69, "rec_yds": 905, "rec_td": 2, "fumbles_lost": 0},
         {"season": 2024, "games": 17, "receptions": 100, "rec_yds": 1271, "rec_td": 9, "fumbles_lost": 0}],
        tag="breakout"),
    _player("Brian Thomas Jr.", "WR", "JAX", 22, 1,
        [{"season": 2024, "games": 17, "receptions": 87, "rec_yds": 1282, "rec_td": 10, "fumbles_lost": 0}],
        tag="breakout"),
    _player("Malik Nabers", "WR", "NYG", 21, 1,
        [{"season": 2024, "games": 15, "receptions": 109, "rec_yds": 1204, "rec_td": 7, "fumbles_lost": 1}],
        news=[_news("2025-01-12", "Nabers' QB situation murky entering year 2", "WR's outlook hinges on NYG QB plan.", "NFL.com", "neutral")],
        tag="breakout"),
    _player("Garrett Wilson", "WR", "NYJ", 24, 3,
        [{"season": 2022, "games": 17, "receptions": 83, "rec_yds": 1103, "rec_td": 4, "fumbles_lost": 0},
         {"season": 2023, "games": 17, "receptions": 95, "rec_yds": 1042, "rec_td": 3, "fumbles_lost": 0},
         {"season": 2024, "games": 17, "receptions": 101, "rec_yds": 1104, "rec_td": 7, "fumbles_lost": 0}]),
    _player("Nico Collins", "WR", "HOU", 26, 4,
        [{"season": 2023, "games": 15, "receptions": 80, "rec_yds": 1297, "rec_td": 8, "fumbles_lost": 0},
         {"season": 2024, "games": 12, "receptions": 68, "rec_yds": 1006, "rec_td": 7, "fumbles_lost": 0}]),
    _player("DK Metcalf", "WR", "SEA", 27, 6,
        [{"season": 2022, "games": 17, "receptions": 90, "rec_yds": 1048, "rec_td": 6, "fumbles_lost": 0},
         {"season": 2023, "games": 16, "receptions": 66, "rec_yds": 1114, "rec_td": 8, "fumbles_lost": 1},
         {"season": 2024, "games": 15, "receptions": 66, "rec_yds": 992, "rec_td": 5, "fumbles_lost": 0}]),
    _player("Stefon Diggs", "WR", "HOU", 31, 10,
        [{"season": 2022, "games": 17, "receptions": 108, "rec_yds": 1429, "rec_td": 11, "fumbles_lost": 0},
         {"season": 2023, "games": 17, "receptions": 107, "rec_yds": 1183, "rec_td": 8, "fumbles_lost": 0},
         {"season": 2024, "games": 8, "receptions": 47, "rec_yds": 496, "rec_td": 3, "fumbles_lost": 0}],
        news=[_news("2024-10-30", "Diggs torn ACL ends season early", "Long recovery raises bust risk for 2025.", "NFL.com", "negative")],
        tag="risk"),
    _player("Terry McLaurin", "WR", "WAS", 29, 6,
        [{"season": 2023, "games": 17, "receptions": 79, "rec_yds": 1002, "rec_td": 4, "fumbles_lost": 0},
         {"season": 2024, "games": 17, "receptions": 82, "rec_yds": 1096, "rec_td": 13, "fumbles_lost": 0}]),
    _player("Jaxon Smith-Njigba", "WR", "SEA", 23, 2,
        [{"season": 2023, "games": 17, "receptions": 63, "rec_yds": 628, "rec_td": 4, "fumbles_lost": 0},
         {"season": 2024, "games": 17, "receptions": 100, "rec_yds": 1130, "rec_td": 6, "fumbles_lost": 1}],
        tag="breakout"),
    _player("Ladd McConkey", "WR", "LAC", 23, 1,
        [{"season": 2024, "games": 16, "receptions": 82, "rec_yds": 1149, "rec_td": 7, "fumbles_lost": 0}],
        tag="breakout"),
    _player("Cooper Kupp", "WR", "LAR", 31, 8,
        [{"season": 2022, "games": 9, "receptions": 75, "rec_yds": 812, "rec_td": 6, "fumbles_lost": 0},
         {"season": 2023, "games": 12, "receptions": 59, "rec_yds": 737, "rec_td": 5, "fumbles_lost": 1},
         {"season": 2024, "games": 12, "receptions": 67, "rec_yds": 710, "rec_td": 6, "fumbles_lost": 1}],
        tag="risk"),
    _player("DeVonta Smith", "WR", "PHI", 26, 4,
        [{"season": 2023, "games": 17, "receptions": 81, "rec_yds": 1066, "rec_td": 7, "fumbles_lost": 0},
         {"season": 2024, "games": 13, "receptions": 68, "rec_yds": 833, "rec_td": 8, "fumbles_lost": 0}]),
    _player("Calvin Ridley", "WR", "TEN", 30, 6,
        [{"season": 2023, "games": 17, "receptions": 76, "rec_yds": 1016, "rec_td": 8, "fumbles_lost": 0},
         {"season": 2024, "games": 17, "receptions": 64, "rec_yds": 1017, "rec_td": 4, "fumbles_lost": 1}]),
    _player("Tee Higgins", "WR", "CIN", 26, 5,
        [{"season": 2022, "games": 16, "receptions": 74, "rec_yds": 1029, "rec_td": 7, "fumbles_lost": 0},
         {"season": 2023, "games": 12, "receptions": 42, "rec_yds": 656, "rec_td": 5, "fumbles_lost": 0},
         {"season": 2024, "games": 12, "receptions": 73, "rec_yds": 911, "rec_td": 10, "fumbles_lost": 0}]),
    _player("DJ Moore", "WR", "CHI", 28, 7,
        [{"season": 2023, "games": 17, "receptions": 96, "rec_yds": 1364, "rec_td": 8, "fumbles_lost": 1},
         {"season": 2024, "games": 17, "receptions": 98, "rec_yds": 966, "rec_td": 6, "fumbles_lost": 0}]),
    _player("Courtland Sutton", "WR", "DEN", 29, 7,
        [{"season": 2023, "games": 16, "receptions": 59, "rec_yds": 772, "rec_td": 10, "fumbles_lost": 0},
         {"season": 2024, "games": 17, "receptions": 81, "rec_yds": 1081, "rec_td": 8, "fumbles_lost": 0}]),
    _player("Zay Flowers", "WR", "BAL", 24, 2,
        [{"season": 2023, "games": 16, "receptions": 77, "rec_yds": 858, "rec_td": 5, "fumbles_lost": 0},
         {"season": 2024, "games": 17, "receptions": 74, "rec_yds": 1059, "rec_td": 4, "fumbles_lost": 0}]),
    _player("Jameson Williams", "WR", "DET", 24, 3,
        [{"season": 2023, "games": 12, "receptions": 24, "rec_yds": 354, "rec_td": 2, "fumbles_lost": 0},
         {"season": 2024, "games": 15, "receptions": 58, "rec_yds": 1001, "rec_td": 7, "fumbles_lost": 0}],
        tag="sleeper"),

    # ===== TIGHT ENDS =====
    _player("Travis Kelce", "TE", "KC", 35, 12,
        [{"season": 2022, "games": 17, "receptions": 110, "rec_yds": 1338, "rec_td": 12, "fumbles_lost": 0},
         {"season": 2023, "games": 15, "receptions": 93, "rec_yds": 984, "rec_td": 5, "fumbles_lost": 0},
         {"season": 2024, "games": 17, "receptions": 97, "rec_yds": 823, "rec_td": 3, "fumbles_lost": 0}],
        tag="risk"),
    _player("Sam LaPorta", "TE", "DET", 24, 2,
        [{"season": 2023, "games": 17, "receptions": 86, "rec_yds": 889, "rec_td": 10, "fumbles_lost": 0},
         {"season": 2024, "games": 16, "receptions": 60, "rec_yds": 726, "rec_td": 7, "fumbles_lost": 0}]),
    _player("Trey McBride", "TE", "ARI", 25, 3,
        [{"season": 2023, "games": 17, "receptions": 81, "rec_yds": 825, "rec_td": 3, "fumbles_lost": 0},
         {"season": 2024, "games": 16, "receptions": 111, "rec_yds": 1146, "rec_td": 2, "fumbles_lost": 0}],
        tag="elite"),
    _player("George Kittle", "TE", "SF", 31, 8,
        [{"season": 2022, "games": 15, "receptions": 60, "rec_yds": 765, "rec_td": 11, "fumbles_lost": 1},
         {"season": 2023, "games": 16, "receptions": 65, "rec_yds": 1020, "rec_td": 6, "fumbles_lost": 0},
         {"season": 2024, "games": 15, "receptions": 78, "rec_yds": 1106, "rec_td": 8, "fumbles_lost": 0}]),
    _player("Brock Bowers", "TE", "LV", 22, 1,
        [{"season": 2024, "games": 17, "receptions": 112, "rec_yds": 1194, "rec_td": 5, "fumbles_lost": 0}],
        tag="breakout"),
    _player("Mark Andrews", "TE", "BAL", 29, 7,
        [{"season": 2022, "games": 15, "receptions": 73, "rec_yds": 847, "rec_td": 5, "fumbles_lost": 1},
         {"season": 2023, "games": 10, "receptions": 45, "rec_yds": 544, "rec_td": 6, "fumbles_lost": 0},
         {"season": 2024, "games": 17, "receptions": 55, "rec_yds": 673, "rec_td": 11, "fumbles_lost": 1}]),
    _player("T.J. Hockenson", "TE", "MIN", 28, 6,
        [{"season": 2022, "games": 17, "receptions": 86, "rec_yds": 914, "rec_td": 6, "fumbles_lost": 0},
         {"season": 2023, "games": 15, "receptions": 95, "rec_yds": 960, "rec_td": 5, "fumbles_lost": 0},
         {"season": 2024, "games": 10, "receptions": 41, "rec_yds": 455, "rec_td": 0, "fumbles_lost": 0}]),
    _player("Jonnu Smith", "TE", "MIA", 29, 8,
        [{"season": 2024, "games": 17, "receptions": 88, "rec_yds": 884, "rec_td": 8, "fumbles_lost": 1}],
        tag="sleeper"),
    _player("Evan Engram", "TE", "JAX", 30, 8,
        [{"season": 2023, "games": 17, "receptions": 114, "rec_yds": 963, "rec_td": 4, "fumbles_lost": 0},
         {"season": 2024, "games": 9, "receptions": 47, "rec_yds": 365, "rec_td": 1, "fumbles_lost": 0}]),
    _player("David Njoku", "TE", "CLE", 28, 8,
        [{"season": 2023, "games": 16, "receptions": 81, "rec_yds": 882, "rec_td": 6, "fumbles_lost": 0},
         {"season": 2024, "games": 11, "receptions": 64, "rec_yds": 505, "rec_td": 5, "fumbles_lost": 1}]),
]


async def populate_db(db):
    existing = await db.players.count_documents({})
    if existing > 0:
        return existing
    for p in PLAYERS:
        p["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.players.insert_many(PLAYERS)
    return len(PLAYERS)
