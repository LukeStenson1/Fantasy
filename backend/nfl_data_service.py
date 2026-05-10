"""Pull real NFL seasonal data via nfl-data-py (nflverse).

Strategy:
- On first refresh, pull seasonal stats + roster for available seasons (2022-2025).
- 2025 rookies pulled from rosters even when 2025 seasonal stats not yet published.
- Real schedules pulled — next opponent computed from upcoming REG games.
- Compute fantasy points (standard, half-PPR, PPR).
- Filter to fantasy-relevant positions (QB, RB, WR, TE, K) with min thresholds.
- Tag breakouts/sleepers/risks heuristically from stats trajectory.
- Re-runs cheaply if `force=False` and players collection is fresh (<24h).

When 2025/2026 seasonal stats become available in nflverse, refresh picks them up automatically.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Iterable

logger = logging.getLogger("ffref.data")

# Positions we care about for fantasy
FANTASY_POSITIONS = {"QB", "RB", "WR", "TE", "K"}

# Per-position player count caps (top-N by fantasy points in latest season)
TOP_N = {"QB": 32, "RB": 75, "WR": 75, "TE": 35, "K": 35}

# 32 NFL team defenses for fantasy lineup support
NFL_TEAMS = [
    ("ARI", "Arizona Cardinals"), ("ATL", "Atlanta Falcons"), ("BAL", "Baltimore Ravens"),
    ("BUF", "Buffalo Bills"), ("CAR", "Carolina Panthers"), ("CHI", "Chicago Bears"),
    ("CIN", "Cincinnati Bengals"), ("CLE", "Cleveland Browns"), ("DAL", "Dallas Cowboys"),
    ("DEN", "Denver Broncos"), ("DET", "Detroit Lions"), ("GB", "Green Bay Packers"),
    ("HOU", "Houston Texans"), ("IND", "Indianapolis Colts"), ("JAX", "Jacksonville Jaguars"),
    ("KC", "Kansas City Chiefs"), ("LAC", "Los Angeles Chargers"), ("LAR", "Los Angeles Rams"),
    ("LV", "Las Vegas Raiders"), ("MIA", "Miami Dolphins"), ("MIN", "Minnesota Vikings"),
    ("NE", "New England Patriots"), ("NO", "New Orleans Saints"), ("NYG", "New York Giants"),
    ("NYJ", "New York Jets"), ("PHI", "Philadelphia Eagles"), ("PIT", "Pittsburgh Steelers"),
    ("SEA", "Seattle Seahawks"), ("SF", "San Francisco 49ers"), ("TB", "Tampa Bay Buccaneers"),
    ("TEN", "Tennessee Titans"), ("WAS", "Washington Commanders"),
]


def _compute_fp(row, scoring: str) -> float:
    """Compute half-PPR / PPR / standard fantasy points from seasonal row."""
    pts = 0.0
    pts += (row.get("passing_yards", 0) or 0) / 25.0
    pts += (row.get("passing_tds", 0) or 0) * 4
    pts -= (row.get("interceptions", 0) or 0) * 2
    pts += (row.get("rushing_yards", 0) or 0) / 10.0
    pts += (row.get("rushing_tds", 0) or 0) * 6
    pts += (row.get("receiving_yards", 0) or 0) / 10.0
    pts += (row.get("receiving_tds", 0) or 0) * 6
    rec = row.get("receptions", 0) or 0
    if scoring == "ppr":
        pts += rec * 1.0
    elif scoring == "half_ppr":
        pts += rec * 0.5
    fumbles_lost = (row.get("rushing_fumbles_lost", 0) or 0) + (row.get("receiving_fumbles_lost", 0) or 0) + (row.get("sack_fumbles_lost", 0) or 0)
    pts -= fumbles_lost * 2
    return round(pts, 2)


def _season_record(row, season: int) -> dict:
    """Build a season stat dict for storage."""
    games = int(row.get("games", 0) or 0)
    rec = {
        "season": season,
        "games": games,
        "pass_yds": int(row.get("passing_yards", 0) or 0),
        "pass_td": int(row.get("passing_tds", 0) or 0),
        "pass_int": int(row.get("interceptions", 0) or 0),
        "rush_yds": int(row.get("rushing_yards", 0) or 0),
        "rush_td": int(row.get("rushing_tds", 0) or 0),
        "rush_att": int(row.get("carries", 0) or 0),
        "receptions": int(row.get("receptions", 0) or 0),
        "targets": int(row.get("targets", 0) or 0),
        "rec_yds": int(row.get("receiving_yards", 0) or 0),
        "rec_td": int(row.get("receiving_tds", 0) or 0),
        "fumbles_lost": int(
            (row.get("rushing_fumbles_lost", 0) or 0)
            + (row.get("receiving_fumbles_lost", 0) or 0)
            + (row.get("sack_fumbles_lost", 0) or 0)
        ),
    }
    rec["total_yards"] = rec["pass_yds"] + rec["rush_yds"] + rec["rec_yds"]
    rec["total_tds"] = rec["pass_td"] + rec["rush_td"] + rec["rec_td"]
    rec["fpts_standard"] = _compute_fp(row, "standard")
    rec["fpts_half_ppr"] = _compute_fp(row, "half_ppr")
    rec["fpts_ppr"] = _compute_fp(row, "ppr")
    rec["fpts_per_game_standard"] = round(rec["fpts_standard"] / max(games, 1), 2)
    rec["fpts_per_game_half_ppr"] = round(rec["fpts_half_ppr"] / max(games, 1), 2)
    rec["fpts_per_game_ppr"] = round(rec["fpts_ppr"] / max(games, 1), 2)
    return rec


def _detect_tag(seasons: list[dict], position: str) -> str | None:
    """Heuristic: tag elite/breakout/sleeper/risk based on trajectory."""
    if not seasons:
        return None
    seasons_sorted = sorted(seasons, key=lambda s: s["season"])
    latest = seasons_sorted[-1]
    fppg = latest.get("fpts_per_game_half_ppr", 0)
    games = latest.get("games", 0)

    elite_threshold = {"QB": 22, "RB": 17, "WR": 16, "TE": 13}.get(position, 99)
    breakout_threshold = {"QB": 19, "RB": 14, "WR": 13, "TE": 10}.get(position, 99)
    risk_games = 11

    if fppg >= elite_threshold and games >= 12:
        return "elite"

    # Breakout: latest year much better than prior, big jump
    if len(seasons_sorted) >= 2:
        prev = seasons_sorted[-2]
        if (
            fppg >= breakout_threshold
            and prev.get("fpts_per_game_half_ppr", 0) < breakout_threshold - 2
            and games >= 12
        ):
            return "breakout"

    # Risk: missed games
    if games > 0 and games < risk_games:
        return "risk"

    # Sleeper: solid fppg but not elite, low games or new season
    if fppg >= breakout_threshold - 3 and games <= 14 and len(seasons_sorted) <= 2:
        return "sleeper"

    return None


def _build_players_from_dataframes(seasonal_dfs: dict, roster_dfs: dict) -> list[dict]:
    """Merge seasonal stats with rosters, group by player, filter top players.
    Also surfaces 2025+ rookies (years_exp == 0) even if seasonal stats not yet published."""
    import pandas as pd

    all_player_seasons: dict[str, dict] = {}  # player_id -> {info, seasons[]}
    rookie_meta: dict[str, dict] = {}  # player_id -> rookie attrs

    for season, df in seasonal_dfs.items():
        if df is None or df.empty:
            continue
        roster = roster_dfs.get(season)
        if roster is None or roster.empty:
            continue
        # latest roster row per player_id
        roster_latest = roster.drop_duplicates(subset=["player_id"], keep="last")
        merged = df.merge(
            roster_latest[["player_id", "player_name", "position", "team", "birth_date"]],
            on="player_id", how="left",
        )
        merged = merged[merged["position"].isin(FANTASY_POSITIONS)]
        merged = merged[merged["games"].fillna(0) >= 1]
        for _, row in merged.iterrows():
            pid = row["player_id"]
            name = row.get("player_name")
            pos = row.get("position")
            team = row.get("team")
            if pd.isna(name) or pd.isna(pos):
                continue
            entry = all_player_seasons.setdefault(pid, {
                "ext_id": pid,
                "name": str(name),
                "position": str(pos),
                "team": str(team) if not pd.isna(team) else "",
                "birth_date": row.get("birth_date"),
                "seasons": [],
            })
            if not pd.isna(team):
                entry["team"] = str(team)
            entry["seasons"].append(_season_record(row, season))

    # ROOKIES: pull rookies (years_exp==0) from each season's roster — even when
    # seasonal stats aren't published yet (e.g., 2025 in early season, or pre-season).
    for season, roster in roster_dfs.items():
        if roster is None or roster.empty:
            continue
        if "years_exp" not in roster.columns:
            continue
        rookies = roster[(roster["years_exp"] == 0) & (roster["position"].isin(FANTASY_POSITIONS))]
        for _, row in rookies.iterrows():
            pid = row.get("player_id")
            if not pid or pd.isna(pid):
                continue
            rookie_meta[pid] = {
                "rookie_year": int(season),
                "draft_number": (None if pd.isna(row.get("draft_number")) else int(row.get("draft_number"))),
                "draft_club": (None if pd.isna(row.get("draft_club")) else str(row.get("draft_club"))),
                "college": (None if pd.isna(row.get("college")) else str(row.get("college"))),
            }
            # Ensure rookie is in our list even with 0 games
            if pid not in all_player_seasons:
                all_player_seasons[pid] = {
                    "ext_id": pid,
                    "name": str(row.get("player_name") or ""),
                    "position": str(row.get("position") or ""),
                    "team": str(row.get("team") or ""),
                    "birth_date": row.get("birth_date"),
                    "seasons": [],
                }

    # Filter to top-N per position based on best-of-any-season fpts.
    # Rookies (no seasons yet) included separately, ranked by inverse draft_number.
    per_position: dict[str, list[dict]] = {}
    rookies_with_no_seasons: list[dict] = []
    for entry in all_player_seasons.values():
        pos = entry["position"]
        if not entry["seasons"]:
            # Pure rookie — keep aside
            r = rookie_meta.get(entry["ext_id"])
            if r:
                entry["_rookie_score"] = -1 * (r.get("draft_number") or 999)
                rookies_with_no_seasons.append(entry)
            continue
        best = max((s.get("fpts_half_ppr", 0) for s in entry["seasons"]), default=0)
        entry["_latest_fpts"] = best
        per_position.setdefault(pos, []).append(entry)

    selected: list[dict] = []
    for pos, lst in per_position.items():
        cap = TOP_N.get(pos, 30)
        lst.sort(key=lambda e: e["_latest_fpts"], reverse=True)
        selected.extend(lst[:cap])

    # Add up to ~50 rookies (early-round draft picks) regardless of stats availability
    rookies_with_no_seasons.sort(key=lambda e: e.get("_rookie_score", -999), reverse=True)
    selected.extend(rookies_with_no_seasons[:60])

    # Build final docs
    today = datetime.now(timezone.utc).date()
    final = []
    for e in selected:
        seasons = sorted(e["seasons"], key=lambda s: s["season"])
        age = None
        bd = e.get("birth_date")
        try:
            if bd is not None and not (hasattr(bd, "isoformat") is False and bd != bd):
                bd_dt = bd if hasattr(bd, "year") else None
                if bd_dt is None:
                    import pandas as pd
                    bd_dt = pd.to_datetime(bd, errors="coerce")
                if bd_dt is not None and not pd.isna(bd_dt):
                    age = today.year - bd_dt.year - ((today.month, today.day) < (bd_dt.month, bd_dt.day))
        except Exception:
            age = None

        # Experience: count of seasons with games >= 1 in the data
        exp = len(seasons)
        tag = _detect_tag(seasons, e["position"])
        rookie_info = None
        # Will be filled-in by caller via rookie_meta
        final.append({
            "id": str(uuid.uuid4()),
            "ext_id": e["ext_id"],
            "name": e["name"],
            "position": e["position"],
            "team": e["team"],
            "age": age,
            "experience": exp,
            "headshot": "",
            "tag": tag,
            "rookie_info": rookie_info,  # filled in below
            "seasons": seasons,
            "news": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    # Attach rookie metadata if present
    for p in final:
        rm = rookie_meta.get(p["ext_id"])
        if rm:
            p["rookie_info"] = rm
            # If only seasons we have are < their rookie year, mark as zero-experience rookie
            if not p["seasons"] or all(s.get("season", 0) < rm["rookie_year"] for s in p["seasons"]):
                p["experience"] = 0
    return final


def _fetch_seasons_sync(seasons: Iterable[int]):
    """Run in thread — pulls from nflverse over HTTP. May 404 on missing seasons."""
    import nfl_data_py as nfl
    seasonal_dfs = {}
    roster_dfs = {}
    for s in seasons:
        try:
            seasonal_dfs[s] = nfl.import_seasonal_data([s])
            logger.info(f"Pulled {s} seasonal stats: {len(seasonal_dfs[s])} rows")
        except Exception as e:
            logger.warning(f"Season {s} stats not available: {e}")
            seasonal_dfs[s] = None
        try:
            roster_dfs[s] = nfl.import_seasonal_rosters([s])
            logger.info(f"Pulled {s} rosters: {len(roster_dfs[s])} rows")
        except Exception as e:
            logger.warning(f"Season {s} roster not available: {e}")
            roster_dfs[s] = None
    return seasonal_dfs, roster_dfs


def _fetch_schedule_sync(seasons: Iterable[int]):
    """Pull real NFL schedule for given seasons. Returns dict team -> next opponent."""
    import nfl_data_py as nfl
    import pandas as pd
    next_opp: dict[str, dict] = {}
    try:
        sched = nfl.import_schedules(list(seasons))
        if sched is None or sched.empty:
            return next_opp
        # Filter REG only, future games only
        today = pd.Timestamp(datetime.now(timezone.utc).date())
        sched["gameday_dt"] = pd.to_datetime(sched["gameday"], errors="coerce")
        future = sched[(sched["game_type"] == "REG") & (sched["gameday_dt"] >= today)]
        # Fallback: latest REG week if no future games (off-season)
        if future.empty:
            latest_season = int(sched["season"].max())
            ss = sched[(sched["season"] == latest_season) & (sched["game_type"] == "REG")]
            if not ss.empty:
                future = ss[ss["week"] == ss["week"].max()]
        future = future.sort_values("gameday_dt") if not future.empty else future
        for _, g in future.iterrows():
            home, away = g.get("home_team"), g.get("away_team")
            week = int(g.get("week", 0)) if not pd.isna(g.get("week")) else 0
            gameday = g.get("gameday")
            if isinstance(home, str) and home not in next_opp:
                next_opp[home] = {"opponent": away, "home": True, "week": week, "gameday": str(gameday)}
            if isinstance(away, str) and away not in next_opp:
                next_opp[away] = {"opponent": home, "home": False, "week": week, "gameday": str(gameday)}
    except Exception as e:
        logger.warning(f"Schedule fetch failed: {e}")
    return next_opp


# Cache: refreshed each refresh_player_data() call
_NEXT_OPP_CACHE: dict[str, dict] = {}


async def refresh_player_data(db, *, seasons: list[int] | None = None, force: bool = False) -> dict:
    """Refresh player data from nfl-data-py. Returns summary."""
    if seasons is None:
        # Try recent seasons; missing ones (current/upcoming not yet published by nflverse) are skipped.
        current_year = datetime.now(timezone.utc).year
        seasons = list(range(current_year - 4, current_year + 1))

    # Skip if data fresh
    if not force:
        meta = await db.meta.find_one({"key": "last_refresh"}, {"_id": 0})
        if meta:
            last = datetime.fromisoformat(meta["value"])
            if datetime.now(timezone.utc) - last < timedelta(hours=24):
                count = await db.players.count_documents({})
                if count > 0:
                    return {"status": "skipped", "reason": "fresh", "players": count}

    loop = asyncio.get_event_loop()
    seasonal_dfs, roster_dfs = await loop.run_in_executor(None, _fetch_seasons_sync, seasons)
    available = [s for s, df in seasonal_dfs.items() if df is not None and not df.empty]
    available_rosters = [s for s, df in roster_dfs.items() if df is not None and not df.empty]

    # Pull live schedules for available roster seasons
    sched_seasons = available_rosters or available
    next_opp = await loop.run_in_executor(None, _fetch_schedule_sync, sched_seasons)
    global _NEXT_OPP_CACHE
    if next_opp:
        _NEXT_OPP_CACHE = next_opp
        logger.info(f"Live schedule loaded: {len(next_opp)} teams have next-opponent data")

    if not available and not available_rosters:
        return {"status": "error", "reason": "no_data"}

    players = await loop.run_in_executor(None, _build_players_from_dataframes, seasonal_dfs, roster_dfs)
    if not players:
        return {"status": "error", "reason": "no_players_built"}

    # Merge: preserve existing news, ids if matching ext_id
    existing = await db.players.find({}, {"_id": 0, "id": 1, "ext_id": 1, "news": 1}).to_list(length=10000)
    ext_to_existing = {e.get("ext_id"): e for e in existing if e.get("ext_id")}

    merged = []
    for p in players:
        prev = ext_to_existing.get(p["ext_id"])
        if prev:
            p["id"] = prev["id"]
            if prev.get("news"):
                p["news"] = prev["news"]
        merged.append(p)

    # Replace collection
    await db.players.delete_many({})
    if merged:
        await db.players.insert_many(merged)

    # Seed 32 NFL team defenses (D/ST) — needed for full fantasy lineups
    def_docs = []
    for code, full_name in NFL_TEAMS:
        def_docs.append({
            "id": str(uuid.uuid4()),
            "ext_id": f"DEF_{code}",
            "name": f"{full_name} D/ST",
            "position": "DEF",
            "team": code,
            "age": None, "experience": None, "headshot": "",
            "tag": None, "rookie_info": None, "seasons": [], "news": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    await db.players.insert_many(def_docs)

    await db.meta.replace_one(
        {"key": "last_refresh"},
        {"key": "last_refresh", "value": datetime.now(timezone.utc).isoformat(), "seasons": available, "count": len(merged)},
        upsert=True,
    )
    return {"status": "ok", "players": len(merged), "seasons": available}


# Defense vs position rankings — synthesized 2024 (1=best D / hardest matchup, 32=worst D / softest matchup)
# Lower rank means tougher D against that position.
DEF_VS_POS_2024 = {
    "QB": {"BAL": 1, "PHI": 2, "MIN": 3, "DEN": 4, "PIT": 5, "GB": 6, "BUF": 7, "DET": 8, "NYG": 9, "SF": 10,
           "HOU": 11, "ARI": 12, "SEA": 13, "TB": 14, "LAC": 15, "KC": 16, "WAS": 17, "CHI": 18, "ATL": 19, "NE": 20,
           "JAX": 21, "MIA": 22, "LV": 23, "TEN": 24, "DAL": 25, "CIN": 26, "IND": 27, "NO": 28, "NYJ": 29, "CLE": 30, "LAR": 31, "CAR": 32},
    "RB": {"PHI": 1, "BAL": 2, "DEN": 3, "MIN": 4, "PIT": 5, "BUF": 6, "DET": 7, "GB": 8, "HOU": 9, "TB": 10,
           "WAS": 11, "ATL": 12, "SF": 13, "KC": 14, "NYG": 15, "LAC": 16, "CHI": 17, "ARI": 18, "MIA": 19, "TEN": 20,
           "JAX": 21, "SEA": 22, "NE": 23, "IND": 24, "NO": 25, "CIN": 26, "DAL": 27, "CLE": 28, "NYJ": 29, "LAR": 30, "LV": 31, "CAR": 32},
    "WR": {"DET": 1, "MIN": 2, "BAL": 3, "PHI": 4, "DEN": 5, "GB": 6, "BUF": 7, "PIT": 8, "TB": 9, "HOU": 10,
           "SF": 11, "KC": 12, "LAC": 13, "ARI": 14, "ATL": 15, "WAS": 16, "CHI": 17, "NYG": 18, "SEA": 19, "JAX": 20,
           "NE": 21, "DAL": 22, "MIA": 23, "TEN": 24, "IND": 25, "NO": 26, "CIN": 27, "LV": 28, "NYJ": 29, "CLE": 30, "LAR": 31, "CAR": 32},
    "TE": {"MIN": 1, "BAL": 2, "PHI": 3, "DEN": 4, "BUF": 5, "DET": 6, "PIT": 7, "GB": 8, "TB": 9, "KC": 10,
           "SF": 11, "HOU": 12, "ARI": 13, "WAS": 14, "ATL": 15, "CHI": 16, "LAC": 17, "NYG": 18, "JAX": 19, "SEA": 20,
           "DAL": 21, "MIA": 22, "TEN": 23, "NO": 24, "IND": 25, "NE": 26, "CLE": 27, "CIN": 28, "LV": 29, "NYJ": 30, "LAR": 31, "CAR": 32},
}


# Static "next week" opponent map — fallback if live schedule fetch fails.
NEXT_OPPONENT = {
    "ARI": "SEA", "ATL": "TB", "BAL": "PIT", "BUF": "MIA", "CAR": "NO", "CHI": "GB", "CIN": "CLE", "CLE": "CIN",
    "DAL": "PHI", "DEN": "LV", "DET": "MIN", "GB": "CHI", "HOU": "JAX", "IND": "TEN", "JAX": "HOU", "KC": "LAC",
    "LAC": "KC", "LAR": "SF", "LV": "DEN", "MIA": "BUF", "MIN": "DET", "NE": "NYJ", "NO": "CAR", "NYG": "WAS",
    "NYJ": "NE", "PHI": "DAL", "PIT": "BAL", "SEA": "ARI", "SF": "LAR", "TB": "ATL", "TEN": "IND", "WAS": "NYG",
}


def get_next_opponent(team: str) -> dict | None:
    """Return {opponent, home, week, gameday} from live schedule, fallback to static map."""
    if team in _NEXT_OPP_CACHE:
        return _NEXT_OPP_CACHE[team]
    opp = NEXT_OPPONENT.get(team)
    if opp:
        return {"opponent": opp, "home": False, "week": 0, "gameday": None}
    return None


def get_next_opponent_team(team: str) -> str | None:
    info = get_next_opponent(team)
    return info["opponent"] if info else None


def player_news_search_url(player_name: str) -> str:
    """Build a Google News search URL for a player — fallback link until we wire a real news API."""
    from urllib.parse import quote_plus
    return f"https://news.google.com/search?q={quote_plus(player_name + ' NFL fantasy')}"


def get_def_rank(opp_team: str, position: str) -> int:
    """Return defense rank (1=tough, 32=soft) for opp_team vs position."""
    return DEF_VS_POS_2024.get(position, {}).get(opp_team, 16)


def matchup_score(opp_team: str, position: str) -> float:
    """Higher = better matchup. Range ~ -2.0 to +2.0"""
    rank = get_def_rank(opp_team, position)
    # rank 1 -> -2 (toughest), rank 32 -> +2 (softest), linear
    return round((rank - 16.5) / 7.75, 2)
