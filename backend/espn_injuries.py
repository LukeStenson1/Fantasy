"""ESPN injuries + news integration — pulls real-time NFL data from public ESPN endpoints.

Injuries endpoint: https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries
News endpoint: https://site.api.espn.com/apis/site/v2/sports/football/nfl/news
- Both public, no API key, no auth.
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
import urllib.request
import json
import re

logger = logging.getLogger("ffref.injuries")

ESPN_INJURIES_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries"
ESPN_NEWS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/news?limit=100"
ESPN_TEAM_NEWS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/news?limit=20"

STATUS_PENALTY = {
    "active": 0.0,
    "probable": -0.2,
    "questionable": -1.0,
    "doubtful": -3.5,
    "out": -10.0,
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

# ESPN team abbreviation -> our code
ESPN_ABV_TO_CODE = {
    "ARI": "ARI", "ATL": "ATL", "BAL": "BAL", "BUF": "BUF", "CAR": "CAR",
    "CHI": "CHI", "CIN": "CIN", "CLE": "CLE", "DAL": "DAL", "DEN": "DEN",
    "DET": "DET", "GB": "GB", "HOU": "HOU", "IND": "IND", "JAX": "JAX",
    "KC": "KC", "LAC": "LAC", "LAR": "LAR", "LV": "LV", "MIA": "MIA",
    "MIN": "MIN", "NE": "NE", "NO": "NO", "NYG": "NYG", "NYJ": "NYJ",
    "PHI": "PHI", "PIT": "PIT", "SEA": "SEA", "SF": "SF", "TB": "TB",
    "TEN": "TEN", "WSH": "WAS", "WAS": "WAS",
}


def _fetch_url_sync(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "FantasyLab/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_injuries_sync() -> list[dict]:
    return _fetch_url_sync(ESPN_INJURIES_URL)


async def refresh_news(db, news_items: list[dict]) -> int:
    """Match news articles to players by team and update their news field.
    Each player gets up to 6 most recent articles from their team."""
    if not news_items:
        return 0

    # Build team -> news list map
    team_news: dict[str, list[dict]] = {}
    for item in news_items:
        for team in item.get("teams", []):
            team_news.setdefault(team, []).append(item)

    logger.info(f"News team_news keys: {list(team_news.keys())[:10]}")
    logger.info(f"Sample news item teams: {[item.get('teams') for item in news_items[:5]]}")

    # Keep only 6 per team, sorted by date desc
    for team in team_news:
        team_news[team] = sorted(
            team_news[team],
            key=lambda x: x.get("date", ""),
            reverse=True
        )[:6]

    updated = 0
    for team, articles in team_news.items():
        result = await db.players.update_many(
            {"team": team, "position": {"$in": ["QB", "RB", "WR", "TE", "K"]}},
            {"$set": {"news": articles}}
        )
        updated += result.modified_count

    logger.info(f"News refresh: updated {updated} players across {len(team_news)} teams")
    return updated

FANTASY_KEYWORDS = [
    "fantasy", "targets", "touches", "snap", "snaps", "carries", "role",
    "depth chart", "starter", "backup", "injury", "return", "practice",
    "week", "activate", "waiver", "start", "sit", "add", "drop", "trade",
    "points", "production", "workload", "usage", "contract", "signs", "cut",
]

def _fantasy_score(article: dict) -> int:
    """Score article by fantasy relevance — higher = more relevant."""
    text = (article.get("headline", "") + " " + article.get("snippet", "")).lower()
    return sum(1 for kw in FANTASY_KEYWORDS if kw in text)

async def refresh_news(db, news_items: list[dict]) -> int:
    """Match news articles to players by team and update their news field.
    Prioritizes fantasy-relevant articles. Invalidates cached outlooks when news changes."""
    if not news_items:
        return 0

    # Build team -> news list map
    team_news: dict[str, list[dict]] = {}
    for item in news_items:
        for team in item.get("teams", []):
            team_news.setdefault(team, []).append(item)

    # Sort by fantasy relevance first, then date — keep top 6
    for team in team_news:
        team_news[team] = sorted(
            team_news[team],
            key=lambda x: (_fantasy_score(x), x.get("date", "")),
            reverse=True
        )[:6]

    updated = 0
    invalidated_outlook_ids = []

    for team, articles in team_news.items():
        # Find players on this team
        players = await db.players.find(
            {"team": team, "position": {"$in": ["QB", "RB", "WR", "TE", "K"]}},
            {"_id": 0, "id": 1, "news": 1}
        ).to_list(length=50)

        for player in players:
            old_news = player.get("news") or []
            old_headlines = {n.get("headline") for n in old_news}
            new_headlines = {a.get("headline") for a in articles}

            # News changed — update player and invalidate cached outlook
            if old_headlines != new_headlines:
                await db.players.update_one(
                    {"id": player["id"]},
                    {"$set": {"news": articles}}
                )
                invalidated_outlook_ids.append(player["id"])
                updated += 1

    # Invalidate cached outlooks for players with new news
    if invalidated_outlook_ids:
        res = await db.outlooks.delete_many({"player_id": {"$in": invalidated_outlook_ids}})
        logger.info(f"News refresh: invalidated {res.deleted_count} cached outlooks due to new news")

    logger.info(f"News refresh: updated {updated} players across {len(team_news)} teams")
    return updated


async def refresh_injuries(db) -> dict:
    """Pull current league injuries from ESPN, upsert into players + injuries collection."""
    loop = asyncio.get_event_loop()
    try:
        payload = await loop.run_in_executor(None, _fetch_injuries_sync)
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

    prior_rows = await db.players.find(
        {"injury_status": {"$exists": True, "$ne": None}},
        {"_id": 0, "id": 1, "injury_status": 1},
    ).to_list(length=2000)
    prior = {r["id"]: r.get("injury_status") for r in prior_rows}

    await db.injuries.delete_many({})
    if flat:
        await db.injuries.insert_many(flat)

    await db.players.update_many({}, {"$unset": {"injury_status": "", "injury_short": "", "injury_type": ""}})

    matched = 0
    matched_ids: set[str] = set()
    for inj in flat:
        if not inj["name_normalized"] or inj["status_normalized"] in ("active", ""):
            continue
        q = {}
        q["name"] = {"$regex": f"^{re.escape(inj['name'])}$", "$options": "i"}
        if inj.get("team"):
            q["team"] = inj["team"]
        target = await db.players.find_one(q, {"_id": 0, "id": 1})
        if target:
            await db.players.update_one({"id": target["id"]}, {
                "$set": {
                    "injury_status": inj["status"],
                    "injury_short": inj["short_comment"][:280],
                    "injury_type": inj.get("type"),
                    "injury_updated_at": datetime.now(timezone.utc).isoformat(),
                }
            })
            matched += 1
            matched_ids.add(target["id"])
            continue
        q.pop("team", None)
        target = await db.players.find_one(q, {"_id": 0, "id": 1})
        if target:
            await db.players.update_one({"id": target["id"]}, {
                "$set": {
                    "injury_status": inj["status"],
                    "injury_short": inj["short_comment"][:280],
                    "injury_type": inj.get("type"),
                    "injury_updated_at": datetime.now(timezone.utc).isoformat(),
                }
            })
            matched += 1
            matched_ids.add(target["id"])

    new_rows = await db.players.find(
        {"id": {"$in": list(matched_ids)}},
        {"_id": 0, "id": 1, "injury_status": 1},
    ).to_list(length=2000)
    new_status = {r["id"]: r.get("injury_status") for r in new_rows}
    changed_ids = set()
    for pid, new_st in new_status.items():
        if prior.get(pid) != new_st:
            changed_ids.add(pid)
    for pid, old_st in prior.items():
        if pid not in new_status and old_st:
            changed_ids.add(pid)

    invalidated = 0
    if changed_ids:
        res = await db.outlooks.delete_many({"player_id": {"$in": list(changed_ids)}})
        invalidated = res.deleted_count or 0

    await db.meta.replace_one(
        {"key": "last_injury_refresh"},
        {"key": "last_injury_refresh", "value": datetime.now(timezone.utc).isoformat(),
         "fetched": len(flat), "matched": matched, "outlooks_invalidated": invalidated},
        upsert=True,
    )
    logger.info(
        f"Injuries refresh: fetched {len(flat)}, matched {matched}, "
        f"changed {len(changed_ids)} players, invalidated {invalidated} outlooks"
    )
    return {"status": "ok", "fetched": len(flat), "matched": matched,
            "outlooks_invalidated": invalidated, "changed_players": len(changed_ids)}


def injury_penalty(status: str | None) -> float:
    if not status:
        return 0.0
    return STATUS_PENALTY.get(status.lower().strip(), 0.0)
