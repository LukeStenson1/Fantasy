"""Fantasy Football Reference API."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import io
import csv
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Literal

from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

from auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    set_auth_cookies, clear_auth_cookies,
    get_current_user_from_request, require_user,
)
from seed_data import populate_db, _enrich_season
from llm_service import generate_player_outlook

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("ffref")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Fantasy Football Reference API")
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


# ---------- Auth ----------
@api.post("/auth/register")
async def register(payload: RegisterIn, response: Response):
    email = payload.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(400, "Email already registered")
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": email,
        "name": payload.name or email.split("@")[0],
        "role": "user",
        "password_hash": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    access = create_access_token(user_id, email)
    refresh = create_refresh_token(user_id)
    set_auth_cookies(response, access, refresh)
    return {"id": user_id, "email": email, "name": user["name"], "role": "user"}


@api.post("/auth/login")
async def login(payload: LoginIn, response: Response):
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    access = create_access_token(user["id"], email)
    refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, refresh)
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
async def refresh_token(request: Request, response: Response):
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
        access = create_access_token(user["id"], user["email"])
        new_refresh = create_refresh_token(user["id"])
        set_auth_cookies(response, access, new_refresh)
        return user
    except Exception as e:
        raise HTTPException(401, f"Invalid refresh token: {e}")


# ---------- Player Stats ----------
def _attach_current_season(p: dict, season: Optional[int], scoring: str):
    """Pick the season row that matches `season`, else most recent."""
    seasons = p.get("seasons", [])
    cur = None
    if season:
        cur = next((s for s in seasons if s.get("season") == season), None)
    if cur is None and seasons:
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
    limit: int = Query(default=200, le=500),
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
    items = await cursor.to_list(length=1000)
    items = [_attach_current_season(p, season, scoring) for p in items]
    items = [p for p in items if p.get("current_season")]
    reverse = direction == "desc"
    def keyfn(p):
        v = p.get(sort)
        if v is None and p.get("current_season"):
            v = p["current_season"].get(sort)
        return v if v is not None else float("-inf") if reverse else float("inf")
    items.sort(key=keyfn, reverse=reverse)
    return {"count": len(items), "items": items[:limit]}


@api.get("/players/{player_id}")
async def get_player(player_id: str, scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr"):
    p = await db.players.find_one({"id": player_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Player not found")
    p = _attach_current_season(p, None, scoring)
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
        "player_id": player_id,
        "scoring": scoring,
        "outlook": text,
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
        "player_id": player_id,
        "scoring": scoring,
        "outlook": text,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.outlooks.replace_one({"player_id": player_id, "scoring": scoring}, doc, upsert=True)
    return doc


# ---------- Sleepers / Busts ----------
@api.get("/sleepers-busts")
async def sleepers_busts(scoring: Literal["standard", "half_ppr", "ppr"] = "half_ppr"):
    cursor = db.players.find({}, {"_id": 0, "news": 0})
    items = await cursor.to_list(length=1000)
    sleepers, busts, breakouts, elites = [], [], [], []
    for p in items:
        p = _attach_current_season(p, None, scoring)
        if not p.get("current_season"):
            continue
        tag = p.get("tag")
        slim = {
            "id": p["id"], "name": p["name"], "position": p["position"], "team": p["team"],
            "tag": tag, "current_fpts": p.get("current_fpts"),
            "current_fpts_per_game": p.get("current_fpts_per_game"),
            "season": p["current_season"].get("season"),
        }
        if tag == "sleeper":
            sleepers.append(slim)
        elif tag == "risk":
            busts.append(slim)
        elif tag == "breakout":
            breakouts.append(slim)
        elif tag == "elite":
            elites.append(slim)
    return {"sleepers": sleepers, "busts": busts, "breakouts": breakouts, "elites": elites}


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
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "title": payload.title,
        "scoring": payload.scoring,
        "player_ids": payload.player_ids,
        "notes": payload.notes,
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


# ---------- CSV upload (backup data import) ----------
@api.post("/upload/csv")
async def upload_csv(request: Request, file: UploadFile = File(...)):
    """Expects CSV with columns: name,position,team,season,games,pass_yds,pass_td,pass_int,
    rush_yds,rush_td,receptions,rec_yds,rec_td,fumbles_lost"""
    await require_user(request, db)
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(400, "Must upload a .csv file")
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8", errors="ignore")))
    upserts = 0
    for row in reader:
        name = row.get("name", "").strip()
        if not name:
            continue
        season_row = {k: _safe_num(v) for k, v in row.items() if k not in ("name", "position", "team", "age", "experience")}
        season_row = _enrich_season(season_row)
        existing = await db.players.find_one({"name": name})
        if existing:
            seasons = existing.get("seasons", [])
            seasons = [s for s in seasons if s.get("season") != season_row.get("season")]
            seasons.append(season_row)
            seasons.sort(key=lambda s: s.get("season", 0))
            await db.players.update_one({"id": existing["id"]}, {"$set": {"seasons": seasons}})
        else:
            await db.players.insert_one({
                "id": str(uuid.uuid4()),
                "name": name,
                "position": row.get("position", "").strip(),
                "team": row.get("team", "").strip(),
                "age": _safe_num(row.get("age", 0)),
                "experience": _safe_num(row.get("experience", 0)),
                "tag": None,
                "seasons": [season_row],
                "news": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        upserts += 1
    return {"imported": upserts}


def _safe_num(v):
    try:
        if v is None or v == "":
            return 0
        if "." in str(v):
            return float(v)
        return int(v)
    except (ValueError, TypeError):
        return 0


# ---------- Health ----------
@api.get("/")
async def health():
    return {"status": "ok", "service": "fantasy-football-reference"}


@api.get("/stats/summary")
async def stats_summary():
    return {
        "total_players": await db.players.count_documents({}),
        "total_users": await db.users.count_documents({}),
        "total_rankings": await db.rankings.count_documents({}),
    }


# ---------- Startup ----------
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.players.create_index("id", unique=True)
    await db.players.create_index("name")
    await db.players.create_index("position")
    await db.players.create_index("team")
    await db.rankings.create_index("user_id")
    await db.outlooks.create_index([("player_id", 1), ("scoring", 1)], unique=True)

    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": admin_email,
            "name": "Admin",
            "role": "admin",
            "password_hash": hash_password(admin_password),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Admin user seeded: {admin_email}")

    # Seed test user
    test_email = "user@ffref.com"
    test_existing = await db.users.find_one({"email": test_email})
    if not test_existing:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": test_email,
            "name": "Test User",
            "role": "user",
            "password_hash": hash_password("user123"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Test user seeded: {test_email}")

    # Seed players
    count = await populate_db(db)
    logger.info(f"Players collection: {count} (seeded if was empty)")


@app.on_event("shutdown")
async def shutdown():
    client.close()


app.include_router(api)

# CORS — allow_credentials requires explicit origins
frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
allowed = [frontend_url, "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
