"""Comprehensive backend tests for Fantasy Football Reference app."""
import os
import io
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://fantasy-depth-chart.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@ffref.com"
ADMIN_PASSWORD = "admin123"
USER_EMAIL = "user@ffref.com"
USER_PASSWORD = "user123"


def _items(resp_json):
    """Players endpoint returns {count, items}."""
    if isinstance(resp_json, dict) and "items" in resp_json:
        return resp_json["items"]
    return resp_json


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def auth_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": USER_EMAIL, "password": USER_PASSWORD})
    if r.status_code != 200:
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Auth login failed: {r.status_code} {r.text}"
    return s


# ==== Health & Stats ====
class TestHealth:
    def test_root(self, session):
        r = session.get(f"{API}/")
        assert r.status_code == 200

    def test_stats_summary(self, session):
        r = session.get(f"{API}/stats/summary")
        assert r.status_code == 200
        d = r.json()
        assert d["total_players"] > 0
        assert "total_users" in d
        assert "total_rankings" in d


# ==== Players ====
class TestPlayers:
    def test_list_default(self, session):
        r = session.get(f"{API}/players")
        assert r.status_code == 200
        items = _items(r.json())
        assert isinstance(items, list) and len(items) > 0
        p = items[0]
        assert "id" in p and "current_season" in p and "current_fpts" in p

    def test_filter_position(self, session):
        r = session.get(f"{API}/players", params={"position": "QB"})
        items = _items(r.json())
        assert len(items) > 0
        assert all(p["position"] == "QB" for p in items)

    def test_filter_season(self, session):
        r = session.get(f"{API}/players", params={"season": 2023})
        items = _items(r.json())
        assert len(items) > 0
        # current_season is a dict; ensure season field equals 2023
        assert all(
            (isinstance(p["current_season"], dict) and p["current_season"].get("season") == 2023)
            for p in items
        )

    def test_filter_team(self, session):
        teams = session.get(f"{API}/teams").json()
        assert len(teams) > 0
        r = session.get(f"{API}/players", params={"team": teams[0]})
        assert r.status_code == 200

    def test_search(self, session):
        r = session.get(f"{API}/players", params={"search": "Mahomes"})
        items = _items(r.json())
        assert any("Mahomes" in p.get("name", "") for p in items)

    def test_sort_fpts_desc(self, session):
        # backend sort defaults to current_fpts; default direction desc
        r = session.get(f"{API}/players", params={"sort": "current_fpts", "direction": "desc"})
        items = _items(r.json())
        fpts = [p["current_fpts"] for p in items]
        assert fpts == sorted(fpts, reverse=True)

    def test_scoring_param(self, session):
        r1 = session.get(f"{API}/players", params={"scoring": "half_ppr"})
        r2 = session.get(f"{API}/players", params={"scoring": "ppr"})
        assert r1.status_code == 200 and r2.status_code == 200

    def test_player_detail(self, session):
        items = _items(session.get(f"{API}/players").json())
        pid = items[0]["id"]
        r = session.get(f"{API}/players/{pid}")
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == pid
        assert isinstance(d.get("seasons"), list)

    def test_player_404(self, session):
        r = session.get(f"{API}/players/nonexistent-id-xyz")
        assert r.status_code == 404


class TestTeams:
    def test_list(self, session):
        r = session.get(f"{API}/teams")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, list) and len(d) > 0


class TestSleepersBusts:
    def test_buckets(self, session):
        r = session.get(f"{API}/sleepers-busts")
        assert r.status_code == 200
        d = r.json()
        for k in ("sleepers", "busts", "breakouts", "elites"):
            assert k in d and isinstance(d[k], list)


class TestAuth:
    def test_register_and_me(self):
        email = f"test_user_{int(time.time())}@example.com"
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        r = s.post(f"{API}/auth/register", json={"email": email, "password": "Password123!", "name": "TestU"})
        assert r.status_code in (200, 201), r.text
        r2 = s.get(f"{API}/auth/me")
        assert r2.status_code == 200
        assert r2.json()["email"].lower() == email.lower()

    def test_login_admin_sets_cookies(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200, r.text
        names = {c.name for c in s.cookies}
        assert "access_token" in names and "refresh_token" in names
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == ADMIN_EMAIL

    def test_invalid_login(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrongpass!"})
        assert r.status_code in (400, 401, 403)

    def test_refresh_and_logout(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": USER_EMAIL, "password": USER_PASSWORD})
        assert r.status_code == 200
        rr = s.post(f"{API}/auth/refresh")
        assert rr.status_code == 200
        out = s.post(f"{API}/auth/logout")
        assert out.status_code == 200
        me = s.get(f"{API}/auth/me")
        assert me.status_code in (401, 403)


class TestRankings:
    created_id = None

    def test_create_ranking(self, auth_session):
        items = _items(requests.get(f"{API}/players").json())[:3]
        payload = {
            "title": "TEST_Ranking",
            "scoring": "half_ppr",
            "player_ids": [p["id"] for p in items],
            "notes": "test",
        }
        r = auth_session.post(f"{API}/rankings", json=payload)
        assert r.status_code in (200, 201), r.text
        d = r.json()
        assert "id" in d
        assert d["title"] == "TEST_Ranking"
        assert len(d["player_ids"]) == 3
        TestRankings.created_id = d["id"]

    def test_list_my_rankings(self, auth_session):
        r = auth_session.get(f"{API}/rankings/me")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, list)
        if TestRankings.created_id:
            assert any(x["id"] == TestRankings.created_id for x in d)

    def test_delete_ranking(self, auth_session):
        if not TestRankings.created_id:
            pytest.skip("no ranking created")
        r = auth_session.delete(f"{API}/rankings/{TestRankings.created_id}")
        assert r.status_code in (200, 204)
        listing = auth_session.get(f"{API}/rankings/me").json()
        assert not any(x["id"] == TestRankings.created_id for x in listing)

    def test_rankings_requires_auth(self):
        r = requests.get(f"{API}/rankings/me")
        assert r.status_code in (401, 403)


class TestCSVUpload:
    def test_upload_csv(self):
        csv_content = (
            "name,position,team,season,games,pass_yds,pass_td,pass_int,rush_yds,rush_td,receptions,rec_yds,rec_td,fumbles_lost\n"
            "TEST_Player_A,RB,KC,2024,17,0,0,0,1200,10,40,300,2,1\n"
        )
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        s = requests.Session()
        login = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert login.status_code == 200
        r = s.post(f"{API}/upload/csv", files=files)
        assert r.status_code in (200, 201), r.text


class TestOutlook:
    def test_outlook_generation(self, session):
        items = _items(session.get(f"{API}/players").json())
        pid = items[0]["id"]
        r = session.get(f"{API}/players/{pid}/outlook", timeout=90)
        assert r.status_code == 200
        d = r.json()
        assert d is not None
        assert d.get("outlook") and isinstance(d["outlook"], str) and len(d["outlook"]) > 20


# ==== Iteration 2 features ====
class TestLineup:
    def test_lineup_suggest(self, session):
        r = session.get(f"{API}/lineup/suggest", params={"scoring": "half_ppr"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["scoring"] == "half_ppr"
        assert "starters" in d and "bench_alternatives" in d
        starters = d["starters"]
        # 1 QB / 2 RB / 2 WR / 1 TE / 1 FLEX
        assert len(starters["QB"]) == 1
        assert len(starters["RB"]) == 2
        assert len(starters["WR"]) == 2
        assert len(starters["TE"]) == 1
        assert len(starters["FLEX"]) == 1
        # FLEX must be RB/WR/TE
        flex = starters["FLEX"][0]
        assert flex["position"] in ("RB", "WR", "TE")
        # Each starter has lineup_score, reasoning, factors
        for slot, players in starters.items():
            for p in players:
                assert "lineup_score" in p and isinstance(p["lineup_score"], (int, float))
                assert p.get("reasoning") and isinstance(p["reasoning"], str)
                assert "factors" in p and "fppg" in p["factors"]
        # No duplicates across starters
        starter_ids = [p["id"] for arr in starters.values() for p in arr]
        assert len(starter_ids) == len(set(starter_ids))


class TestStartSit:
    def test_start_sit_basic(self, session):
        items = _items(session.get(f"{API}/players", params={"position": "RB"}).json())[:3]
        ids = [p["id"] for p in items]
        r = session.post(f"{API}/start-sit", json={"player_ids": ids, "scoring": "half_ppr"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert "ranked" in d and "recommendation" in d
        assert len(d["ranked"]) == 3
        # recommendation is the first ranked
        assert d["recommendation"]["id"] == d["ranked"][0]["id"]
        # sorted desc
        scores = [p["lineup_score"] for p in d["ranked"]]
        assert scores == sorted(scores, reverse=True)
        for p in d["ranked"]:
            assert p.get("reasoning") and "factors" in p

    def test_start_sit_slot_filter(self, session):
        rbs = _items(session.get(f"{API}/players", params={"position": "RB"}).json())[:2]
        wrs = _items(session.get(f"{API}/players", params={"position": "WR"}).json())[:2]
        ids = [p["id"] for p in rbs + wrs]
        r = session.post(f"{API}/start-sit", json={"player_ids": ids, "scoring": "half_ppr", "slot": "RB"})
        assert r.status_code == 200
        d = r.json()
        assert all(p["position"] == "RB" for p in d["ranked"])
        # FLEX
        r2 = session.post(f"{API}/start-sit", json={"player_ids": ids, "slot": "FLEX"})
        d2 = r2.json()
        assert all(p["position"] in ("RB", "WR", "TE") for p in d2["ranked"])

    def test_start_sit_empty(self, session):
        r = session.post(f"{API}/start-sit", json={"player_ids": []})
        assert r.status_code == 400


class TestDefenseRankings:
    def test_def_rankings(self, session):
        r = session.get(f"{API}/defense-rankings")
        assert r.status_code == 200
        d = r.json()
        for pos in ("QB", "RB", "WR", "TE"):
            assert pos in d
            assert isinstance(d[pos], dict)
            # Each team should have an integer rank
            for team, rank in d[pos].items():
                assert isinstance(rank, int) and 1 <= rank <= 32


class TestPlayerMatchup:
    def test_player_has_matchup_fields(self, session):
        items = _items(session.get(f"{API}/players").json())
        # Find a player with a non-empty team
        target = next((p for p in items if p.get("team")), None)
        assert target is not None
        r = session.get(f"{API}/players/{target['id']}")
        assert r.status_code == 200
        d = r.json()
        # next_opponent may be None for some teams; if present, matchup_def_rank should be set
        if d.get("next_opponent"):
            assert "matchup_def_rank" in d
            assert isinstance(d["matchup_def_rank"], int)


class TestAdminDataStatus:
    def test_data_status(self, session):
        r = session.get(f"{API}/admin/data-status")
        assert r.status_code == 200
        d = r.json()
        assert "player_count" in d
        assert isinstance(d["player_count"], int)
        assert d["player_count"] > 0
        # last_refresh may be None on cold start; if present should be dict with value
        assert "last_refresh" in d


class TestPlayerCounts:
    def test_player_counts_by_position(self, session):
        d = {}
        for pos in ("QB", "RB", "WR", "TE"):
            items = _items(session.get(f"{API}/players", params={"position": pos, "limit": 1000}).json())
            d[pos] = len(items)
        # Expected ~32 QB, 75 RB, 75 WR, 35 TE per spec; allow some flex
        total = sum(d.values())
        assert total >= 150, f"Expected ~217 players, got {total}: {d}"
        assert d["QB"] >= 20
        assert d["RB"] >= 50
        assert d["WR"] >= 50
        assert d["TE"] >= 20
