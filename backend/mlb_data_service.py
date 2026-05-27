"""MLB data service using pybaseball.
Fetches player stats for fantasy baseball.
"""
from __future__ import annotations
import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("ffref.mlb")

# Map full city/team names from Baseball Reference to abbreviations
MLB_TEAM_NAME_TO_ABV = {
    "Arizona": "ARI", "Atlanta": "ATL", "Baltimore": "BAL", "Boston": "BOS",
    "Cincinnati": "CIN", "Cleveland": "CLE", "Colorado": "COL", "Detroit": "DET",
    "Houston": "HOU", "Kansas City": "KC", "Miami": "MIA", "Milwaukee": "MIL",
    "Minnesota": "MIN", "Oakland": "OAK", "Philadelphia": "PHI", "Pittsburgh": "PIT",
    "San Diego": "SD", "San Francisco": "SF", "Seattle": "SEA", "St. Louis": "STL",
    "Tampa Bay": "TB", "Texas": "TEX", "Toronto": "TOR", "Washington": "WSH",
    # AL/NL disambiguation
    "Chicago": "CHC",      # default Chicago to Cubs; White Sox handled below
    "Los Angeles": "LAD",  # default LA to Dodgers; Angels handled below
    "New York": "NYM",     # default NY to Mets; Yankees handled below
    # Full team names
    "Cubs": "CHC", "White Sox": "CWS", "Yankees": "NYY", "Mets": "NYM",
    "Dodgers": "LAD", "Angels": "LAA", "Athletics": "OAK",
    # Lev-based disambiguation keys (used with Lev column)
    "Chicago-AL": "CWS", "Chicago-NL": "CHC",
    "Los Angeles-AL": "LAA", "Los Angeles-NL": "LAD",
    "New York-AL": "NYY", "New York-NL": "NYM",
}

MLB_BATTER_POSITIONS = {"C", "1B", "2B", "3B", "SS", "OF", "DH"}
MLB_PITCHER_POSITIONS = {"SP", "RP"}

def _fetch_mlb_positions() -> dict:
    """Fetch player positions from MLB Stats API."""
    import urllib.request
    import json
    pos_lookup = {}
    try:
        url = "https://statsapi.mlb.com/api/v1/sports/1/players?season=2026&gameType=R"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        for player in data.get("people", []):
            mlb_id = player.get("id")
            pos = player.get("primaryPosition", {}).get("abbreviation", "")
            if mlb_id and pos:
                # Normalize position
                if pos in ("C",):
                    mapped = "C"
                elif pos in ("1B",):
                    mapped = "1B"
                elif pos in ("2B",):
                    mapped = "2B"
                elif pos in ("3B",):
                    mapped = "3B"
                elif pos in ("SS",):
                    mapped = "SS"
                elif pos in ("DH",):
                    mapped = "DH"
                elif pos in ("LF", "CF", "RF", "OF"):
                    mapped = "OF"
                elif pos in ("SP", "P"):
                    mapped = "SP"
                elif pos in ("RP",):
                    mapped = "RP"
                else:
                    mapped = "OF"
                pos_lookup[str(mlb_id)] = mapped
        logger.info(f"MLB position lookup: {len(pos_lookup)} players")
    except Exception as e:
        logger.warning(f"MLB position lookup failed: {e}")
    return pos_lookup

def _normalize_mlb_team(tm: str, lev: str = "") -> str:
    """Convert full team name to abbreviation using Lev to disambiguate."""
    tm = tm.strip()
    lev = lev.strip()
    if not tm or tm == "TOT":
        return tm
    # Try disambiguation with league
    if tm in ("Chicago", "Los Angeles", "New York"):
        league = "AL" if "-AL" in lev else "NL" if "-NL" in lev else ""
        if league:
            key = f"{tm}-{league}"
            if key in MLB_TEAM_NAME_TO_ABV:
                return MLB_TEAM_NAME_TO_ABV[key]
    return MLB_TEAM_NAME_TO_ABV.get(tm, tm[:3].upper() if len(tm) >= 3 else tm)


def _fix_name_encoding(raw) -> str:
    """Fix UTF-8 encoding issues in player names from pybaseball."""
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace").strip()
    s = str(raw).strip()
    # Handle literal \xNN escape sequences in the string
    import re
    if re.search(r'\\x[0-9a-fA-F]{2}', s):
        try:
            s = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), s)
            s = s.encode('latin-1').decode('utf-8')
        except Exception:
            pass
    else:
        try:
            s = s.encode("latin-1").decode("utf-8").strip()
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass
    return s


def _compute_batter_fpts(row: dict) -> float:
    h = (row.get("H") or 0) * 1.0
    r = (row.get("R") or 0) * 1.0
    hr = (row.get("HR") or 0) * 4.0
    rbi = (row.get("RBI") or 0) * 1.0
    sb = (row.get("SB") or 0) * 2.0
    bb = (row.get("BB") or 0) * 1.0
    so = (row.get("SO") or 0) * -0.5
    return round(h + r + hr + rbi + sb + bb + so, 2)


def _compute_pitcher_fpts(row: dict) -> float:
    ip = (row.get("IP") or 0) * 3.0
    k = (row.get("SO") or 0) * 1.0
    w = (row.get("W") or 0) * 5.0
    sv = (row.get("SV") or 0) * 5.0
    er = (row.get("ER") or 0) * -1.0
    bb = (row.get("BB") or 0) * -0.5
    h = (row.get("H") or 0) * -0.5
    return round(ip + k + w + sv + er + bb + h, 2)


def _detect_mlb_tag(seasons: list[dict], position: str) -> str | None:
    if not seasons:
        return None
    seasons_sorted = sorted(seasons, key=lambda s: s["season"])
    latest = seasons_sorted[-1]
    fppg = latest.get("fpts_per_game", 0)
    games = latest.get("G", 0)

    is_pitcher = position in MLB_PITCHER_POSITIONS

    if is_pitcher:
        elite_thresh, break_thresh = 18, 13
        min_games = 20
    else:
        elite_thresh, break_thresh = 12, 8
        min_games = 80

    if fppg >= elite_thresh and games >= min_games:
        return "elite"
    if len(seasons_sorted) >= 2:
        prev = seasons_sorted[-2]
        if (
            fppg >= break_thresh
            and prev.get("fpts_per_game", 0) < break_thresh - 3
            and games >= min_games * 0.6
        ):
            return "breakout"
    if games > 0 and games < min_games * 0.4:
        return "risk"
    if fppg >= break_thresh - 2 and games <= min_games and len(seasons_sorted) <= 2:
        return "sleeper"
    return None


def _fetch_mlb_players_sync(seasons_back: int = 3) -> list[dict]:
    """Fetch MLB player stats using MLB Stats API directly."""
    import urllib.request
    import json
    import math

    def safe_int(v):
        try:
            if v is None or (isinstance(v, float) and math.isnan(v)):
                return 0
            return int(v)
        except Exception:
            return 0

    def safe_float(v, decimals=2):
        try:
            if v is None or (isinstance(v, float) and math.isnan(v)):
                return 0.0
            return round(float(v), decimals)
        except Exception:
            return 0.0

    def mlb_api_get(url):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())

    current_year = datetime.now(timezone.utc).year
    seasons = list(range(current_year - seasons_back + 1, current_year + 1))

    all_player_seasons: dict[str, dict] = {}

    for season in seasons:
        # ── Batters ──
        try:
            url = (
                f"https://statsapi.mlb.com/api/v1/stats"
                f"?stats=season&season={season}&group=hitting"
                f"&gameType=R&limit=1000&offset=0"
                f"&fields=stats,splits,stat,player,team,season"
            )
            data = mlb_api_get(url)
            splits = data.get("stats", [{}])[0].get("splits", [])
            logger.info(f"Fetched MLB batting {season}: {len(splits)} players")

            for split in splits:
                stat = split.get("stat", {})
                player = split.get("player", {})
                team = split.get("team", {})

                pid = str(player.get("id", ""))
                if not pid:
                    continue

                name = player.get("fullName", "")
                team_abv = team.get("abbreviation", "")
                games = safe_int(stat.get("gamesPlayed"))

                if games < (5 if season == current_year else 20):
                    continue

                # Get position from players endpoint
                pos = "OF"  # will be overridden by position lookup

                season_rec = {
                    "season": season,
                    "G": games,
                    "AB": safe_int(stat.get("atBats")),
                    "H": safe_int(stat.get("hits")),
                    "R": safe_int(stat.get("runs")),
                    "HR": safe_int(stat.get("homeRuns")),
                    "RBI": safe_int(stat.get("rbi")),
                    "SB": safe_int(stat.get("stolenBases")),
                    "BB": safe_int(stat.get("baseOnBalls")),
                    "SO": safe_int(stat.get("strikeOuts")),
                    "AVG": safe_float(stat.get("avg"), 3),
                    "OBP": safe_float(stat.get("obp"), 3),
                    "SLG": safe_float(stat.get("slg"), 3),
                    "OPS": safe_float(stat.get("ops"), 3),
                }
                fpts = _compute_batter_fpts(season_rec)
                season_rec["fpts"] = fpts
                season_rec["fpts_per_game"] = round(fpts / max(games, 1), 2)

                bpid = f"BAT_{pid}"
                if bpid not in all_player_seasons:
                    all_player_seasons[bpid] = {
                        "ext_id": f"MLB_{bpid}",
                        "name": name,
                        "position": pos,
                        "team": team_abv,
                        "sport": "mlb",
                        "player_type": "batter",
                        "mlb_id": pid,
                        "seasons": [],
                    }
                else:
                    all_player_seasons[bpid]["team"] = team_abv

                all_player_seasons[bpid]["seasons"].append(season_rec)

        except Exception as e:
            logger.warning(f"MLB batting {season} failed: {e}")

        # ── Pitchers ──
        try:
            url = (
                f"https://statsapi.mlb.com/api/v1/stats"
                f"?stats=season&season={season}&group=pitching"
                f"&gameType=R&limit=1000&offset=0"
                f"&fields=stats,splits,stat,player,team,season"
            )
            data = mlb_api_get(url)
            splits = data.get("stats", [{}])[0].get("splits", [])
            logger.info(f"Fetched MLB pitching {season}: {len(splits)} players")

            for split in splits:
                stat = split.get("stat", {})
                player = split.get("player", {})
                team = split.get("team", {})

                pid = str(player.get("id", ""))
                if not pid:
                    continue

                name = player.get("fullName", "")
                team_abv = team.get("abbreviation", "")
                games = safe_int(stat.get("gamesPlayed"))
                gs = safe_int(stat.get("gamesStarted"))

                if games < (2 if season == current_year else 5):
                    continue

                pos = "SP" if gs >= games * 0.5 else "RP"

                ip_str = stat.get("inningsPitched", "0") or "0"
                try:
                    ip = float(ip_str)
                except Exception:
                    ip = 0.0

                season_rec = {
                    "season": season,
                    "G": games,
                    "GS": gs,
                    "IP": round(ip, 1),
                    "W": safe_int(stat.get("wins")),
                    "L": safe_int(stat.get("losses")),
                    "SV": safe_int(stat.get("saves")),
                    "SO": safe_int(stat.get("strikeOuts")),
                    "BB": safe_int(stat.get("baseOnBalls")),
                    "H": safe_int(stat.get("hits")),
                    "ER": safe_int(stat.get("earnedRuns")),
                    "ERA": safe_float(stat.get("era")),
                    "WHIP": safe_float(stat.get("whip")),
                    "K9": safe_float(stat.get("strikeoutsPer9Inn"), 1),
                }
                fpts = _compute_pitcher_fpts(season_rec)
                season_rec["fpts"] = fpts
                season_rec["fpts_per_game"] = round(fpts / max(games, 1), 2)

                ppid = f"PIT_{pid}"
                if ppid not in all_player_seasons:
                    all_player_seasons[ppid] = {
                        "ext_id": f"MLB_{ppid}",
                        "name": name,
                        "position": pos,
                        "team": team_abv,
                        "sport": "mlb",
                        "player_type": "pitcher",
                        "mlb_id": pid,
                        "seasons": [],
                    }
                else:
                    all_player_seasons[ppid]["team"] = team_abv

                all_player_seasons[ppid]["seasons"].append(season_rec)

        except Exception as e:
            logger.warning(f"MLB pitching {season} failed: {e}")

    # Apply position lookup
    pos_lookup = _fetch_mlb_positions()
    for pid_key, entry in all_player_seasons.items():
        mlb_id = entry.get("mlb_id", "")
        if mlb_id and entry.get("player_type") == "batter":
            looked_up = pos_lookup.get(str(mlb_id))
            if looked_up:
                entry["position"] = looked_up

    # Build final list
    final = []
    for pid, entry in all_player_seasons.items():
        seasons_sorted = sorted(entry["seasons"], key=lambda s: s["season"])
        latest = seasons_sorted[-1] if seasons_sorted else {}
        tag = _detect_mlb_tag(seasons_sorted, entry["position"])

        final.append({
            "id": str(uuid.uuid4()),
            "ext_id": entry["ext_id"],
            "name": entry["name"],
            "position": entry["position"],
            "team": entry["team"],
            "sport": "mlb",
            "player_type": entry.get("player_type", "batter"),
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

    logger.info(f"MLB players built: {len(final)}")
    return final


async def refresh_mlb_data(db, *, force: bool = False) -> dict:
    """Refresh MLB player data."""
    if not force:
        meta = await db.meta.find_one({"key": "last_mlb_refresh"}, {"_id": 0})
        if meta:
            last = datetime.fromisoformat(meta["value"])
            if datetime.now(timezone.utc) - last < timedelta(hours=24):
                count = await db.players.count_documents({"sport": "mlb"})
                if count > 0:
                    return {"status": "skipped", "reason": "fresh", "players": count}

    loop = asyncio.get_event_loop()
    players = await loop.run_in_executor(None, _fetch_mlb_players_sync)

    if not players:
        return {"status": "error", "reason": "no_mlb_data"}

    await db.players.delete_many({"sport": "mlb"})
    await db.players.insert_many(players)

    await db.meta.replace_one(
        {"key": "last_mlb_refresh"},
        {"key": "last_mlb_refresh", "value": datetime.now(timezone.utc).isoformat(), "count": len(players)},
        upsert=True,
    )

    return {"status": "ok", "players": len(players)}
