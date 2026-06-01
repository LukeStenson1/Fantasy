"""Fantasy Lab API."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import io
import csv
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Literal

from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, UploadFile, File, Query
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

from backend.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    set_auth_cookies, clear_auth_cookies,
    get_current_user_from_request, require_user,
)
from .llm_service import generate_player_outlook
from .nfl_data_service import (
    refresh_player_data, get_def_rank, matchup_score,
    DEF_VS_POS_2024, get_next_opponent, get_next_opponent_team,
    player_news_search_url, get_def_dvp, get_dvp_table,
    hydrate_dvp_cache, hydrate_next_opp_cache,
)
from .espn_injuries import refresh_injuries, injury_penalty

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("ffref")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Fantasy Lab API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://(fantasy(-[a-z0-9]+)*(-lukestenson1s-projects)?\.vercel\.app|fantasylabs\.website|www\.fantasylabs\.website)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter()

# ---------- Models ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RankingIn(BaseModel):
    title: str
    scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr"
    player_ids: List[str]
    notes: Optional[str] = None


class StartSitIn(BaseModel):
    player_ids: List[str]
    scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr"
    slot: Optional[Literal["QB", "RB", "WR", "TE", "FLEX"]] = None


class LineupSlot(BaseModel):
    slot: str
    player_id: str


class LineupIn(BaseModel):
    title: str
    scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr"
    starters: List[LineupSlot]
    bench: List[str] = []


class PredictionIn(BaseModel):
    player_id: str
    scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr"
    predicted_fpts: float
    week: Optional[int] = None
    season: Optional[int] = None
    source: Optional[str] = "lineup_ai"



# ---------- Auth ----------
@api.post("/auth/register")
async def register(payload: RegisterIn, response: Response):
    email = payload.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(400, "Email already registered")
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id, "email": email,
        "name": payload.name or email.split("@")[0],
        "role": "user", "password_hash": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    set_auth_cookies(response, create_access_token(user_id, email), create_refresh_token(user_id))
    return {"id": user_id, "email": email, "name": user["name"], "role": "user"}


@api.post("/auth/login")
async def login(payload: LoginIn, response: Response):
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    set_auth_cookies(response, create_access_token(user["id"], email), create_refresh_token(user["id"]))
    return {"id": user["id"], "email": email, "name": user.get("name"), "role": user.get("role", "user")}


@api.post("/auth/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"ok": True}


@api.get("/auth/me")
async def me(request: Request):
    user = await get_current_user_from_request(request, db)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return user


@api.post("/auth/refresh")
async def refresh_token_ep(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "No refresh token")
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(401, "User not found")
        set_auth_cookies(response, create_access_token(user["id"], user["email"]), create_refresh_token(user["id"]))
        return user
    except Exception as e:
        raise HTTPException(401, f"Invalid refresh token: {e}")


def _attach_current_season(p: dict, season, scoring: str) -> dict:
    seasons = p.get("seasons") or []
    sport = p.get("sport", "nfl")
    if not seasons:
        p["current_season"] = None
        p["current_fpts"] = 0
        p["current_fpts_per_game"] = 0
        return p
    if season:
        match = next((s for s in seasons if str(s.get("season", "")) == str(season)), None)
        if match is None:
            if sport == "nfl":
                match = seasons[-1]  # NFL falls back to latest
            else:
                # NBA/MLB — no fallback, player doesn't have this season
                p["current_season"] = None
                p["current_fpts"] = 0
                p["current_fpts_per_game"] = 0
                return p
    else:
        match = seasons[-1]
    p["current_season"] = match
    if sport == "nfl":
        p["current_fpts"] = match.get(f"fpts_{scoring}", 0) or 0
        p["current_fpts_per_game"] = match.get(f"fpts_per_game_{scoring}", 0) or 0
    else:
        p["current_fpts"] = match.get("fpts", 0) or 0
        p["current_fpts_per_game"] = match.get("fpts_per_game", 0) or 0
    return p


@api.get("/players")
async def list_players(
    position: Optional[str] = None,
    team: Optional[str] = None,
    season: Optional[str] = None,
    scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr",
    search: Optional[str] = None,
    sort: str = "current_fpts",
    direction: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=300, le=1000),
    tag: Optional[str] = None,
    sport: Optional[str] = None,
    player_type: Optional[str] = None,
):
    q = {}
    if sport and sport != "nfl":
        q["sport"] = sport
    else:
        q["sport"] = {"$not": {"$in": ["nba", "mlb"]}}
    if player_type:
        q["player_type"] = player_type
    if position and position != "ALL":
        q["position"] = position
    if team and team != "ALL":
        q["team"] = team
    if tag:
        q["tag"] = tag
    if search:
        q["name"] = {"$regex": search, "$options": "i"}
    cursor = db.players.find(q, {"_id": 0, "news": 0})
    items = await cursor.to_list(length=2000)
    items = [_attach_current_season(p, season, scoring) for p in items]
    # Attach matchup info for all players
    for p in items:
        info = get_next_opponent(p.get("team", ""))
        if info:
            p["next_opponent"] = info["opponent"]
            if p["position"] == "DEF":
                opp = info["opponent"]
                pos_ranks = []
                for pos in ["QB", "RB", "WR", "TE"]:
                    rank = get_def_rank(p.get("team", ""), pos)
                    pos_ranks.append(rank)
                avg_rank = sum(pos_ranks) / len(pos_ranks) if pos_ranks else 16
                p["matchup_score"] = round((16.5 - avg_rank) / 7.75, 2)
            else:
                p["matchup_score"] = matchup_score(info["opponent"], p["position"])
                dvp = get_def_dvp(info["opponent"], p["position"])
                p["matchup_def_rank"] = dvp.get("rank", 16)
                p["matchup_def_fpts_allowed"] = dvp.get("fpts_allowed_per_game")
                p["matchup_def_source"] = dvp.get("source")
    is_nfl = not sport or sport == "nfl"
    has_explicit_filter = bool(search) or position in ("DEF", "K") or tag is not None
    if is_nfl and not has_explicit_filter:
        items = [p for p in items if p.get("current_season")]
    elif not is_nfl:
        # For NBA/MLB, only show players who have data for the requested season
        items = [p for p in items if p.get("current_season")]
    reverse = direction == "desc"
    def keyfn(p):
        v = p.get(sort)
        if v is None and p.get("current_season"):
            v = p["current_season"].get(sort)
        return v if v is not None else (float("-inf") if reverse else float("inf"))
    items.sort(key=keyfn, reverse=reverse)
    return {"count": len(items), "items": items[:limit]}


@api.get("/players/{player_id}")
async def get_player(player_id: str, scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr"):
    p = await db.players.find_one({"id": player_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Player not found")
    p = _attach_current_season(p, None, scoring)
    # Add matchup info from live schedule
    info = get_next_opponent(p.get("team", ""))
    if info:
        p["next_opponent"] = info["opponent"]
        p["next_opponent_home"] = info.get("home")
        p["next_opponent_week"] = info.get("week")
        dvp = get_def_dvp(info["opponent"], p["position"])
        p["matchup_def_rank"] = dvp.get("rank", 16)
        p["matchup_def_fpts_allowed"] = dvp.get("fpts_allowed_per_game")
        p["matchup_def_source"] = dvp.get("source")
        p["matchup_score"] = matchup_score(info["opponent"], p["position"])
    p["news_search_url"] = player_news_search_url(p["name"])
    return p


@api.get("/players/{player_id}/outlook")
async def get_outlook(player_id: str, scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr"):
    p = await db.players.find_one({"id": player_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Player not found")
    cached = await db.outlooks.find_one({"player_id": player_id, "scoring": scoring}, {"_id": 0})
    if cached:
        return cached
    text = await generate_player_outlook(p, p.get("news", []), scoring)
    doc = {
        "player_id": player_id, "scoring": scoring, "outlook": text,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.outlooks.insert_one({**doc})
    doc.pop("_id", None)
    return doc


@api.post("/players/{player_id}/outlook/regenerate")
async def regenerate_outlook(player_id: str, scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr"):
    p = await db.players.find_one({"id": player_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Player not found")
    text = await generate_player_outlook(p, p.get("news", []), scoring)
    doc = {
        "player_id": player_id, "scoring": scoring, "outlook": text,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.outlooks.replace_one({"player_id": player_id, "scoring": scoring}, doc, upsert=True)
    return doc


# ---------- Sleepers / Busts ----------
@api.get("/sleepers-busts")
async def sleepers_busts(
    scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr",
    sport: Optional[str] = None,
):
    q: dict = {"tag": {"$ne": None}}
    if sport and sport != "nfl":
        q["sport"] = sport
    else:
        q["$or"] = [
            {"sport": {"$exists": False}},
            {"sport": None},
            {"sport": "nfl"},
        ]
    cursor = db.players.find(q, {"_id": 0, "news": 0})
    items = await cursor.to_list(length=2000)
    sleepers, busts, breakouts, elites = [], [], [], []
    for p in items:
        p = _attach_current_season(p, None, scoring)
        if not p.get("current_season"):
            continue
        slim = {
            "id": p["id"], "name": p["name"], "position": p["position"], "team": p["team"],
            "tag": p.get("tag"),
            "current_fpts": p.get("current_fpts"),
            "current_fpts_per_game": p.get("current_fpts_per_game"),
            "season": p["current_season"].get("season"),
        }
        tag = p.get("tag")
        if tag == "sleeper":
            sleepers.append(slim)
        elif tag == "risk":
            busts.append(slim)
        elif tag == "breakout":
            breakouts.append(slim)
        elif tag == "elite":
            elites.append(slim)

    for lst in (sleepers, busts, breakouts, elites):
        lst.sort(key=lambda x: x.get("current_fpts_per_game") or 0, reverse=True)
    return {"sleepers": sleepers, "busts": busts, "breakouts": breakouts, "elites": elites}


# ---------- Lineup Tool ----------
def _player_lineup_score(p: dict, scoring: str) -> tuple[float, dict]:
    """Calculate a composite lineup score. Returns (score, factors_dict).
    Factors live injury status (ESPN), live matchup (DvP from weekly nflverse data),
    availability (games last season), tag boost, self-learned bias correction."""
    cur = p.get("current_season") or {}
    fppg = cur.get(f"fpts_per_game_{scoring}", 0) or 0
    games = cur.get("games", 0) or 0

    # Matchup from live schedule
    opp = get_next_opponent_team(p.get("team") or "")
    m_score = matchup_score(opp, p["position"]) if opp else 0
    dvp = get_def_dvp(opp, p["position"]) if opp else {"rank": 16, "fpts_allowed_per_game": None, "source": "none"}

    # Live injury impact (ESPN refresh populates these fields)
    inj_status = p.get("injury_status")
    inj_pen = injury_penalty(inj_status)

    # Availability factor: penalize low games (injury history)
    avail = 0.0
    if games < 8:
        avail = -2.0
    elif games < 13:
        avail = -0.5

    # Tag boost
    tag = p.get("tag")
    tag_boost = {"elite": 1.5, "breakout": 0.8, "sleeper": 0.4, "risk": -0.8}.get(tag, 0)

    # Self-learned position bias correction (precomputed by caller into p["_lab_correction"])
    correction = p.get("_lab_correction") or 0

    score = round(fppg + m_score + avail + tag_boost + inj_pen + correction, 2)
    factors = {
        "fppg": fppg,
        "matchup_score": m_score,
        "def_rank": dvp.get("rank", 16),
        "def_fpts_allowed": dvp.get("fpts_allowed_per_game"),
        "def_rank_source": dvp.get("source"),
        "opponent": opp,
        "availability": avail,
        "tag_boost": tag_boost,
        "tag": tag,
        "injury_status": inj_status,
        "injury_short": p.get("injury_short"),
        "injury_penalty": inj_pen,
        "correction": correction,
    }
    return score, factors


def _reasoning_text(p: dict, factors: dict) -> str:
    parts = []
    fppg = factors["fppg"]
    parts.append(f"{fppg:.1f} FPts/G last season")
    opp = factors["opponent"]
    rank = factors["def_rank"]
    fpa = factors.get("def_fpts_allowed")
    if opp:
        rank_label = (
            "soft matchup" if rank >= 24 else
            "tough matchup" if rank <= 8 else
            "neutral matchup"
        )
        if fpa:
            parts.append(f"{rank_label} vs {opp} (#{rank} D vs {p['position']}, {fpa:.1f} allowed/G)")
        else:
            parts.append(f"{rank_label} vs {opp} (#{rank} D vs {p['position']})")
    if factors.get("injury_status"):
        parts.append(f"injury: {factors['injury_status']}")
    if factors["availability"] < 0:
        parts.append("availability concern (missed games)")
    if factors["tag"] == "elite":
        parts.append("elite-tier producer")
    elif factors["tag"] == "breakout":
        parts.append("trending up")
    elif factors["tag"] == "risk":
        parts.append("bust risk noted")
    return " · ".join(parts)


@api.get("/lineup/suggest")
async def suggest_lineup(request: Request, scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr"):
    """Suggest a starting lineup: 1QB / 2RB / 2WR / 1TE / 1FLEX. Logs predictions for self-learning."""
    cursor = db.players.find({"position": {"$in": ["QB", "RB", "WR", "TE"]}}, {"_id": 0, "news": 0})
    items = await cursor.to_list(length=2000)
    items = [_attach_current_season(p, None, scoring) for p in items]
    items = [p for p in items if p.get("current_season")]

    # Apply self-learned position bias correction
    bias = await _learned_bias_by_position()
    for p in items:
        p["_lab_correction"] = -1 * bias.get(p["position"], 0)  # subtract avg over-projection

    scored = []
    for p in items:
        score, factors = _player_lineup_score(p, scoring)
        scored.append({**p, "lineup_score": score, "factors": factors, "reasoning": _reasoning_text(p, factors)})

    by_pos: dict[str, list] = {}
    for p in scored:
        by_pos.setdefault(p["position"], []).append(p)
    for pos in by_pos:
        by_pos[pos].sort(key=lambda x: x["lineup_score"], reverse=True)

    def slim(p: dict) -> dict:
        return {
            "id": p["id"], "name": p["name"], "position": p["position"], "team": p["team"],
            "tag": p.get("tag"), "lineup_score": p["lineup_score"], "reasoning": p["reasoning"],
            "factors": p["factors"], "current_fpts_per_game": p.get("current_fpts_per_game"),
            "news_search_url": player_news_search_url(p["name"]),
        }

    qb = (by_pos.get("QB", []) or [])[:1]
    rb = (by_pos.get("RB", []) or [])[:2]
    wr = (by_pos.get("WR", []) or [])[:2]
    te = (by_pos.get("TE", []) or [])[:1]

    starters = set([p["id"] for p in qb + rb + wr + te])
    flex_pool = [p for p in scored if p["position"] in ("RB", "WR", "TE") and p["id"] not in starters]
    flex_pool.sort(key=lambda x: x["lineup_score"], reverse=True)
    flex = flex_pool[:1]

    bench: dict[str, list] = {}
    for pos, lst in by_pos.items():
        bench[pos] = [slim(p) for p in lst[:8] if p["id"] not in starters and p["id"] not in {f["id"] for f in flex}]

    # Log starter predictions for self-learning (no-op for anonymous users — captured globally)
    starter_list = qb + rb + wr + te + flex
    asyncio.create_task(_log_starter_predictions(starter_list, scoring, "lineup_ai"))

    return {
        "scoring": scoring,
        "starters": {
            "QB": [slim(p) for p in qb],
            "RB": [slim(p) for p in rb],
            "WR": [slim(p) for p in wr],
            "TE": [slim(p) for p in te],
            "FLEX": [slim(p) for p in flex],
        },
        "bench_alternatives": bench,
    }


async def _learned_bias_by_position() -> dict:
    """Return mean over-projection per position (positive = we over-predicted)."""
    pipeline = [
        {"$match": {"actual_fpts": {"$ne": None}}},
        {"$group": {
            "_id": "$position",
            "n": {"$sum": 1},
            "bias_sum": {"$sum": {"$subtract": ["$predicted_fpts", "$actual_fpts"]}},
        }},
    ]
    rows = await db.predictions.aggregate(pipeline).to_list(length=10)
    return {r["_id"]: r["bias_sum"] / max(r["n"], 1) for r in rows if r["n"] >= 5}


# ---------- Lineup Builder (roster-based) ----------
class RosterIn(BaseModel):
    player_ids: List[str]
    scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr"


@api.post("/lineup/build")
async def build_lineup_from_roster(payload: RosterIn):
    """Auto-pick a starting lineup from the user's roster: 1QB / 2RB / 2WR / 1TE / 1FLEX / 1K / 1DEF.
    Returns starters with Lab Score + reasoning, plus bench players ranked."""
    if not payload.player_ids:
        raise HTTPException(400, "Provide at least 1 player_id")
    cursor = db.players.find({"id": {"$in": payload.player_ids}}, {"_id": 0, "news": 0})
    items = await cursor.to_list(length=200)
    items = [_attach_current_season(p, None, payload.scoring) for p in items]

    bias = await _learned_bias_by_position()
    scored = []
    for p in items:
        p["_lab_correction"] = -1 * bias.get(p["position"], 0)
        score, factors = _player_lineup_score_v2(p, payload.scoring)
        scored.append({
            "id": p["id"], "name": p["name"], "position": p["position"], "team": p["team"],
            "tag": p.get("tag"),
            "lineup_score": score, "factors": factors,
            "reasoning": _reasoning_text(p, factors),
            "current_fpts_per_game": p.get("current_fpts_per_game"),
            "news_search_url": player_news_search_url(p["name"]),
        })

    by_pos: dict[str, list] = {}
    for p in scored:
        by_pos.setdefault(p["position"], []).append(p)
    for pos in by_pos:
        by_pos[pos].sort(key=lambda x: x["lineup_score"], reverse=True)

    qb = (by_pos.get("QB", []) or [])[:1]
    rb = (by_pos.get("RB", []) or [])[:2]
    wr = (by_pos.get("WR", []) or [])[:2]
    te = (by_pos.get("TE", []) or [])[:1]
    k = (by_pos.get("K", []) or [])[:1]
    d = (by_pos.get("DEF", []) or [])[:1]

    starter_ids = {p["id"] for p in qb + rb + wr + te + k + d}
    flex_pool = [p for p in scored if p["position"] in ("RB", "WR", "TE") and p["id"] not in starter_ids]
    flex_pool.sort(key=lambda x: x["lineup_score"], reverse=True)
    flex = flex_pool[:1]
    starter_ids |= {p["id"] for p in flex}

    bench = [p for p in scored if p["id"] not in starter_ids]
    bench.sort(key=lambda x: x["lineup_score"], reverse=True)

    asyncio.create_task(_log_starter_predictions(qb + rb + wr + te + flex, payload.scoring, "lineup_build"))

    return {
        "scoring": payload.scoring,
        "starters": {
            "QB": qb, "RB": rb, "WR": wr, "TE": te, "FLEX": flex, "K": k, "DEF": d,
        },
        "bench": bench,
    }


def _player_lineup_score_v2(p: dict, scoring: str) -> tuple[float, dict]:
    """Lab Score for ANY position including K and DEF.
    QB/RB/WR/TE → uses current-season FPts/G + matchup + tag boost + correction.
    K → matchup-based (soft pass D = more sacks/punts → more FG attempts).
    DEF → matchup-based (vs weak offense = more points)."""
    pos = p.get("position")
    opp = get_next_opponent_team(p.get("team") or "")

    if pos == "DEF":
        # Estimate opposing offense weakness as inverse of how their offense ranks vs DEFs (use generic position scoring)
        # Use a rough 'opposing offense' proxy: average of QB/RB/WR/TE def_rank for the opp team flipped
        ranks = [get_def_rank(opp, x) if opp else 16 for x in ("QB", "RB", "WR", "TE")]
        avg_rank = sum(ranks) / max(len(ranks), 1)  # 1 = strong def, 32 = soft def
        # Opposing offense is INVERSE: low avg_rank means they face good defenses (their team is weak offensively)
        # Soft offense → good DEF play
        m_score = round((16.5 - avg_rank) / 6, 2)
        baseline = 7.5  # avg fantasy DEF FPts/G league-wide
        score = round(baseline + m_score, 2)
        factors = {"fppg": baseline, "matchup_score": m_score, "def_rank": int(avg_rank), "opponent": opp,
                   "availability": 0, "tag_boost": 0, "tag": None, "correction": 0}
        return score, factors

    if pos == "K":
        # Kickers: matchup against soft def = more FG attempts (game flow / red zone stalls)
        m_rank = get_def_rank(opp, "QB") if opp else 16  # use QB D-rank as proxy for offensive game flow
        m_score = round((m_rank - 16.5) / 8, 2)
        baseline = 8.0  # avg fantasy K FPts/G
        score = round(baseline + m_score, 2)
        factors = {"fppg": baseline, "matchup_score": m_score, "def_rank": m_rank, "opponent": opp,
                   "availability": 0, "tag_boost": 0, "tag": None, "correction": 0}
        return score, factors

    return _player_lineup_score(p, scoring)


async def _log_starter_predictions(starters: list[dict], scoring: str, source: str):
    """Async-fire log predictions; never raise — best-effort self-learning."""
    try:
        for p in starters:
            doc = {
                "id": str(uuid.uuid4()),
                "user_id": None,
                "player_id": p["id"],
                "player_name": p["name"], "position": p["position"], "team": p["team"],
                "scoring": scoring,
                "predicted_fpts": p.get("lineup_score") or 0,
                "actual_fpts": None,
                "week": None, "season": None,
                "source": source,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "settled_at": None,
            }
            await db.predictions.insert_one(doc)
    except Exception as e:
        logger.warning(f"Prediction logging failed: {e}")


@api.post("/start-sit")
async def start_sit(payload: StartSitIn):
    """Rank a list of player IDs (the user's roster) and recommend who to start."""
    if not payload.player_ids:
        raise HTTPException(400, "Provide at least 1 player_id")
    cursor = db.players.find({"id": {"$in": payload.player_ids}}, {"_id": 0, "news": 0})
    items = await cursor.to_list(length=200)
    items = [_attach_current_season(p, None, payload.scoring) for p in items]

    out = []
    for p in items:
        score, factors = _player_lineup_score(p, payload.scoring)
        out.append({
            "id": p["id"], "name": p["name"], "position": p["position"], "team": p["team"],
            "tag": p.get("tag"),
            "lineup_score": score, "factors": factors,
            "reasoning": _reasoning_text(p, factors),
            "current_fpts_per_game": p.get("current_fpts_per_game"),
        })
    out.sort(key=lambda x: x["lineup_score"], reverse=True)

    if payload.slot and payload.slot != "FLEX":
        out_filtered = [p for p in out if p["position"] == payload.slot]
    elif payload.slot == "FLEX":
        out_filtered = [p for p in out if p["position"] in ("RB", "WR", "TE")]
    else:
        out_filtered = out

    return {
        "scoring": payload.scoring,
        "slot": payload.slot,
        "ranked": out_filtered,
        "recommendation": out_filtered[0] if out_filtered else None,
    }


# ---------- Rookies ----------
def _draft_round(dn: Optional[int]) -> Optional[int]:
    if not dn:
        return None
    return min(7, ((dn - 1) // 32) + 1)


# ---------- Lineups (auth) ----------
@api.post("/lineups")
async def save_lineup(payload: LineupIn, request: Request):
    user = await require_user(request, db)
    doc = {
        "id": str(uuid.uuid4()), "user_id": user["id"],
        "title": payload.title, "scoring": payload.scoring,
        "starters": [s.model_dump() for s in payload.starters],
        "bench": payload.bench,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.lineups.insert_one({**doc})
    return doc


@api.get("/lineups/me")
async def my_lineups(request: Request):
    user = await require_user(request, db)
    rows = await db.lineups.find({"user_id": user["id"]}, {"_id": 0}).to_list(length=200)
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return rows


@api.delete("/lineups/{lineup_id}")
async def delete_lineup(lineup_id: str, request: Request):
    user = await require_user(request, db)
    res = await db.lineups.delete_one({"id": lineup_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Lineup not found")
    return {"ok": True}


# ---------- Predictions / Self-Learning ----------
@api.post("/predictions")
async def log_prediction(payload: PredictionIn, request: Request):
    """Log a Lab Score prediction. Used for self-learning accuracy tracking."""
    user = await get_current_user_from_request(request, db)
    p = await db.players.find_one({"id": payload.player_id}, {"_id": 0, "name": 1, "position": 1, "team": 1})
    if not p:
        raise HTTPException(404, "Player not found")
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": (user or {}).get("id"),
        "player_id": payload.player_id,
        "player_name": p["name"], "position": p["position"], "team": p["team"],
        "scoring": payload.scoring,
        "predicted_fpts": payload.predicted_fpts,
        "actual_fpts": None,
        "week": payload.week, "season": payload.season,
        "source": payload.source,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "settled_at": None,
    }
    await db.predictions.insert_one({**doc})
    return doc


@api.get("/predictions/stats")
async def prediction_stats():
    """Return self-learning accuracy summary: total predictions, settled, MAE per position."""
    pipeline = [
        {"$match": {"actual_fpts": {"$ne": None}}},
        {"$group": {
            "_id": "$position",
            "n": {"$sum": 1},
            "mae_sum": {"$sum": {"$abs": {"$subtract": ["$predicted_fpts", "$actual_fpts"]}}},
            "bias_sum": {"$sum": {"$subtract": ["$predicted_fpts", "$actual_fpts"]}},
        }},
    ]
    rows = await db.predictions.aggregate(pipeline).to_list(length=100)
    by_pos = {}
    for r in rows:
        n = max(r["n"], 1)
        by_pos[r["_id"]] = {
            "n": r["n"],
            "mae": round(r["mae_sum"] / n, 2),
            "bias": round(r["bias_sum"] / n, 2),  # positive = over-predicted
        }
    total = await db.predictions.count_documents({})
    settled = await db.predictions.count_documents({"actual_fpts": {"$ne": None}})
    return {
        "total": total, "settled": settled, "pending": total - settled,
        "by_position": by_pos,
    }


@api.post("/predictions/settle")
async def settle_predictions(request: Request):
    """When new seasonal data is available, score open predictions (admin only)."""
    user = await require_user(request, db)
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    open_preds = await db.predictions.find({"actual_fpts": None}, {"_id": 0}).to_list(length=10000)
    settled = 0
    for pred in open_preds:
        p = await db.players.find_one({"id": pred["player_id"]}, {"_id": 0})
        if not p:
            continue
        # Match by season if specified, else most recent season
        season = pred.get("season")
        target = None
        for s in p.get("seasons", []):
            if season and s.get("season") == season:
                target = s
                break
        if target is None and p.get("seasons"):
            target = max(p["seasons"], key=lambda s: s.get("season", 0))
        if target:
            actual = target.get(f"fpts_per_game_{pred['scoring']}", 0)
            await db.predictions.update_one(
                {"id": pred["id"]},
                {"$set": {"actual_fpts": actual, "settled_at": datetime.now(timezone.utc).isoformat()}},
            )
            settled += 1
    return {"settled": settled}


# ---------- This Week's Edge ----------
@api.get("/this-week")
async def this_week(scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr"):
    """Aggregate top 10 best plays + top 5 fades for the upcoming week."""
    cursor = db.players.find({"position": {"$in": ["QB", "RB", "WR", "TE"]}}, {"_id": 0, "news": 0})
    items = await cursor.to_list(length=2000)
    items = [_attach_current_season(p, None, scoring) for p in items]
    items = [p for p in items if p.get("current_season")]

    scored = []
    for p in items:
        score, factors = _player_lineup_score(p, scoring)
        info = get_next_opponent(p.get("team") or "")
        scored.append({
            "id": p["id"], "name": p["name"], "position": p["position"], "team": p["team"],
            "tag": p.get("tag"),
            "lineup_score": score, "factors": factors,
            "opponent": info["opponent"] if info else None,
            "matchup_score": factors["matchup_score"],
            "current_fpts_per_game": p.get("current_fpts_per_game"),
            "news_search_url": player_news_search_url(p["name"]),
        })

    # Plays = high matchup_score + decent fppg
    plays = sorted(
        [p for p in scored if (p["current_fpts_per_game"] or 0) >= 8],
        key=lambda x: x["matchup_score"] + (x["current_fpts_per_game"] or 0) / 5,
        reverse=True,
    )[:10]

    # Fades = elite/breakout players in tough matchups
    fades = sorted(
        [p for p in scored if p.get("tag") in ("elite", "breakout") and p["matchup_score"] < 0],
        key=lambda x: x["matchup_score"],
    )[:5]

    return {"scoring": scoring, "plays": plays, "fades": fades}


# ---------- News URL helper ----------
@api.get("/players/{player_id}/news-url")
async def news_url(player_id: str):
    p = await db.players.find_one({"id": player_id}, {"_id": 0, "name": 1})
    if not p:
        raise HTTPException(404, "Player not found")
    return {"url": player_news_search_url(p["name"])}
# ---------- Rookies ----------
@api.get("/rookies")
async def list_rookies(scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr"):
    """Latest-class rookies. Pulled from rosters where years_exp==0 — includes 2025 rookies even when seasonal stats not yet published."""
    cursor = db.players.find({
        "rookie_info": {"$exists": True, "$ne": None},
    }, {"_id": 0})
    items = await cursor.to_list(length=500)

    if not items:
        return {"count": 0, "items": []}

   # Current year — only show players drafted this year or later (haven't played yet)
    current_year = datetime.now(timezone.utc).year
    items = [p for p in items if (p.get("rookie_info") or {}).get("rookie_year", 0) >= current_year]
    if not items:
        return {"count": 0, "rookie_year": None, "items": []}
    max_year = max((p.get("rookie_info", {}).get("rookie_year", 0) for p in items), default=0)
    items = [p for p in items if (p.get("rookie_info") or {}).get("rookie_year") == max_year]
    items = [_attach_current_season(p, None, scoring) for p in items]

    items.sort(key=lambda p: (p.get("rookie_info") or {}).get("draft_number") or 999)

    out = []
    for p in items:
        info = get_next_opponent(p.get("team") or "")
        opp = info["opponent"] if info else None
        rinfo = p.get("rookie_info") or {}
        dn = rinfo.get("draft_number") or 999
        outlook_label = "elite_landing" if dn <= 32 else "sleeper" if dn <= 100 else "deep_dart"
        out.append({
            "id": p["id"], "name": p["name"], "position": p["position"], "team": p["team"],
            "age": p.get("age"), "tag": p.get("tag"),
            "rookie_info": rinfo,
            "rookie_year": rinfo.get("rookie_year"),
            "draft_number": rinfo.get("draft_number"),
            "draft_round": _draft_round(rinfo.get("draft_number")),
            "college": rinfo.get("college"),
            "outlook_label": outlook_label,
            "next_opponent": opp,
            "matchup_def_rank": get_def_rank(opp, p["position"]) if opp else None,
            "current_fpts_per_game": p.get("current_fpts_per_game"),
            "news_search_url": player_news_search_url(p["name"]),
        })
    return {"count": len(out), "rookie_year": max_year, "items": out}


def _draft_round(dn: Optional[int]) -> Optional[int]:
    if not dn:
        return None
    return min(7, ((dn - 1) // 32) + 1)





# ---------- Defense rankings ----------
@api.get("/defense-rankings")
async def defense_rankings():
    """Returns live computed DvP if available, else static fallback.
    Shape: {source, data: {position: {team: {rank, fpts_allowed_per_game, games, season}}}}"""
    return get_dvp_table()


# ---------- This-week best/worst matchups widget ----------
@api.get("/matchups/this-week")
async def matchups_this_week():
    """Live best/worst defenses being faced this week.
    Combines live next-opponent map with live DvP. Output: 5 softest + 5 toughest per position."""
    dvp = get_dvp_table()
    data = dvp.get("data", {})
    # Build set of (offense_team, opp_team, week) from current schedule cache via get_next_opponent on every NFL team
    teams = await db.players.distinct("team", {"team": {"$ne": ""}})
    week = None
    rows: list[dict] = []
    for t in teams:
        if not t or len(t) > 4:
            continue
        info = get_next_opponent(t)
        if not info or not info.get("opponent"):
            continue
        opp = info["opponent"]
        week = info.get("week") or week
        for pos in ("QB", "RB", "WR", "TE"):
            cell = data.get(pos, {}).get(opp)
            if not cell:
                continue
            rows.append({
                "offense_team": t, "opp_team": opp, "position": pos,
                "rank": cell.get("rank"),
                "fpts_allowed_per_game": cell.get("fpts_allowed_per_game"),
                "season": cell.get("season"),
            })
    # Best plays (offense facing softest D = highest rank)
    by_pos: dict[str, dict] = {}
    for pos in ("QB", "RB", "WR", "TE"):
        sub = [r for r in rows if r["position"] == pos]
        sub_soft = sorted(sub, key=lambda r: r["rank"] or 0, reverse=True)[:5]
        sub_tough = sorted(sub, key=lambda r: r["rank"] or 99)[:5]
        by_pos[pos] = {"soft": sub_soft, "tough": sub_tough}

    # DEF matchups — best defenses face weakest offenses
    # Use average offensive rank (how many pts the offense scores vs defenses)
    # Proxy: teams facing the toughest defenses (rank 1-5) = hardest matchup for DEF
    # Teams facing the softest defenses (rank 28-32) = easiest matchup for DEF
    def_rows = []
    for t in teams:
        if not t or len(t) > 4:
            continue
        info = get_next_opponent(t)
        if not info or not info.get("opponent"):
            continue
        opp = info["opponent"]
        # Average DvP rank across all positions as proxy for offensive strength
        pos_ranks = []
        for pos in ("QB", "RB", "WR", "TE"):
            cell = data.get(pos, {}).get(t)
            if cell and cell.get("rank"):
                pos_ranks.append(cell["rank"])
        if not pos_ranks:
            continue
        avg_rank = sum(pos_ranks) / len(pos_ranks)
        # High avg_rank = soft defense = good for offense = bad for DEF streaming
        # Low avg_rank = tough defense = bad for offense = good for DEF streaming
        def_rows.append({
            "offense_team": t,
            "opp_team": opp,
            "position": "DEF",
            "rank": round(avg_rank, 1),
            "fpts_allowed_per_game": None,
            "season": next((data.get(pos, {}).get(t, {}).get("season") for pos in ("QB", "RB", "WR", "TE") if data.get(pos, {}).get(t)), None),
        })

    # For DEF: "soft" means facing a weak offense (low avg rank = tough D = good for streaming)
    # "tough" means facing a strong offense
    def_soft = sorted(def_rows, key=lambda r: r["rank"] or 16)[:5]   # face weakest offenses
    def_tough = sorted(def_rows, key=lambda r: r["rank"] or 16, reverse=True)[:5]  # face strongest offenses
    by_pos["DEF"] = {"soft": def_soft, "tough": def_tough}

    return {"week": week, "source": dvp.get("source"), "by_position": by_pos}


# ---------- Trade Analyzer ----------
class TradeIn(BaseModel):
    side_a_label: Optional[str] = "You give"
    side_b_label: Optional[str] = "You get"
    side_a_player_ids: List[str]
    side_b_player_ids: List[str]
    scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr"


def _trade_side_breakdown(items: list[dict], scoring: str) -> dict:
    """Score each player on a trade side using the live Lab Score (injury + matchup + tag aware)."""
    scored = []
    total = 0.0
    for p in items:
        score, factors = _player_lineup_score_v2(p, scoring)
        slim = {
            "id": p["id"], "name": p["name"], "position": p["position"], "team": p["team"],
            "tag": p.get("tag"),
            "lineup_score": score, "factors": factors,
            "current_fpts_per_game": p.get("current_fpts_per_game"),
            "injury_status": p.get("injury_status"),
            "next_opponent": factors.get("opponent"),
        }
        scored.append(slim)
        total += score
    scored.sort(key=lambda x: x["lineup_score"], reverse=True)
    return {"players": scored, "total_lab_score": round(total, 2)}


@api.post("/trade/analyze")
async def analyze_trade(payload: TradeIn):
    """Analyze a fantasy trade. Uses live injuries + DvP + tags to score each side, then asks Claude
    for a concise verdict factoring in the same live signals."""
    if not payload.side_a_player_ids or not payload.side_b_player_ids:
        raise HTTPException(400, "Provide at least 1 player on each side")
    all_ids = list(set(payload.side_a_player_ids + payload.side_b_player_ids))
    cursor = db.players.find({"id": {"$in": all_ids}}, {"_id": 0, "news": 0})
    players = await cursor.to_list(length=200)
    players = [_attach_current_season(p, None, payload.scoring) for p in players]
    # Apply learned bias before scoring (consistent with lineup endpoints)
    bias = await _learned_bias_by_position()
    for p in players:
        p["_lab_correction"] = -1 * bias.get(p["position"], 0)

    by_id = {p["id"]: p for p in players}
    side_a_items = [by_id[i] for i in payload.side_a_player_ids if i in by_id]
    side_b_items = [by_id[i] for i in payload.side_b_player_ids if i in by_id]
    if len(side_a_items) != len(payload.side_a_player_ids) or len(side_b_items) != len(payload.side_b_player_ids):
        raise HTTPException(404, "One or more player IDs not found")

    side_a = _trade_side_breakdown(side_a_items, payload.scoring)
    side_b = _trade_side_breakdown(side_b_items, payload.scoring)

    diff = round(side_b["total_lab_score"] - side_a["total_lab_score"], 2)
    # Verdict label
    if abs(diff) < 1.5:
        verdict = "fair"
    elif diff > 6:
        verdict = "side_b_strongly_wins"
    elif diff > 1.5:
        verdict = "side_b_wins"
    elif diff < -6:
        verdict = "side_a_strongly_wins"
    else:
        verdict = "side_a_wins"

    # AI commentary — concise, uses live factors
    from .llm_service import generate_trade_verdict
    commentary = await generate_trade_verdict(
        side_a_label=payload.side_a_label or "Side A",
        side_b_label=payload.side_b_label or "Side B",
        side_a=side_a, side_b=side_b,
        diff=diff, verdict=verdict, scoring=payload.scoring,
    )

    return {
        "scoring": payload.scoring,
        "side_a_label": payload.side_a_label,
        "side_b_label": payload.side_b_label,
        "side_a": side_a,
        "side_b": side_b,
        "diff": diff,
        "verdict": verdict,
        "commentary": commentary,
        "data_freshness": {
            "uses_live_injuries": True,
            "uses_live_dvp": True,
            "uses_live_schedule": True,
        },
    }


# ---------- Teams ----------
@api.get("/teams")
async def teams(sport: Optional[str] = None):
    q = {}
    if sport and sport != "nfl":
        q["sport"] = sport
    pipeline = [{"$match": q}, {"$group": {"_id": "$team"}}, {"$sort": {"_id": 1}}]
    rows = await db.players.aggregate(pipeline).to_list(length=200)
    return [r["_id"] for r in rows if r["_id"]]


# ---------- Rankings (auth) ----------
@api.post("/rankings")
async def create_ranking(payload: RankingIn, request: Request):
    user = await require_user(request, db)
    doc = {
        "id": str(uuid.uuid4()), "user_id": user["id"],
        "title": payload.title, "scoring": payload.scoring,
        "player_ids": payload.player_ids, "notes": payload.notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.rankings.insert_one({**doc})
    return doc


@api.get("/rankings/me")
async def my_rankings(request: Request):
    user = await require_user(request, db)
    rows = await db.rankings.find({"user_id": user["id"]}, {"_id": 0}).to_list(length=200)
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return rows


@api.delete("/rankings/{ranking_id}")
async def delete_ranking(ranking_id: str, request: Request):
    user = await require_user(request, db)
    res = await db.rankings.delete_one({"id": ranking_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Ranking not found")
    return {"ok": True}


# ---------- CSV upload ----------
def _safe_num(v):
    try:
        if v is None or v == "":
            return 0
        if "." in str(v):
            return float(v)
        return int(v)
    except (ValueError, TypeError):
        return 0


@api.post("/upload/csv")
async def upload_csv(request: Request, file: UploadFile = File(...)):
    """Expects: name,position,team,season,games,pass_yds,pass_td,pass_int,rush_yds,rush_td,receptions,rec_yds,rec_td,fumbles_lost"""
    await require_user(request, db)
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(400, "Must upload a .csv file")
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8", errors="ignore")))
    upserts = 0
    for row in reader:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        season_row = {k: _safe_num(v) for k, v in row.items() if k not in ("name", "position", "team", "age", "experience")}
        # Compute fpts
        from nfl_data_service import _compute_fp  # local helper
        srow = {
            "passing_yards": season_row.get("pass_yds", 0),
            "passing_tds": season_row.get("pass_td", 0),
            "interceptions": season_row.get("pass_int", 0),
            "rushing_yards": season_row.get("rush_yds", 0),
            "rushing_tds": season_row.get("rush_td", 0),
            "receptions": season_row.get("receptions", 0),
            "receiving_yards": season_row.get("rec_yds", 0),
            "receiving_tds": season_row.get("rec_td", 0),
        }
        games = season_row.get("games", 17) or 17
        season_row["fpts_standard"] = _compute_fp(srow, "standard")
        season_row["fpts_half_ppr"] = _compute_fp(srow, "half_ppr")
        season_row["fpts_ppr"] = _compute_fp(srow, "ppr")
        season_row["fpts_per_game_standard"] = round(season_row["fpts_standard"] / max(games, 1), 2)
        season_row["fpts_per_game_half_ppr"] = round(season_row["fpts_half_ppr"] / max(games, 1), 2)
        season_row["fpts_per_game_ppr"] = round(season_row["fpts_ppr"] / max(games, 1), 2)
        season_row["total_yards"] = season_row.get("pass_yds", 0) + season_row.get("rush_yds", 0) + season_row.get("rec_yds", 0)
        season_row["total_tds"] = season_row.get("pass_td", 0) + season_row.get("rush_td", 0) + season_row.get("rec_td", 0)

        existing = await db.players.find_one({"name": name})
        if existing:
            seasons = existing.get("seasons", [])
            seasons = [s for s in seasons if s.get("season") != season_row.get("season")]
            seasons.append(season_row)
            seasons.sort(key=lambda s: s.get("season", 0))
            await db.players.update_one({"id": existing["id"]}, {"$set": {"seasons": seasons}})
        else:
            await db.players.insert_one({
                "id": str(uuid.uuid4()), "name": name,
                "position": row.get("position", "").strip(),
                "team": row.get("team", "").strip(),
                "age": _safe_num(row.get("age", 0)),
                "experience": _safe_num(row.get("experience", 0)),
                "tag": None, "seasons": [season_row], "news": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        upserts += 1
    return {"imported": upserts}


# ---------- Admin: refresh data ----------
@api.post("/admin/refresh-injuries")
async def refresh_injuries_ep(request: Request):
    """Pull live injuries from ESPN and update player records + Lab Score."""
    user = await require_user(request, db)
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    return await refresh_injuries(db)

@api.post("/admin/refresh-nba")
async def refresh_nba(request: Request, force: bool = False):
    user = await require_user(request, db)
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    from .nba_data_service import refresh_nba_data
    result = await refresh_nba_data(db, force=force)
    return result

@api.post("/admin/refresh-mlb")
async def refresh_mlb(request: Request, force: bool = False):
    user = await require_user(request, db)
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    from .mlb_data_service import refresh_mlb_data
    result = await refresh_mlb_data(db, force=force)
    return result

@api.post("/admin/refresh-data")
async def refresh_data(request: Request, force: bool = True):
    """Re-pull latest player data from nfl-data-py (nflverse)."""
    user = await require_user(request, db)
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    result = await refresh_player_data(db, force=force)
    return result


@api.get("/admin/data-status")
async def data_status():
    meta = await db.meta.find_one({"key": "last_refresh"}, {"_id": 0})
    inj_meta = await db.meta.find_one({"key": "last_injury_refresh"}, {"_id": 0})
    count = await db.players.count_documents({})
    injured = await db.players.count_documents({"injury_status": {"$exists": True, "$ne": None}})
    return {
        "last_refresh": meta,
        "last_injury_refresh": inj_meta,
        "player_count": count,
        "injured_count": injured,
    }


# ---------- Health ----------
@api.get("/")
async def health():
    return {"status": "ok", "service": "fantasy-lab"}


@api.get("/stats/summary")
async def stats_summary():
    meta = await db.meta.find_one({"key": "last_refresh"}, {"_id": 0})
    inj_meta = await db.meta.find_one({"key": "last_injury_refresh"}, {"_id": 0})
    seasons = (meta or {}).get("seasons") if meta else []
    return {
        "total_players": await db.players.count_documents({}),
        "total_users": await db.users.count_documents({}),
        "total_rankings": await db.rankings.count_documents({}),
        "data_seasons": seasons or [],
        "last_refresh": (meta or {}).get("value") if meta else None,
        "last_injury_refresh": (inj_meta or {}).get("value") if inj_meta else None,
        "injuries_matched": (inj_meta or {}).get("matched") if inj_meta else None,
    }


# ---------- Startup ----------
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.players.create_index("id", unique=True)
    await db.players.create_index("ext_id", sparse=True)
    await db.players.create_index("name")
    await db.players.create_index("position")
    await db.players.create_index("team")
    await db.players.create_index("tag", sparse=True)
    await db.players.create_index("experience", sparse=True)
    await db.rankings.create_index("user_id")
    await db.lineups.create_index("user_id")
    await db.predictions.create_index("player_id")
    await db.predictions.create_index("user_id", sparse=True)
    await db.predictions.create_index("settled_at", sparse=True)
    await db.outlooks.create_index([("player_id", 1), ("scoring", 1)], unique=True)

    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    if not await db.users.find_one({"email": admin_email}):
        await db.users.insert_one({
            "id": str(uuid.uuid4()), "email": admin_email, "name": "Admin", "role": "admin",
            "password_hash": hash_password(admin_password),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Admin user seeded: {admin_email}")
    if not await db.users.find_one({"email": "user@ffref.com"}):
        await db.users.insert_one({
            "id": str(uuid.uuid4()), "email": "user@ffref.com", "name": "Test User", "role": "user",
            "password_hash": hash_password("user123"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    # Hydrate persisted DvP + next-opp caches before any request hits us
    dvp_meta = await db.meta.find_one({"key": "dvp_live"}, {"_id": 0})
    if dvp_meta and dvp_meta.get("value"):
        hydrate_dvp_cache(dvp_meta["value"])
        logger.info(f"Hydrated DvP cache: {sum(len(v) for v in dvp_meta['value'].values())} cells")
    no_meta = await db.meta.find_one({"key": "next_opp"}, {"_id": 0})
    if no_meta and no_meta.get("value"):
        hydrate_next_opp_cache(no_meta["value"])
        logger.info(f"Hydrated next-opp cache: {len(no_meta['value'])} teams")

    # Refresh real data in background — don't block startup
    async def _bg_refresh():
        try:
            res = await refresh_player_data(db, force=False)
            logger.info(f"Player data refresh: {res}")
        except Exception as e:
            logger.exception(f"Background refresh failed: {e}")
    asyncio.create_task(_bg_refresh())


@app.on_event("shutdown")
async def shutdown():
    client.close()

app.include_router(api, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
    
