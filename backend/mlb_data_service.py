"""MLB data service using pybaseball.
Fetches player stats for fantasy baseball.
"""
from __future__ import annotations
import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("ffref.mlb")

MLB_BATTER_POSITIONS = {"C", "1B", "2B", "3B", "SS", "OF", "DH"}
MLB_PITCHER_POSITIONS = {"SP", "RP"}

# Fantasy scoring — standard points league
# Batters: H=1, R=1, HR=4, RBI=1, SB=2, BB=1, HBP=1, SO=-0.5
# Pitchers: IP=3, K=1, W=5, SV=5, HLD=3, ER=-1, BB=-0.5, H=-0.5

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
    """Fetch MLB player stats using pybaseball."""
    try:
        from pybaseball import batting_stats_bref as batting_stats
        from pybaseball import pitching_stats_bref as pitching_stats
        from pybaseball import cache
        cache.enable()
        import pandas as pd
    except ImportError:
        logger.error("pybaseball not installed")
        return []

    current_year = datetime.now(timezone.utc).year
    seasons = list(range(current_year - seasons_back + 1, current_year + 1))

    all_player_seasons: dict[str, dict] = {}

    # ── Batters ──
    for season in seasons:
        try:
            df = batting_stats(season, season, qual=50)
            if df is None or df.empty:
                logger.warning(f"No MLB batting data for {season}")
                continue
            logger.info(f"Fetched MLB batting {season}: {len(df)} players")

            for _, row in df.iterrows():
                name = str(row.get("Name", "") or "")
                team = str(row.get("Tm", "") or "")
                pos = str(row.get("Pos", "") or "").strip().upper()
                games = int(row.get("G", 0) or 0)
                pid = f"BAT_{name.replace(' ', '_')}_{team}"

                # Normalize position
                if "C" in pos:
                    pos = "C"
                elif "1B" in pos:
                    pos = "1B"
                elif "2B" in pos:
                    pos = "2B"
                elif "3B" in pos:
                    pos = "3B"
                elif "SS" in pos:
                    pos = "SS"
                elif "DH" in pos:
                    pos = "DH"
                else:
                    pos = "OF"

                season_rec = {
                    "season": season,
                    "G": games,
                    "AB": int(row.get("AB", 0) or 0),
                    "H": int(row.get("H", 0) or 0),
                    "R": int(row.get("R", 0) or 0),
                    "HR": int(row.get("HR", 0) or 0),
                    "RBI": int(row.get("RBI", 0) or 0),
                    "SB": int(row.get("SB", 0) or 0),
                    "BB": int(row.get("BB", 0) or 0),
                    "SO": int(row.get("SO", 0) or 0),
                    "AVG": round(float(row.get("AVG", 0) or 0), 3),
                    "OBP": round(float(row.get("OBP", 0) or 0), 3),
                    "SLG": round(float(row.get("SLG", 0) or 0), 3),
                    "OPS": round(float(row.get("OPS", 0) or 0), 3),
                }
                fpts = _compute_batter_fpts(season_rec)
                season_rec["fpts"] = fpts
                season_rec["fpts_per_game"] = round(fpts / max(games, 1), 2)

                if pid not in all_player_seasons:
                    all_player_seasons[pid] = {
                        "ext_id": f"MLB_{pid}",
                        "name": name,
                        "position": pos,
                        "team": team,
                        "sport": "mlb",
                        "player_type": "batter",
                        "seasons": [],
                    }
                else:
                    all_player_seasons[pid]["team"] = team

                all_player_seasons[pid]["seasons"].append(season_rec)

        except Exception as e:
            logger.warning(f"MLB batting {season} failed: {e}")

    # ── Pitchers ──
    for season in seasons:
        try:
            df = pitching_stats(season, season, qual=20)
            if df is None or df.empty:
                logger.warning(f"No MLB pitching data for {season}")
                continue
            logger.info(f"Fetched MLB pitching {season}: {len(df)} players")

            for _, row in df.iterrows():
                name = str(row.get("Name", "") or "")
                team = str(row.get("Team", "") or "")
                games = int(row.get("G", 0) or 0)
                gs = int(row.get("GS", 0) or 0)
                pid = f"PIT_{name.replace(' ', '_')}_{team}"

                # SP if more than half games are starts
                pos = "SP" if gs >= games * 0.5 else "RP"

                ip_raw = row.get("IP", 0) or 0
                try:
                    ip = float(ip_raw)
                except Exception:
                    ip = 0.0

                season_rec = {
                    "season": season,
                    "G": games,
                    "GS": gs,
                    "IP": round(ip, 1),
                    "W": int(row.get("W", 0) or 0),
                    "L": int(row.get("L", 0) or 0),
                    "SV": int(row.get("SV", 0) or 0),
                    "SO": int(row.get("SO", 0) or 0),
                    "BB": int(row.get("BB", 0) or 0),
                    "H": int(row.get("H", 0) or 0),
                    "ER": int(row.get("ER", 0) or 0),
                    "ERA": round(float(row.get("ERA", 0) or 0), 2),
                    "WHIP": round(float(row.get("WHIP", 0) or 0), 2),
                    "K9": round(float(row.get("K/9", 0) or 0), 1),
                }
                fpts = _compute_pitcher_fpts(season_rec)
                season_rec["fpts"] = fpts
                season_rec["fpts_per_game"] = round(fpts / max(games, 1), 2)

                if pid not in all_player_seasons:
                    all_player_seasons[pid] = {
                        "ext_id": f"MLB_{pid}",
                        "name": name,
                        "position": pos,
                        "team": team,
                        "sport": "mlb",
                        "player_type": "pitcher",
                        "seasons": [],
                    }
                else:
                    all_player_seasons[pid]["team"] = team

                all_player_seasons[pid]["seasons"].append(season_rec)

        except Exception as e:
            logger.warning(f"MLB pitching {season} failed: {e}")

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
