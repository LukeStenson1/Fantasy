"""ESPN injuries integration — pulls real-time NFL injuries from public ESPN endpoint.

Endpoint: https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries
- Returns injuries grouped by team across the entire league.
- Public, no API key, no auth.
- Cached in MongoDB collection `injuries` keyed by player_name + team.
- Matched to our nflverse players by normalized name + team.
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
import urllib.request
import json
import re

logger = logging.getLogger("ffref.injuries")

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries"

# Status -> Lab Score penalty (deducted from lineup_score). Tuned conservatively.
STATUS_PENALTY = {
    "active": 0.0,
    "probable": -0.2,
    "questionable": -1.0,
    "doubtful": -3.5,
    "out": -10.0,         # Effectively benches them
    "ir": -10.0,
    "injured reserve": -10.0,
    "pup": -10.0,
    "suspension": -10.0,
    "suspended": -10.0,
    "day-to-day": -0.5,
}


def _normalize(name: str) -> str:
    if not name:
        return ""
    n = name.lower().strip()
    n = re.sub(r"[^a-z0-9 ]", "", n)
    n = re.sub(r"\s+", " ", n)
    return n


# Map ESPN team displayName to our 3-letter code
ESPN_TO_CODE = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF", "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC", "Los Angeles Chargers": "LAC", "Los Angeles Rams": "LAR",
    "Las Vegas Raiders": "LV", "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN",
    "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
    "Seattle Seahawks": "SEA", "San Francisco 49ers": "SF", "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
}


def _fetch_sync() -> list[dict]:
    """Sync HTTP fetch — runs in thread."""
    req = urllib.request.Request(ESPN_URL, headers={"User-Agent": "FantasyLab/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def refresh_injuries(db) -> dict:
    """Pull current league injuries from ESPN, upsert into players + injuries collection."""
    loop = asyncio.get_event_loop()
    try:
        payload = await loop.run_in_executor(None, _fetch_sync)
    except Exception as e:
        logger.warning(f"ESPN injuries fetch failed: {e}")
        return {"status": "error", "reason": str(e)}

    teams = payload.get("injuries", []) or []
    flat = []
    for team_block in teams:
        team_code = ESPN_TO_CODE.get(team_block.get("displayName", ""), None)
        for inj in team_block.get("injuries", []) or []:
            ath = inj.get("athlete") or {}
            name = ath.get("displayName") or ""
            status = (inj.get("status") or "").strip()
            short = inj.get("shortComment") or ""
            long_c = inj.get("longComment") or ""
            inj_type = inj.get("type", {}).get("description") if isinstance(inj.get("type"), dict) else None
            flat.append({
                "name": name,
                "name_normalized": _normalize(name),
                "team": team_code,
                "status": status,
                "status_normalized": status.lower().strip(),
                "type": inj_type,
                "short_comment": short,
                "long_comment": long_c,
                "espn_id": str(inj.get("id", "")),
                "athlete_id": str(ath.get("id", "")),
                "date": inj.get("date"),
            })

    # Replace injuries collection
    await db.injuries.delete_many({})
    if flat:
        await db.injuries.insert_many(flat)

    # Match to players by normalized name + team and update their injury_status
    # 1. Clear all stale injury fields first
    await db.players.update_many({}, {"$unset": {"injury_status": "", "injury_short": "", "injury_type": ""}})

    matched = 0
    for inj in flat:
        if not inj["name_normalized"] or inj["status_normalized"] in ("active", ""):
            continue
        # Find player by normalized name (and team if available)
        q = {}
        # Match by exact name first, then loosely by normalized prefix
        q["name"] = {"$regex": f"^{re.escape(inj['name'])}$", "$options": "i"}
        if inj.get("team"):
            q["team"] = inj["team"]
        result = await db.players.update_one(q, {
            "$set": {
                "injury_status": inj["status"],
                "injury_short": inj["short_comment"][:280],
                "injury_type": inj.get("type"),
                "injury_updated_at": datetime.now(timezone.utc).isoformat(),
            }
        })
        if result.matched_count:
            matched += 1
            continue
        # Fallback: loose match without team filter
        q.pop("team", None)
        result = await db.players.update_one(q, {
            "$set": {
                "injury_status": inj["status"],
                "injury_short": inj["short_comment"][:280],
                "injury_type": inj.get("type"),
                "injury_updated_at": datetime.now(timezone.utc).isoformat(),
            }
        })
        if result.matched_count:
            matched += 1

    await db.meta.replace_one(
        {"key": "last_injury_refresh"},
        {"key": "last_injury_refresh", "value": datetime.now(timezone.utc).isoformat(),
         "fetched": len(flat), "matched": matched},
        upsert=True,
    )
    logger.info(f"Injuries refresh: fetched {len(flat)}, matched to {matched} players")
    return {"status": "ok", "fetched": len(flat), "matched": matched}


def injury_penalty(status: str | None) -> float:
    """Return Lab Score penalty for a given injury status string."""
    if not status:
        return 0.0
    return STATUS_PENALTY.get(status.lower().strip(), 0.0)
