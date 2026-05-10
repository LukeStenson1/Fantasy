"""Iteration 3 backend tests: rookies, this-week, lineups, predictions, news-url, schedule integration."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://fantasy-depth-chart.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@ffref.com"
ADMIN_PASSWORD = "admin123"
USER_EMAIL = "user@ffref.com"
USER_PASSWORD = "user123"


def _items(j):
    if isinstance(j, dict) and "items" in j:
        return j["items"]
    return j


@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="session")
def user_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": USER_EMAIL, "password": USER_PASSWORD})
    assert r.status_code == 200, r.text
    return s


# ============ Rookies ============
class TestRookies:
    def test_rookies_endpoint(self):
        r = requests.get(f"{API}/rookies")
        assert r.status_code == 200, r.text
        d = r.json()
        assert "count" in d and "items" in d
        assert d["count"] > 0, "Expected 2025 rookie class"
        assert d.get("rookie_year") == 2025, f"rookie_year={d.get('rookie_year')}"

    def test_rookie_fields(self):
        d = requests.get(f"{API}/rookies").json()
        items = d["items"]
        assert len(items) > 10
        sample = items[0]
        for f in ("id", "name", "position", "team", "rookie_info", "outlook_label", "news_search_url"):
            assert f in sample, f"Missing {f}"
        assert sample["outlook_label"] in ("elite_landing", "sleeper", "deep_dart")
        # draft_round computed
        if sample.get("draft_number"):
            assert sample.get("draft_round") and 1 <= sample["draft_round"] <= 7

    def test_rookies_known_2025_names(self):
        d = requests.get(f"{API}/rookies").json()
        names = " ".join(p["name"] for p in d["items"])
        # At least one of the high-profile 2025 rookies should be present
        known = ["Cam Ward", "Travis Hunter", "Ashton Jeanty", "Tetairoa McMillan", "Omarion Hampton"]
        assert any(k in names for k in known), f"None of {known} found in rookies list"


# ============ This Week's Edge ============
class TestThisWeek:
    def test_this_week_basic(self):
        r = requests.get(f"{API}/this-week")
        assert r.status_code == 200, r.text
        d = r.json()
        assert "plays" in d and "fades" in d
        assert isinstance(d["plays"], list)
        assert isinstance(d["fades"], list)
        # plays should be up to 10
        assert len(d["plays"]) <= 10
        assert len(d["fades"]) <= 5

    def test_this_week_play_fields(self):
        d = requests.get(f"{API}/this-week").json()
        if d["plays"]:
            p = d["plays"][0]
            for f in ("id", "name", "position", "team", "matchup_score", "news_search_url"):
                assert f in p, f"Play missing {f}"


# ============ Lineups CRUD (auth) ============
class TestLineups:
    created_id = None

    def test_save_lineup(self, user_session):
        items = _items(requests.get(f"{API}/players").json())[:8]
        starters = [
            {"slot": "QB", "player_id": items[0]["id"]},
            {"slot": "RB1", "player_id": items[1]["id"]},
            {"slot": "RB2", "player_id": items[2]["id"]},
            {"slot": "WR1", "player_id": items[3]["id"]},
            {"slot": "WR2", "player_id": items[4]["id"]},
            {"slot": "TE", "player_id": items[5]["id"]},
            {"slot": "FLEX", "player_id": items[6]["id"]},
        ]
        bench = [items[7]["id"]]
        r = user_session.post(f"{API}/lineups", json={
            "title": "TEST_Lineup",
            "scoring": "half_ppr",
            "starters": starters,
            "bench": bench,
        })
        assert r.status_code in (200, 201), r.text
        d = r.json()
        assert d["title"] == "TEST_Lineup"
        assert len(d["starters"]) == 7
        assert d["bench"] == bench
        TestLineups.created_id = d["id"]

    def test_my_lineups_get(self, user_session):
        r = user_session.get(f"{API}/lineups/me")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, list)
        if TestLineups.created_id:
            assert any(x["id"] == TestLineups.created_id for x in d)

    def test_lineups_unauth(self):
        r = requests.get(f"{API}/lineups/me")
        assert r.status_code in (401, 403)
        r2 = requests.post(f"{API}/lineups", json={"title": "x", "starters": [], "bench": []})
        assert r2.status_code in (401, 403)

    def test_delete_lineup(self, user_session):
        if not TestLineups.created_id:
            pytest.skip("nothing to delete")
        r = user_session.delete(f"{API}/lineups/{TestLineups.created_id}")
        assert r.status_code in (200, 204)
        # verify
        listing = user_session.get(f"{API}/lineups/me").json()
        assert not any(x["id"] == TestLineups.created_id for x in listing)


# ============ Predictions / Self-Learning ============
class TestPredictions:
    def test_log_prediction(self, user_session):
        items = _items(requests.get(f"{API}/players").json())
        pid = items[0]["id"]
        r = user_session.post(f"{API}/predictions", json={
            "player_id": pid,
            "predicted_fpts": 18.5,
            "scoring": "half_ppr",
            "source": "test",
        })
        assert r.status_code in (200, 201), r.text
        d = r.json()
        assert d["player_id"] == pid
        assert d["predicted_fpts"] == 18.5
        assert d["actual_fpts"] is None

    def test_predictions_stats_shape(self):
        r = requests.get(f"{API}/predictions/stats")
        assert r.status_code == 200, r.text
        d = r.json()
        for f in ("total", "settled", "pending", "by_position"):
            assert f in d, f"Missing {f}"
        assert isinstance(d["by_position"], dict)
        assert d["total"] >= 0

    def test_lineup_suggest_grows_predictions(self):
        before = requests.get(f"{API}/predictions/stats").json()["total"]
        # Trigger lineup suggest, which logs predictions in background
        r = requests.get(f"{API}/lineup/suggest")
        assert r.status_code == 200
        # background task — give it time
        time.sleep(2.5)
        after = requests.get(f"{API}/predictions/stats").json()["total"]
        assert after > before, f"Expected predictions to grow ({before} -> {after})"

    def test_settle_requires_admin(self, user_session):
        r = user_session.post(f"{API}/predictions/settle")
        assert r.status_code == 403

    def test_settle_admin(self, admin_session):
        r = admin_session.post(f"{API}/predictions/settle")
        assert r.status_code == 200, r.text
        d = r.json()
        assert "settled" in d
        assert isinstance(d["settled"], int)


# ============ News URL ============
class TestNewsUrl:
    def test_news_url_endpoint(self):
        items = _items(requests.get(f"{API}/players").json())
        pid = items[0]["id"]
        r = requests.get(f"{API}/players/{pid}/news-url")
        assert r.status_code == 200
        d = r.json()
        assert "url" in d
        assert "google.com" in d["url"] or "news.google" in d["url"]

    def test_player_detail_has_news_url(self):
        items = _items(requests.get(f"{API}/players").json())
        pid = items[0]["id"]
        r = requests.get(f"{API}/players/{pid}")
        d = r.json()
        assert "news_search_url" in d


# ============ Schedule Integration (real) ============
class TestSchedule:
    def test_player_has_next_opponent_from_schedule(self):
        # find a player on a popular team
        items = _items(requests.get(f"{API}/players").json())
        # pick highest-fpts player with a team
        target = next((p for p in items if p.get("team")), None)
        assert target
        d = requests.get(f"{API}/players/{target['id']}").json()
        # next_opponent may be None at end-of-season — accept that, but if present must be 2-3 letter code
        if d.get("next_opponent"):
            assert isinstance(d["next_opponent"], str) and 2 <= len(d["next_opponent"]) <= 4
            assert "next_opponent_week" in d


# ============ Admin refresh ============
class TestAdminRefresh:
    @pytest.mark.slow
    def test_refresh_unauthorized(self, user_session):
        r = user_session.post(f"{API}/admin/refresh-data", params={"force": "false"})
        assert r.status_code == 403
