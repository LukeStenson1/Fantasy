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

from auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    set_auth_cookies, clear_auth_cookies,
    get_current_user_from_request, require_user,
)
from llm_service import generate_player_outlook
from nfl_data_service import (
    refresh_player_data, get_def_rank, matchup_score,
    NEXT_OPPONENT, DEF_VS_POS_2024,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("ffref")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Fantasy Lab API")
api = APIRouter(prefix="/api")


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


# ---------- Player Stats ----------
def _attach_current_season(p: dict, season: Optional[int], scoring: str):
    seasons = p.get("seasons", [])
    cur = None
    if season is not None:
        # Strict: only return the row for that season; if absent, leave None so caller filters out
        cur = next((s for s in seasons if s.get("season") == season), None)
    elif seasons:
        cur = max(seasons, key=lambda s: s.get("season", 0))
    p["current_season"] = cur
    if cur:
        p["current_fpts"] = cur.get(f"fpts_{scoring}", 0)
        p["current_fpts_per_game"] = cur.get(f"fpts_per_game_{scoring}", 0)
    return p


@api.get("/players")
async def list_players(
    position: Optional[str] = None,
    team: Optional[str] = None,
    season: Optional[int] = None,
    scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr",
    search: Optional[str] = None,
    sort: str = "current_fpts",
    direction: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=300, le=1000),
    tag: Optional[str] = None,
):
    q = {}
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
    # Add matchup info
    opp = NEXT_OPPONENT.get(p.get("team", ""), None)
    if opp:
        p["next_opponent"] = opp
        p["matchup_def_rank"] = get_def_rank(opp, p["position"])
        p["matchup_score"] = matchup_score(opp, p["position"])
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
async def sleepers_busts(scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr"):
    cursor = db.players.find({"tag": {"$ne": None}}, {"_id": 0, "news": 0})
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
    """Calculate a composite lineup score. Returns (score, factors_dict)."""
    cur = p.get("current_season") or {}
    fppg = cur.get(f"fpts_per_game_{scoring}", 0) or 0
    games = cur.get("games", 0) or 0

    # Matchup
    opp = NEXT_OPPONENT.get(p.get("team") or "", None)
    m_score = matchup_score(opp, p["position"]) if opp else 0
    def_rank = get_def_rank(opp, p["position"]) if opp else 16

    # Availability factor: penalize low games (injury)
    avail = 0.0
    if games < 8:
        avail = -2.0
    elif games < 13:
        avail = -0.5

    # Tag boost
    tag = p.get("tag")
    tag_boost = {"elite": 1.5, "breakout": 0.8, "sleeper": 0.4, "risk": -0.8}.get(tag, 0)

    score = round(fppg + m_score + avail + tag_boost, 2)
    factors = {
        "fppg": fppg,
        "matchup_score": m_score,
        "def_rank": def_rank,
        "opponent": opp,
        "availability": avail,
        "tag_boost": tag_boost,
        "tag": tag,
    }
    return score, factors


def _reasoning_text(p: dict, factors: dict) -> str:
    parts = []
    fppg = factors["fppg"]
    parts.append(f"{fppg:.1f} FPts/G last season")
    opp = factors["opponent"]
    rank = factors["def_rank"]
    if opp:
        if rank >= 24:
            parts.append(f"soft matchup vs {opp} (#{rank} D vs {p['position']})")
        elif rank <= 8:
            parts.append(f"tough matchup vs {opp} (#{rank} D vs {p['position']})")
        else:
            parts.append(f"neutral matchup vs {opp} (#{rank} D vs {p['position']})")
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
async def suggest_lineup(scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr"):
    """Suggest a starting lineup: 1QB / 2RB / 2WR / 1TE / 1FLEX."""
    cursor = db.players.find({"position": {"$in": ["QB", "RB", "WR", "TE"]}}, {"_id": 0, "news": 0})
    items = await cursor.to_list(length=2000)
    items = [_attach_current_season(p, None, scoring) for p in items]
    items = [p for p in items if p.get("current_season")]

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


# ---------- Defense rankings ----------
@api.get("/defense-rankings")
async def defense_rankings():
    return DEF_VS_POS_2024


# ---------- Teams ----------
@api.get("/teams")
async def teams():
    pipeline = [{"$group": {"_id": "$team"}}, {"$sort": {"_id": 1}}]
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
    count = await db.players.count_documents({})
    return {"last_refresh": meta, "player_count": count}


# ---------- Health ----------
@api.get("/")
async def health():
    return {"status": "ok", "service": "fantasy-lab"}


@api.get("/stats/summary")
async def stats_summary():
    meta = await db.meta.find_one({"key": "last_refresh"}, {"_id": 0})
    seasons = (meta or {}).get("seasons") if meta else []
    return {
        "total_players": await db.players.count_documents({}),
        "total_users": await db.users.count_documents({}),
        "total_rankings": await db.rankings.count_documents({}),
        "data_seasons": seasons or [],
        "last_refresh": (meta or {}).get("value") if meta else None,
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
    await db.rankings.create_index("user_id")
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


app.include_router(api)

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
allowed = [frontend_url, "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware, allow_origins=allowed, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
