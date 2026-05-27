"""NBA data service using nba_api.
Fetches player stats, rosters, and schedules for fantasy basketball.
"""
from __future__ import annotations
import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger("ffref.nba")

NBA_POSITIONS = {"PG", "SG", "SF", "PF", "C"}

# Fantasy points scoring (standard points league)
# PTS=1, REB=1.2, AST=1.5, STL=3, BLK=3, TO=-1, 3PM=0.5
FP_WEIGHTS = {
    "pts": 1.0,
    "fgm": 2.0,
    "fga": -1.0,
    "ftm": 1.0,
    "fta": -1.0,
    "fg3m": 1.0,
    "reb": 1.0,
    "ast": 2.0,
    "stl": 4.0,
    "blk": 4.0,
    "tov": -2.0,
}

NBA_TEAMS = [
    ("ATL", "Atlanta Hawks"), ("BOS", "Boston Celtics"), ("BKN", "Brooklyn Nets"),
    ("CHA", "Charlotte Hornets"), ("CHI", "Chicago Bulls"), ("CLE", "Cleveland Cavaliers"),
    ("DAL", "Dallas Mavericks"), ("DEN", "Denver Nuggets"), ("DET", "Detroit Pistons"),
    ("GSW", "Golden State Warriors"), ("HOU", "Houston Rockets"), ("IND", "Indiana Pacers"),
    ("LAC", "LA Clippers"), ("LAL", "Los Angeles Lakers"), ("MEM", "Memphis Grizzlies"),
    ("MIA", "Miami Heat"), ("MIL", "Milwaukee Bucks"), ("MIN", "Minnesota Timberwolves"),
    ("NOP", "New Orleans Pelicans"), ("NYK", "New York Knicks"), ("OKC", "Oklahoma City Thunder"),
    ("ORL", "Orlando Magic"), ("PHI", "Philadelphia 76ers"), ("PHX", "Phoenix Suns"),
    ("POR", "Portland Trail Blazers"), ("SAC", "Sacramento Kings"), ("SAS", "San Antonio Spurs"),
    ("TOR", "Toronto Raptors"), ("UTA", "Utah Jazz"), ("WAS", "Washington Wizards"),
]

# Map full team names to abbreviations
TEAM_NAME_TO_ABV = {name: abv for abv, name in NBA_TEAMS}
TEAM_ABV_TO_NAME = {abv: name for abv, name in NBA_TEAMS}

def _compute_fpts(row: dict) -> float:
    return round(
        (row.get("pts") or 0) * 1.0 +
        (row.get("fgm") or 0) * 2.0 +
        (row.get("fga") or 0) * -1.0 +
        (row.get("ftm") or 0) * 1.0 +
        (row.get("fta") or 0) * -1.0 +
        (row.get("fg3m") or 0) * 1.0 +
        (row.get("reb") or 0) * 1.0 +
        (row.get("ast") or 0) * 2.0 +
        (row.get("stl") or 0) * 4.0 +
        (row.get("blk") or 0) * 4.0 +
        (row.get("tov") or 0) * -2.0,
        2
    )

def _detect_nba_tag(seasons: list[dict], position: str) -> str | None:
    if not seasons:
        return None
    seasons_sorted = sorted(seasons, key=lambda s: s["season"])
    latest = seasons_sorted[-1]
    fppg = latest.get("fpts_per_game", 0)
    games = latest.get("games", 0)

    elite_threshold = {"PG": 45, "SG": 38, "SF": 36, "PF": 36, "C": 38}.get(position, 40)
    breakout_threshold = {"PG": 35, "SG": 30, "SF": 28, "PF": 28, "C": 30}.get(position, 30)

    if fppg >= elite_threshold and games >= 50:
        return "elite"
    if len(seasons_sorted) >= 2:
        prev = seasons_sorted[-2]
        if (
            fppg >= breakout_threshold
            and prev.get("fpts_per_game", 0) < breakout_threshold - 5
            and games >= 40
        ):
            return "breakout"
    if games > 0 and games < 30:
        return "risk"
    if fppg >= breakout_threshold - 5 and games <= 50 and len(seasons_sorted) <= 2:
        return "sleeper"
    return None

def _get_current_nba_season() -> str:
    """Returns current NBA season in YYYY-YY format e.g. 2025-26"""
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month
    # NBA season starts in October
    if month >= 10:
        return f"{year}-{str(year + 1)[-2:]}"
    else:
        return f"{year - 1}-{str(year)[-2:]}"

def _fetch_nba_players_sync(seasons_back: int = 3) -> list[dict]:
    """Fetch NBA player stats using nba_api."""
    try:
        from nba_api.stats.endpoints import leaguedashplayerstats, commonallplayers
        from nba_api.stats.static import players as nba_players_static
        import pandas as pd
        import time
    except ImportError:
        logger.error("nba_api not installed")
        return []

    current_season = _get_current_nba_season()
    season_year = int(current_season.split("-")[0])
    seasons = [current_season] + [
        f"{season_year - i}-{str(season_year - i + 1)[-2:]}"
        for i in range(1, seasons_back)
    ]

   # Build position lookup from team rosters
    pos_lookup = {}
    try:
        from nba_api.stats.endpoints import commonteamroster
        from nba_api.stats.static import teams as nba_teams_static
        all_teams = nba_teams_static.get_teams()
        logger.info(f"Building NBA position lookup from {len(all_teams)} teams...")
        for team in all_teams:
            try:
                time.sleep(0.5)
                roster = commonteamroster.CommonTeamRoster(
                    team_id=str(team["id"]),
                    season=current_season
                )
                dfs = roster.get_data_frames()
                if not dfs:
                    continue
                roster_df = dfs[0]
                for _, row in roster_df.iterrows():
                    pid = str(row.get("PLAYER_ID", ""))
                    pos = str(row.get("POSITION", "") or "").strip().upper()
                    if not pid:
                        continue
                    if not pos:
                        mapped = "SF"
                    elif pos in ("PG", "G"):
                        mapped = "PG"
                    elif pos == "SG":
                        mapped = "SG"
                    elif pos in ("SF", "F"):
                        mapped = "SF"
                    elif pos == "PF":
                        mapped = "PF"
                    elif pos in ("C",):
                        mapped = "C"
                    elif "G-F" in pos or "F-G" in pos:
                        mapped = "SG"
                    elif "F-C" in pos or "C-F" in pos:
                        mapped = "PF"
                    else:
                        mapped = "SF"
                    pos_lookup[pid] = mapped
            except Exception as team_err:
                logger.warning(f"NBA roster fetch failed for {team['abbreviation']}: {team_err}")
                continue
        logger.info(f"NBA position lookup built: {len(pos_lookup)} players")
    except Exception as e:
        logger.warning(f"NBA position lookup failed: {e}")

    all_player_seasons: dict[str, dict] = {}

    for season in seasons:
        try:
            logger.info(f"Fetching NBA season {season}...")
            time.sleep(0.6)
            stats = leaguedashplayerstats.LeagueDashPlayerStats(
                season=season,
                season_type_all_star="Regular Season",
                per_mode_detailed="PerGame",
            )
            df = stats.get_data_frames()[0]
            if df is None or df.empty:
                logger.warning(f"No NBA data for season {season}")
                continue

            logger.info(f"Fetched NBA {season}: {len(df)} players")

            for _, row in df.iterrows():
                pid = str(row.get("PLAYER_ID", ""))
                if not pid:
                    continue

                name = str(row.get("PLAYER_NAME", "") or "")
                team_abv = str(row.get("TEAM_ABBREVIATION", "") or "")
                games = int(row.get("GP", 0) or 0)

                if games < 5:
                    continue

                # Get position from lookup
                pos = pos_lookup.get(pid, "")
                if not pos:
                    pos = "SF"  # default

                pts = round(float(row.get("PTS", 0) or 0), 1)
                reb = round(float(row.get("REB", 0) or 0), 1)
                ast = round(float(row.get("AST", 0) or 0), 1)
                stl = round(float(row.get("STL", 0) or 0), 1)
                blk = round(float(row.get("BLK", 0) or 0), 1)
                tov = round(float(row.get("TOV", 0) or 0), 1)
                fg3m = round(float(row.get("FG3M", 0) or 0), 1)

                fgm = round(float(row.get("FGM", 0) or 0), 1)
                fga = round(float(row.get("FGA", 0) or 0), 1)
                ftm = round(float(row.get("FTM", 0) or 0), 1)
                fta = round(float(row.get("FTA", 0) or 0), 1)

                season_rec = {
                    "season": season,
                    "games": games,
                    "pts": pts,
                    "reb": reb,
                    "ast": ast,
                    "stl": stl,
                    "blk": blk,
                    "tov": tov,
                    "fg3m": fg3m,
                    "fgm": fgm,
                    "fga": fga,
                    "ftm": ftm,
                    "fta": fta,
                    "fg_pct": round(float(row.get("FG_PCT", 0) or 0) * 100, 1),
                    "ft_pct": round(float(row.get("FT_PCT", 0) or 0) * 100, 1),
                    "min": round(float(row.get("MIN", 0) or 0), 1),
                }
                fpts = _compute_fpts({"pts": pts, "fgm": fgm, "fga": fga, "ftm": ftm, "fta": fta, "fg3m": fg3m, "reb": reb, "ast": ast, "stl": stl, "blk": blk, "tov": tov})
                season_rec["fpts"] = fpts
                season_rec["fpts_per_game"] = fpts  # already per-game since stats are PerGame

                if pid not in all_player_seasons:
                    all_player_seasons[pid] = {
                        "ext_id": f"NBA_{pid}",
                        "name": name,
                        "position": pos,
                        "team": team_abv,
                        "seasons": [],
                        "sport": "nba",
                    }
                else:
                    all_player_seasons[pid]["team"] = team_abv
                    # Update position if we have a better one
                    if pos != "SF":
                        all_player_seasons[pid]["position"] = pos

                all_player_seasons[pid]["seasons"].append(season_rec)

        except Exception as e:
            logger.warning(f"NBA season {season} fetch failed: {e}")
            continue

    # Build final player list
    final = []
    for pid, entry in all_player_seasons.items():
        seasons_sorted = sorted(entry["seasons"], key=lambda s: s["season"])
        latest = seasons_sorted[-1] if seasons_sorted else {}
        tag = _detect_nba_tag(seasons_sorted, entry["position"])

        final.append({
            "id": str(uuid.uuid4()),
            "ext_id": entry["ext_id"],
            "name": entry["name"],
            "position": entry["position"],
            "team": entry["team"],
            "sport": "nba",
            "age": None,
            "experience": len(seasons_sorted),
            "headshot": "",
            "tag": tag,
            "rookie_info": None,
            "seasons": seasons_sorted,
            "news": [],
            "current_fpts": latest.get("fpts_per_game", 0),
            "current_fpts_per_game": latest.get("fpts_per_game", 0),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    logger.info(f"NBA players built: {len(final)}")
    return final


async def refresh_nba_data(db, *, force: bool = False) -> dict:
    """Refresh NBA player data."""
    if not force:
        meta = await db.meta.find_one({"key": "last_nba_refresh"}, {"_id": 0})
        if meta:
            last = datetime.fromisoformat(meta["value"])
            if datetime.now(timezone.utc) - last < timedelta(hours=24):
                count = await db.players.count_documents({"sport": "nba"})
                if count > 0:
                    return {"status": "skipped", "reason": "fresh", "players": count}

    loop = asyncio.get_event_loop()
    players = await loop.run_in_executor(None, _fetch_nba_players_sync)

    if not players:
        return {"status": "error", "reason": "no_nba_data"}

    # Delete old NBA players and reinsert
    await db.players.delete_many({"sport": "nba"})
    await db.players.insert_many(players)

    await db.meta.replace_one(
        {"key": "last_nba_refresh"},
        {"key": "last_nba_refresh", "value": datetime.now(timezone.utc).isoformat(), "count": len(players)},
        upsert=True,
    )

    return {"status": "ok", "players": len(players)}
