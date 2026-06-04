"""ESPN injuries + news integration — pulls real-time NFL, NBA, and MLB data from public ESPN endpoints."""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
import urllib.request
import json
import re

logger = logging.getLogger("ffref.injuries")

# ── ESPN endpoints ────────────────────────────────────────────────────────────
ESPN_INJURIES_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries"

ESPN_NEWS_URLS = {
    "nfl": "https://site.api.espn.com/apis/site/v2/sports/football/nfl/news?limit=100",
    "nba": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/news?limit=100",
    "mlb": "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/news?limit=100",
}

STATUS_PENALTY = {
    "active": 0.0, "probable": -0.2, "questionable": -1.0, "doubtful": -3.5,
    "out": -10.0, "ir": -10.0, "injured reserve": -10.0, "pup": -10.0,
    "suspension": -10.0, "suspended": -10.0, "day-to-day": -0.5,
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

ESPN_ABV_TO_CODE = {
    "ARI": "ARI", "ATL": "ATL", "BAL": "BAL", "BUF": "BUF", "CAR": "CAR",
    "CHI": "CHI", "CIN": "CIN", "CLE": "CLE", "DAL": "DAL", "DEN": "DEN",
    "DET": "DET", "GB": "GB", "HOU": "HOU", "IND": "IND", "JAX": "JAX",
    "KC": "KC", "LAC": "LAC", "LAR": "LAR", "LV": "LV", "MIA": "MIA",
    "MIN": "MIN", "NE": "NE", "NO": "NO", "NYG": "NYG", "NYJ": "NYJ",
    "PHI": "PHI", "PIT": "PIT", "SEA": "SEA", "SF": "SF", "TB": "TB",
    "TEN": "TEN", "WSH": "WAS", "WAS": "WAS",
    # NBA
    "ATL": "ATL", "BOS": "BOS", "BKN": "BKN", "CHA": "CHA", "CHI": "CHI",
    "CLE": "CLE", "DAL": "DAL", "DEN": "DEN", "DET": "DET", "GSW": "GSW",
    "HOU": "HOU", "IND": "IND", "LAC": "LAC", "LAL": "LAL", "MEM": "MEM",
    "MIA": "MIA", "MIL": "MIL", "MIN": "MIN", "NOP": "NOP", "NYK": "NYK",
    "OKC": "OKC", "ORL": "ORL", "PHI": "PHI", "PHX": "PHX", "POR": "POR",
    "SAC": "SAC", "SAS": "SAS", "TOR": "TOR", "UTA": "UTA", "WAS": "WAS",
    # MLB
    "ARI": "ARI", "ATL": "ATL", "BAL": "BAL", "BOS": "BOS", "CHC": "CHC",
    "CWS": "CWS", "CIN": "CIN", "CLE": "CLE", "COL": "COL", "DET": "DET",
    "HOU": "HOU", "KC": "KC", "LAA": "LAA", "LAD": "LAD", "MIA": "MIA",
    "MIL": "MIL", "MIN": "MIN", "NYM": "NYM", "NYY": "NYY", "OAK": "OAK",
    "PHI": "PHI", "PIT": "PIT", "SD": "SD", "SF": "SF", "SEA": "SEA",
    "STL": "STL", "TB": "TB", "TEX": "TEX", "TOR": "TOR", "WSH": "WSH",
}

# Sport-specific position filters for news matching
SPORT_POSITIONS = {
    "nfl": ["QB", "RB", "WR", "TE", "K", "DEF"],
    "nba": ["PG", "SG", "SF", "PF", "C"],
    "mlb": ["SP", "RP", "C", "1B", "2B", "3B", "SS", "OF", "DH"],
}

FANTASY_KEYWORDS = [
    "fantasy", "targets", "touches", "snap", "snaps", "carries", "role",
    "depth chart", "starter", "backup", "injury", "return", "practice",
    "week", "activate", "waiver", "start", "sit", "add", "drop", "trade",
    "points", "production", "workload", "usage", "contract", "signs", "cut",
    # NBA
    "minutes", "rebounds", "assists", "blocks", "steals", "rotation",
    # MLB
    "batting", "pitching", "rotation", "bullpen", "lineup", "ERA", "strikeout",
    "home run", "batting average", "on base",
]


def _fetch_url_sync(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "FantasyLab/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_injuries_sync() -> list[dict]:
    return _fetch_url_sync(ESPN_INJURIES_URL)


def _extract_team_codes(article: dict) -> list[str]:
    """Extract team codes from ESPN article categories."""
    teams = []
    for cat in (article.get("categories") or []):
        if cat.get("type") == "team":
            abv = cat.get("abbreviation", "")
            code = ESPN_ABV_TO_CODE.get(abv.upper())
            if not code:
                desc = cat.get("description", "")
                code = ESPN_TO_CODE.get(desc)
            if not code:
                team_obj = cat.get("team", {})
                if isinstance(team_obj, dict):
                    desc = team_obj.get("description", "")
                    code = ESPN_TO_CODE.get(desc)
            if code:
                teams.append(code)
    return teams


def _extract_athlete_names(article: dict) -> list[str]:
    """Extract player names mentioned in article categories."""
    names = []
    for cat in (article.get("categories") or []):
        if cat.get("type") == "athlete":
            desc = cat.get("description", "")
            if desc:
                names.append(desc)
            ath = cat.get("athlete", {})
            if isinstance(ath, dict):
                ath_desc = ath.get("description", "")
                if ath_desc and ath_desc not in names:
                    names.append(ath_desc)
    return names


def _parse_articles(articles: list[dict], sport: str) -> list[dict]:
    """Parse ESPN articles into standardized news items."""
    news_items = []
    for a in articles:
        if not isinstance(a, dict):
            continue
        teams = _extract_team_codes(a)
        athletes = _extract_athlete_names(a)
        headline = a.get("headline") or a.get("title") or ""
        description = a.get("description") or ""
        published = a.get("published") or a.get("lastModified") or ""
        url = ""
        links = a.get("links") or {}
        if isinstance(links, dict):
            web = links.get("web")
            if isinstance(web, dict):
                url = web.get("href", "")
            elif isinstance(web, list) and web:
                url = web[0].get("href", "") if isinstance(web[0], dict) else ""
        news_items.append({
            "headline": headline,
            "snippet": description[:300] if description else "",
            "url": url,
            "date": published[:10] if published else "",
            "source": "ESPN",
            "teams": teams,
            "athletes": athletes,
            "sport": sport,
        })
    return news_items


def _fetch_news_sync(sport: str = "nfl") -> list[dict]:
    """Fetch latest news for a sport from ESPN."""
    url = ESPN_NEWS_URLS.get(sport, ESPN_NEWS_URLS["nfl"])
    try:
        payload = _fetch_url_sync(url)
        if not isinstance(payload, dict):
            return []
        articles = [a for a in (payload.get("articles") or []) if isinstance(a, dict)]
        if articles:
            logger.info(f"ESPN article sample keys: {list(articles[0].keys())}")
            logger.info(f"ESPN article categories sample: {articles[0].get('categories', [])[:3]}")
        news_items = _parse_articles(articles, sport)
        logger.info(f"ESPN {sport.upper()} news: fetched {len(news_items)} articles")
        return news_items
    except Exception as e:
        logger.warning(f"ESPN {sport} news fetch failed: {e}")
        return []


def _fantasy_score(article: dict) -> int:
    text = (article.get("headline", "") + " " + article.get("snippet", "")).lower()
    return sum(1 for kw in FANTASY_KEYWORDS if kw in text)


async def refresh_news(db, news_items: list[dict]) -> int:
    """Match news articles to players by team/athlete and update their news field.
    Handles NFL, NBA, and MLB players."""
    if not news_items:
        return 0

    # Group by sport
    by_sport: dict[str, list[dict]] = {}
    for item in news_items:
        s = item.get("sport", "nfl")
        by_sport.setdefault(s, []).append(item)

    updated = 0
    invalidated_outlook_ids = []

    for sport, articles in by_sport.items():
        positions = SPORT_POSITIONS.get(sport, SPORT_POSITIONS["nfl"])

        # Build team -> news map
        team_news: dict[str, list[dict]] = {}
        for item in articles:
            for team in item.get("teams", []):
                team_news.setdefault(team, []).append(item)

        # Sort by fantasy relevance, keep top 6 per team
        for team in team_news:
            team_news[team] = sorted(
                team_news[team],
                key=lambda x: (_fantasy_score(x), x.get("date", "")),
                reverse=True,
            )[:6]

        for team, team_articles in team_news.items():
            players = await db.players.find(
                {"team": team, "sport": sport if sport != "nfl" else {"$not": {"$in": ["nba", "mlb"]}},
                 "position": {"$in": positions}},
                {"_id": 0, "id": 1, "news": 1}
            ).to_list(length=100)

            for player in players:
                old_headlines = {n.get("headline") for n in (player.get("news") or [])}
                new_headlines = {a.get("headline") for a in team_articles}
                if old_headlines != new_headlines:
                    await db.players.update_one(
                        {"id": player["id"]},
                        {"$set": {"news": team_articles}}
                    )
                    invalidated_outlook_ids.append(player["id"])
                    updated += 1

        # Also match by athlete name for direct mentions
        athlete_articles: dict[str, list[dict]] = {}
        for item in articles:
            for name in item.get("athletes", []):
                athlete_articles.setdefault(name, []).append(item)

        for athlete_name, ath_articles in athlete_articles.items():
            player = await db.players.find_one(
                {"name": {"$regex": f"^{re.escape(athlete_name)}$", "$options": "i"},
                 "sport": sport if sport != "nfl" else {"$not": {"$in": ["nba", "mlb"]}}},
                {"_id": 0, "id": 1, "news": 1}
            )
            if player:
                # Merge with existing team news, deduplicate
                existing = player.get("news") or []
                existing_headlines = {n.get("headline") for n in existing}
                new_items = [a for a in ath_articles if a.get("headline") not in existing_headlines]
                if new_items:
                    merged = sorted(
                        existing + new_items,
                        key=lambda x: (_fantasy_score(x), x.get("date", "")),
                        reverse=True,
                    )[:6]
                    await db.players.update_one(
                        {"id": player["id"]},
                        {"$set": {"news": merged}}
                    )
                    if player["id"] not in invalidated_outlook_ids:
                        invalidated_outlook_ids.append(player["id"])
                    updated += 1

    if invalidated_outlook_ids:
        res = await db.outlooks.delete_many({"player_id": {"$in": invalidated_outlook_ids}})
        logger.info(f"News refresh: invalidated {res.deleted_count} cached outlooks due to new news")

    logger.info(f"News refresh: updated {updated} players across {len(by_sport)} sports")
    return updated


async def refresh_injuries(db) -> dict:
    """Pull current NFL injuries from ESPN and upsert into players."""
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
        q = {"name": {"$regex": f"^{re.escape(inj['name'])}$", "$options": "i"}}
        if inj.get("team"):
            q["team"] = inj["team"]
        target = await db.players.find_one(q, {"_id": 0, "id": 1})
        if not target:
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
    changed_ids = {pid for pid, st in new_status.items() if prior.get(pid) != st}
    changed_ids |= {pid for pid, st in prior.items() if pid not in new_status and st}

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
    logger.info(f"Injuries refresh: fetched {len(flat)}, matched {matched}, invalidated {invalidated} outlooks")
    return {"status": "ok", "fetched": len(flat), "matched": matched,
            "outlooks_invalidated": invalidated, "changed_players": len(changed_ids)}


def injury_penalty(status: str | None) -> float:
    if not status:
        return 0.0
    return STATUS_PENALTY.get(status.lower().strip(), 0.0)
