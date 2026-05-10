# FantasyLab — Product Requirements Document

## Original Problem Statement
> Build a Pro Football Reference-like site, fantasy football focused. Filterable previous-season data, player profiles with team news/insights, AI outlooks, sleeper/bust identifier, lineup tools, rookie analysis, save lineups, self-learning predictions, ad-compatible.

## Architecture
- **Backend**: FastAPI · MongoDB · Motor · JWT cookie auth · Claude Sonnet 4.5 (Emergent LLM key) · nfl-data-py / nflverse (real seasonal stats + rosters + schedules) · async background data refresh
- **Frontend**: React 19 · React Router 7 · Tailwind · Shadcn/UI · Cabinet Grotesk + IBM Plex Sans + JetBrains Mono · DARK theme (#0a0e16 + emerald accents) · ad-slot-ready
- **Routes**: `/`, `/stats`, `/lineup`, `/start-sit`, `/this-week`, `/rookies`, `/sleepers-busts`, `/login`, `/register`, `/my-rankings`

## User Personas
- Casual league commissioner wanting a clean half-PPR reference + start/sit help.
- Draft prep nerd who wants filterable historical stats + rookie/sleeper/bust tags.
- Weekly lineup decider who needs matchup-aware start/sit recommendations.
- Power user saving rankings + lineups + tracking the Lab's prediction accuracy over time.

## What's Implemented (as of 2026-02)
- ✅ JWT email/password auth (httpOnly cookies + bcrypt)
- ✅ Real nflverse data — 277 players (217 stat-rich + 53 2025 rookies). 3 seasons (2022-2024) of stats. Auto-refresh on startup.
- ✅ Real 2025 NFL schedule wired — `next_opponent` driven by `nfl_data_py.import_schedules()`.
- ✅ Rookie class auto-detection from rosters where `years_exp == 0`. 2025 rookies (Cam Ward, Travis Hunter, Ashton Jeanty, Tetairoa McMillan, Tyler Warren, etc.) surface even though 2025 seasonal stats not yet published.
- ✅ AI player outlook (Claude Sonnet 4.5) — separate prompts for veterans vs. rookies. Cached + regenerate.
- ✅ AI rookie outlook prompt covers landing spot, scheme fit, projected target/touch share.
- ✅ Filterable/sortable stats with inline-expanding rows showing career stats + AI outlook + team news.
- ✅ Lineup AI: composite Lab Score = FPts/G + matchup adj + availability + tag boost + learned correction. Save Lineup feature for authed users.
- ✅ Start/Sit tool: ranked recommendation with reasoning per player.
- ✅ Sleepers/Busts dashboard (4 buckets), Rookie sleepers/busts page (3 outlook tiers), This Week's Edge (top 10 plays + 5 fades).
- ✅ Self-learning predictions — every Lineup AI suggestion auto-logged, settle endpoint scores them when new seasonal data arrives, learned bias feeds back as `_lab_correction` per position.
- ✅ Custom rankings + saved lineups (auth required) — surfaced in "My Lab" tabs along with self-learning accuracy panel.
- ✅ Real news search links (Google News) on every player listing — opens credible NFL source headlines.
- ✅ CSV upload for custom data import (`POST /api/upload/csv`) — accepts any season, useful when you want to upload partial 2025 stats early.
- ✅ Ad-slot containers (`<AdSlot slot="..." />`) on Home / Lineup / This Week / My Lab, ready for AdSense or Carbon ad activation.
- ✅ DARK theme, FantasyLab branding, FL logo.
- ✅ ESPN real-time injuries — refreshed via `POST /api/admin/refresh-injuries`, badges on Stats table + factored into Lab Score.
- ✅ **Defense vs Position (DvP) overlay (2026-02)** — live computed from `nfl-data-py` weekly data (latest season w/ ≥4 weeks). Each defense ranked 1–32 per position with FPts allowed/G. Color-coded matchup badges (🟢 EASY/GOOD, 🟦 NEUTRAL, 🔴 HARD/TOUGH) on Lineup slot cards, bench, and StatsTable expanded profile. Reasoning includes "X.X allowed/G". Persisted in `db.meta`, hydrated on startup, falls back to static 2024 baseline if not yet computed.

## Test Credentials
- Admin: `admin@ffref.com` / `admin123`
- User: `user@ffref.com` / `user123`

## Data Source Notes
- `nfl-data-py` 0.3.3 — pulls from nflverse (free, no API key)
- 2025 SEASONAL stats: not yet published by nflverse (404). Will auto-include when uploaded — no code changes needed.
- 2025 ROSTERS + SCHEDULES: available now, used to detect rookies + compute next-opponent.
- Refresh runs daily on backend startup; admins can force-refresh anytime via `POST /api/admin/refresh-data?force=true`.
- Users can also upload custom 2025 CSV stats via `POST /api/upload/csv` (auth required).

## Prioritized Backlog
- **P1**: When admin runs `POST /api/predictions/settle` after 2025 stats land, the Lab will correct its own bias automatically. Document this admin flow.
- **P1**: Sleeper league import (one-click roster sync into Lineup tool via Sleeper username).
- **P2**: AdSense / Carbon ad integration (slot containers ready in code).
- **P2**: Yahoo / ESPN league import (OAuth — more complex than Sleeper).
- **P2**: Refactor `server.py` (~1000+ lines) into modular FastAPI routers (`/routes/players.py`, `/routes/lineups.py`, `/routes/admin.py`).
- **P3**: Mock-draft simulator using sleeper/bust tags.
- **P3**: Trade analyzer.

## API Quick Reference
- `GET /api/players` `?position&team&season&scoring&search&sort&limit`
- `GET /api/players/{id}` — full profile + news_search_url + matchup
- `GET /api/players/{id}/outlook` — Claude AI outlook (cached) + regenerate variant
- `GET /api/rookies` — latest rookie class
- `GET /api/this-week` — top plays + fades
- `GET /api/lineup/suggest` — auto-built lineup (auto-logs predictions)
- `POST /api/start-sit` — rank user's roster
- `POST /api/lineups` — save lineup (auth)
- `GET /api/lineups/me` / `DELETE /api/lineups/{id}` (auth)
- `POST /api/predictions` / `GET /api/predictions/stats` / `POST /api/predictions/settle` (admin)
- `POST /api/upload/csv` — custom data import (auth)
- `POST /api/admin/refresh-data?force=true` — refresh from nflverse (admin)
