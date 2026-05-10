# FantasyLab — Product Requirements Document

## Original Problem Statement
> Build a Pro Football Reference-like site, fantasy football focused. Filterable previous-season data, player profiles with team news/insights, and an outlook section. Iteration 2 added: inline expand on stats, Lineup AI tool, Start/Sit decision tool, Dark theme, Fantasy Lab rebrand with FL logo, real auto-updating data.

## Architecture
- **Backend**: FastAPI · MongoDB · Motor · JWT cookie auth · Claude Sonnet 4.5 (Emergent LLM key) · nfl-data-py (real nflverse data)
- **Frontend**: React 19 · React Router 7 · Tailwind · Shadcn/UI · Cabinet Grotesk + IBM Plex Sans + JetBrains Mono · DARK theme (#0a0e16 + emerald accents)
- **Routes**: `/`, `/stats`, `/lineup`, `/start-sit`, `/sleepers-busts`, `/login`, `/register`, `/my-rankings`

## User Personas
- **Casual league commissioner** wanting a clean half-PPR reference + start/sit help.
- **Draft prep nerd** who wants filterable historical stats + sleeper/bust tags.
- **Weekly lineup decider** who needs matchup-aware start/sit recommendations.

## Core Requirements
- Filterable + sortable multi-season player stats with half/PPR/standard scoring toggle.
- Player profiles with career stats, AI-generated outlook, team news, matchup info.
- Sleepers/busts identification with auto-tagging from stat trajectories.
- Lineup AI: 1QB / 2RB / 2WR / 1TE / 1FLEX with Lab Score reasoning.
- Start/Sit tool: user picks players, gets ranked recommendation.
- Custom rankings (auth required).
- Real data, auto-refreshes when newer NFL seasons publish to nflverse.

## What's Implemented (as of 2026-02)
- ✅ JWT email/password auth (httpOnly cookies + bcrypt + login_attempts brute force protection)
- ✅ MongoDB models: users, players, rankings, outlooks, meta, login_attempts
- ✅ Real player data via nfl-data-py — currently 2022, 2023, 2024 seasons (217 players: 32 QB / 75 RB / 75 WR / 35 TE)
- ✅ Auto-refresh on backend startup (background task), skip if <24h fresh
- ✅ Admin refresh endpoint `/api/admin/refresh-data` to force-pull when 2025/2026 data publishes
- ✅ AI player outlook via Claude Sonnet 4.5 (Emergent LLM key) — cached + regenerate
- ✅ Filterable/sortable stats API + UI (position, team, season, scoring, search)
- ✅ Inline-expanding stats rows showing career stats + AI outlook + team news
- ✅ Lineup AI: composite Lab Score = FPts/G + matchup adj + availability + tag boost
- ✅ Start/Sit tool: ranked recommendation with reasoning per player
- ✅ Sleepers / Busts dashboard (4 buckets)
- ✅ Custom rankings (build, save, delete) — auth required
- ✅ CSV upload for custom data import — auth required
- ✅ DARK theme + FantasyLab branding with FL logo

## Prioritized Backlog
- **P0**: When nflverse publishes 2025 stats, auto-pickup (already wired — just hits the endpoint)
- **P1**: Real schedule integration via `nfl_data_py.import_schedules()` to replace static NEXT_OPPONENT
- **P1**: Real defense-vs-position rankings computed from actual data (currently synthesized)
- **P1**: Mock-draft simulator using sleeper/bust tags
- **P2**: Trade analyzer (compare two rosters)
- **P2**: Weekly news scraper (currently relies on AI synthesis since no public ESPN API)
- **P2**: Real player headshots (nflverse has IDs we can map to ESPN headshot URLs)
- **P2**: League integration (Sleeper API import to auto-load roster into Start/Sit)

## Test Credentials
- Admin: `admin@ffref.com` / `admin123`
- User: `user@ffref.com` / `user123`

## Data Source Notes
- `nfl-data-py` 0.3.3 — pulls from nflverse (free, no API key)
- 2025 / 2026 data not yet published by nflverse (404). Will auto-include when uploaded.
- Refresh runs daily on backend startup; admins can force-refresh anytime.
