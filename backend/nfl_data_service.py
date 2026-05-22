"""Pull real NFL seasonal data via nflreadpy (nflverse).
Replaces nfl-data-py which was archived Sept 2025.
"""
from __future__ import annotations
import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Iterable

logger = logging.getLogger("ffref.data")

FANTASY_POSITIONS = {"QB", "RB", "WR", "TE", "K"}
TOP_N = {"QB": 64, "RB": 140, "WR": 140, "TE": 64, "K": 32}

TEAM_CODE_ALIASES = {
    "LA": "LAR", "JAC": "JAX", "STL": "LAR", "SD": "LAC",
    "OAK": "LV", "WSH": "WAS", "ARZ": "ARI",
}

def normalize_team(code) -> str:
    if not code:
        return ""
    c = str(code).strip().upper()
    return TEAM_CODE_ALIASES.get(c, c)

NFL_TEAMS = [
    ("ARI", "Arizona Cardinals"), ("ATL", "Atlanta Falcons"), ("BAL", "Baltimore Ravens"),
    ("BUF", "Buffalo Bills"), ("CAR", "Carolina Panthers"), ("CHI", "Chicago Bears"),
    ("CIN", "Cincinnati Bengals"), ("CLE", "Cleveland Browns"), ("DAL", "Dallas Cowboys"),
    ("DEN", "Denver Broncos"), ("DET", "Detroit Lions"), ("GB", "Green Bay Packers"),
    ("HOU", "Houston Texans"), ("IND", "Indianapolis Colts"), ("JAX", "Jacksonville Jaguars"),
    ("KC", "Kansas City Chiefs"), ("LAC", "Los Angeles Chargers"), ("LAR", "Los Angeles Rams"),
    ("LV", "Las Vegas Raiders"), ("MIA", "Miami Dolphins"), ("MIN", "Minnesota Vikings"),
    ("NE", "New England Patriots"), ("NO", "New Orleans Saints"), ("NYG", "New York Giants"),
    ("NYJ", "New York Jets"), ("PHI", "Philadelphia Eagles"), ("PIT", "Pittsburgh Steelers"),
    ("SEA", "Seattle Seahawks"), ("SF", "San Francisco 49ers"), ("TB", "Tampa Bay Buccaneers"),
    ("TEN", "Tennessee Titans"), ("WAS", "Washington Commanders"),
]

def _compute_fp(row, scoring: str) -> float:
    pts = 0.0
    pts += (row.get("passing_yards", 0) or 0) / 25.0
    pts += (row.get("passing_tds", 0) or 0) * 4
    pts -= (row.get("interceptions", 0) or 0) * 2
    pts += (row.get("rushing_yards", 0) or 0) / 10.0
    pts += (row.get("rushing_tds", 0) or 0) * 6
    pts += (row.get("receiving_yards", 0) or 0) / 10.0
    pts += (row.get("receiving_tds", 0) or 0) * 6
    rec = row.get("receptions", 0) or 0
    if scoring == "ppr":
        pts += rec * 1.0
    elif scoring == "half_ppr":
        pts += rec * 0.5
    fumbles_lost = (
        (row.get("rushing_fumbles_lost", 0) or 0) +
        (row.get("receiving_fumbles_lost", 0) or 0) +
        (row.get("sack_fumbles_lost", 0) or 0)
    )
    pts -= fumbles_lost * 2
    return round(pts, 2)

def _season_record(row, season: int) -> dict:
    games = int(row.get("games", 0) or 0)
    rec = {
        "season": season,
        "games": games,
        "pass_yds": int(row.get("passing_yards", 0) or 0),
        "pass_td": int(row.get("passing_tds", 0) or 0),
        "pass_int": int(row.get("interceptions", 0) or 0),
        "rush_yds": int(row.get("rushing_yards", 0) or 0),
        "rush_td": int(row.get("rushing_tds", 0) or 0),
        "rush_att": int(row.get("carries", 0) or 0),
        "receptions": int(row.get("receptions", 0) or 0),
        "targets": int(row.get("targets", 0) or 0),
        "rec_yds": int(row.get("receiving_yards", 0) or 0),
        "rec_td": int(row.get("receiving_tds", 0) or 0),
        "fumbles_lost": int(
            (row.get("rushing_fumbles_lost", 0) or 0) +
            (row.get("receiving_fumbles_lost", 0) or 0) +
            (row.get("sack_fumbles_lost", 0) or 0)
        ),
        "fg_made": 0,
        "fg_att": 0,
        "fg_pct": 0.0,
        "fg_long": 0,
        "fg_made_0_19": 0,
        "fg_made_20_29": 0,
        "fg_made_30_39": 0,
        "fg_made_40_49": 0,
        "fg_made_50_59": 0,
        "fg_made_60_": 0,
        "pat_made": 0,
        "pat_att": 0,
    }
    rec["total_yards"] = rec["pass_yds"] + rec["rush_yds"] + rec["rec_yds"]
    rec["total_tds"] = rec["pass_td"] + rec["rush_td"] + rec["rec_td"]
    rec["fpts_standard"] = _compute_fp(row, "standard")
    rec["fpts_half_ppr"] = _compute_fp(row, "half_ppr")
    rec["fpts_ppr"] = _compute_fp(row, "ppr")
    rec["fpts_per_game_standard"] = round(rec["fpts_standard"] / max(games, 1), 2)
    rec["fpts_per_game_half_ppr"] = round(rec["fpts_half_ppr"] / max(games, 1), 2)
    rec["fpts_per_game_ppr"] = round(rec["fpts_ppr"] / max(games, 1), 2)
    return rec
    
def _detect_tag(seasons: list[dict], position: str) -> str | None:
    if not seasons:
        return None
    seasons_sorted = sorted(seasons, key=lambda s: s["season"])
    latest = seasons_sorted[-1]
    fppg = latest.get("fpts_per_game_half_ppr", 0)
    games = latest.get("games", 0)
    elite_threshold = {"QB": 22, "RB": 17, "WR": 16, "TE": 13}.get(position, 99)
    breakout_threshold = {"QB": 19, "RB": 14, "WR": 13, "TE": 10}.get(position, 99)
    risk_games = 11
    if fppg >= elite_threshold and games >= 12:
        return "elite"
    if len(seasons_sorted) >= 2:
        prev = seasons_sorted[-2]
        if (
            fppg >= breakout_threshold
            and prev.get("fpts_per_game_half_ppr", 0) < breakout_threshold - 2
            and games >= 12
        ):
            return "breakout"
    if games > 0 and games < risk_games:
        return "risk"
    if fppg >= breakout_threshold - 3 and games <= 14 and len(seasons_sorted) <= 2:
        return "sleeper"
    return None

def _fetch_seasons_sync(seasons: Iterable[int]):
    try:
        import nflreadpy as nfl
        import pandas as pd
    except ImportError:
        logger.error("nflreadpy not installed")
        return {}, {}

    seasonal_dfs = {}
    roster_dfs = {}
    kicking_dfs = {}
    team_def_dfs = {}

    for s in seasons:
        # ── Offensive stats ──
        try:
            df = nfl.load_player_stats([s])
            if hasattr(df, 'to_pandas'):
                df = df.to_pandas()
            if df is not None and not df.empty:
                agg_cols = {
                    'passing_yards': 'sum', 'passing_tds': 'sum', 'interceptions': 'sum',
                    'rushing_yards': 'sum', 'rushing_tds': 'sum', 'carries': 'sum',
                    'receptions': 'sum', 'targets': 'sum', 'receiving_yards': 'sum',
                    'receiving_tds': 'sum', 'rushing_fumbles_lost': 'sum',
                    'receiving_fumbles_lost': 'sum', 'sack_fumbles_lost': 'sum',
                }
                existing_cols = {k: v for k, v in agg_cols.items() if k in df.columns}
                if 'player_id' in df.columns:
                    games_count = df.groupby('player_id').size().reset_index(name='games')
                    if existing_cols:
                        seasonal = df.groupby('player_id').agg(existing_cols).reset_index()
                        seasonal = seasonal.merge(games_count, on='player_id', how='left')
                    else:
                        seasonal = games_count
                    meta_cols = ['player_id']
                    for col in ['player_display_name', 'player_name', 'position', 'recent_team']:
                        if col in df.columns:
                            meta_cols.append(col)
                    if len(meta_cols) > 1:
                        meta = df.groupby('player_id')[meta_cols[1:]].first().reset_index()
                        seasonal = seasonal.merge(meta, on='player_id', how='left')
                    seasonal = seasonal.rename(columns={'player_display_name': 'player_name', 'recent_team': 'team'})
                    seasonal_dfs[s] = seasonal
                    logger.info(f"Fetched {s} seasonal stats: {len(seasonal)} players")
                    if s == 2025 and 'position' in seasonal.columns:
                        positions = seasonal['position'].value_counts().to_dict()
                        logger.info(f"2025 positions in seasonal stats: {positions}")
                else:
                    seasonal_dfs[s] = None
            else:
                seasonal_dfs[s] = None
        except Exception as e:
            logger.warning(f"Season {s} stats not available via nflreadpy: {e}")
            seasonal_dfs[s] = None

        # ── Kicking stats ──
        try:
            # Try different methods nflreadpy might support
            kdf = None
            for method_name in ['load_kicking_stats', 'load_player_kicking_stats']:
                if hasattr(nfl, method_name):
                    kdf = getattr(nfl, method_name)([s])
                    break
            if kdf is None:
                kicking_dfs[s] = None
                logger.info(f"Season {s}: no kicking stats method available in nflreadpy")
            else:
                if hasattr(kdf, 'to_pandas'):
                    kdf = kdf.to_pandas()
                if kdf is not None and not kdf.empty:
                    k_agg_cols = {
                        'fg_made': 'sum', 'fg_att': 'sum', 'fg_missed': 'sum',
                        'fg_blocked': 'sum', 'fg_long': 'max',
                        'fg_made_0_19': 'sum', 'fg_made_20_29': 'sum',
                        'fg_made_30_39': 'sum', 'fg_made_40_49': 'sum',
                        'fg_made_50_59': 'sum', 'fg_made_60_': 'sum',
                        'pat_made': 'sum', 'pat_att': 'sum', 'pat_missed': 'sum',
                    }
                    k_existing = {k: v for k, v in k_agg_cols.items() if k in kdf.columns}
                    if 'player_id' in kdf.columns and k_existing:
                        k_games = kdf.groupby('player_id').size().reset_index(name='games')
                        k_seasonal = kdf.groupby('player_id').agg(k_existing).reset_index()
                        k_seasonal = k_seasonal.merge(k_games, on='player_id', how='left')
                        k_meta_cols = ['player_id']
                        for col in ['player_display_name', 'player_name', 'team']:
                            if col in kdf.columns:
                                k_meta_cols.append(col)
                        if len(k_meta_cols) > 1:
                            k_meta = kdf.groupby('player_id')[k_meta_cols[1:]].first().reset_index()
                            k_seasonal = k_seasonal.merge(k_meta, on='player_id', how='left')
                        k_seasonal = k_seasonal.rename(columns={'player_display_name': 'player_name'})
                        if 'fg_made' in k_seasonal.columns and 'fg_att' in k_seasonal.columns:
                            k_seasonal['fg_pct'] = (
                                k_seasonal['fg_made'] / k_seasonal['fg_att'].replace(0, 1) * 100
                            ).round(1)
                        kicking_dfs[s] = k_seasonal
                        logger.info(f"Fetched {s} kicking stats: {len(k_seasonal)} kickers")
                    else:
                        kicking_dfs[s] = None
                else:
                    kicking_dfs[s] = None
        except Exception as e:
            logger.warning(f"Season {s} kicking stats not available: {e}")
            kicking_dfs[s] = None

        # ── Team defensive stats ──
        try:
            tdf = nfl.load_team_stats([s])
            if hasattr(tdf, 'to_pandas'):
                tdf = tdf.to_pandas()
            if tdf is not None and not tdf.empty:
                def_cols = {
                    'def_sacks': 'sum', 'def_interceptions': 'sum',
                    'def_fumbles_forced': 'sum', 'def_fumbles_recovered': 'sum',
                    'def_tds': 'sum', 'def_safety': 'sum',
                    'points_allowed': 'sum', 'yards_allowed': 'sum',
                    'pass_yards_allowed': 'sum', 'rush_yards_allowed': 'sum',
                }
                d_existing = {k: v for k, v in def_cols.items() if k in tdf.columns}
                team_col = next((c for c in ['team', 'team_abbr', 'posteam', 'defteam'] if c in tdf.columns), None)
                if team_col and d_existing:
                    team_def = tdf.groupby(team_col).agg(d_existing).reset_index()
                    team_def = team_def.rename(columns={team_col: 'team'})
                    team_def_dfs[s] = team_def
                    logger.info(f"Fetched {s} team defense stats: {len(team_def)} teams")
                else:
                    logger.warning(f"Season {s} team stats missing expected columns. Have: {list(tdf.columns)[:20]}")
                    team_def_dfs[s] = None
            else:
                team_def_dfs[s] = None
        except Exception as e:
            logger.warning(f"Season {s} team defense stats not available: {e}")
            team_def_dfs[s] = None

        # ── Rosters ──
        try:
            roster = nfl.load_rosters([s])
            if hasattr(roster, 'to_pandas'):
                roster = roster.to_pandas()
            if roster is not None and not roster.empty:
                rename_map = {}
                if 'gsis_id' in roster.columns and 'player_id' not in roster.columns:
                    rename_map['gsis_id'] = 'player_id'
                if 'full_name' in roster.columns and 'player_name' not in roster.columns:
                    rename_map['full_name'] = 'player_name'
                if rename_map:
                    roster = roster.rename(columns=rename_map)
                roster_dfs[s] = roster
                logger.info(f"Fetched {s} rosters: {len(roster)} players")
                if s == 2026:
                    logger.info(f"2026 roster columns: {list(roster.columns)}")
                    if "entry_year" in roster.columns:
                        ey = roster["entry_year"].value_counts().head(5).to_dict()
                        logger.info(f"2026 entry_year distribution: {ey}")
                    if "years_exp" in roster.columns:
                        exp = roster["years_exp"].value_counts().head(5).to_dict()
                        logger.info(f"2026 years_exp distribution: {exp}")
            else:
                roster_dfs[s] = None
        except Exception as e:
            logger.warning(f"Season {s} roster not available via nflreadpy: {e}")
            roster_dfs[s] = None

    return seasonal_dfs, roster_dfs, kicking_dfs, team_def_dfs

def _fetch_weekly_sync(seasons: Iterable[int]):
    try:
        import nflreadpy as nfl
        import pandas as pd
    except ImportError:
        return None

    frames = []
    for s in seasons:
        try:
            df = nfl.load_player_stats([s])
            if hasattr(df, 'to_pandas'):
                df = df.to_pandas()
            if df is not None and not df.empty:
                df["_season"] = s
                frames.append(df)
                logger.info(f"Fetched {s} weekly data: {len(df)} rows")
        except Exception as e:
            logger.warning(f"Season {s} weekly data not available: {e}")

    if not frames:
        return None
    import pandas as pd
    return pd.concat(frames, ignore_index=True)

def _compute_dvp_from_weekly(weekly_df) -> dict:
    import pandas as pd
    if weekly_df is None or weekly_df.empty:
        return {}

    seasons_avail = sorted(weekly_df["_season"].dropna().unique().tolist())
    if not seasons_avail:
        return {}

    target_season = None
    for s in reversed(seasons_avail):
        wk_count = weekly_df[weekly_df["_season"] == s]["week"].nunique() if "week" in weekly_df.columns else 0
        if wk_count >= 4:
            target_season = int(s)
            break
    if target_season is None:
        target_season = int(seasons_avail[-1])

    df = weekly_df[weekly_df["_season"] == target_season].copy()

    opp_col = None
    for candidate in ["opponent_team", "opponent", "defteam"]:
        if candidate in df.columns:
            opp_col = candidate
            break

    if opp_col is None:
        logger.warning("No opponent column found in weekly data")
        return {}

    needed = {"position", opp_col, "week"}
    if not needed.issubset(set(df.columns)):
        logger.warning(f"Weekly data missing columns. Have: {list(df.columns)[:20]}")
        return {}

    df = df[df["position"].isin(["QB", "RB", "WR", "TE"])]
    df = df[df[opp_col].notna()]

    fp_col = None
    for candidate in ["fantasy_points_ppr", "fantasy_points", "ppr_points"]:
        if candidate in df.columns:
            fp_col = candidate
            break

    if fp_col is None:
        logger.warning("No fantasy points column found")
        return {}

    if "fantasy_points_ppr" in df.columns and "fantasy_points" in df.columns:
        df["_fp_half"] = (df["fantasy_points"].fillna(0) + df["fantasy_points_ppr"].fillna(0)) / 2.0
    else:
        df["_fp_half"] = df[fp_col].fillna(0)

    game_level = df.groupby([opp_col, "position", "week"], as_index=False)["_fp_half"].sum()
    per_def = (
        game_level.groupby([opp_col, "position"], as_index=False)
                  .agg(fpts_allowed_per_game=("_fp_half", "mean"), games=("_fp_half", "count"))
    )

    out: dict[str, dict] = {}
    for pos in ["QB", "RB", "WR", "TE"]:
        sub = per_def[per_def["position"] == pos].copy()
        if sub.empty:
            continue
        sub = sub.sort_values("fpts_allowed_per_game", ascending=True).reset_index(drop=True)
        out[pos] = {}
        for i, row in sub.iterrows():
            out[pos][str(row[opp_col])] = {
                "rank": int(i + 1),
                "fpts_allowed_per_game": round(float(row["fpts_allowed_per_game"]), 2),
                "games": int(row["games"]),
                "season": target_season,
            }
    logger.info(f"DvP computed from {target_season} weekly data: {sum(len(v) for v in out.values())} cells")
    return out

def _compute_kicker_stats_from_weekly(weekly_df) -> dict:
    """Extract kicker fantasy points from weekly play-by-play style stats."""
    import pandas as pd
    if weekly_df is None or weekly_df.empty:
        return {}

    # Filter to kickers
    if 'position' not in weekly_df.columns:
        return {}

    k_df = weekly_df[weekly_df['position'] == 'K'].copy()
    if k_df.empty:
        return {}

    # Find fantasy points column
    fp_col = None
    for candidate in ['fantasy_points', 'fantasy_points_ppr']:
        if candidate in k_df.columns:
            fp_col = candidate
            break
    if not fp_col:
        return {}

    # Also look for FG columns in weekly data
    fg_cols = {}
    for col in ['fg_made', 'fg_att', 'fg_made_40_49', 'fg_made_50_59', 'fg_made_60_',
                'pat_made', 'pat_att']:
        if col in k_df.columns:
            fg_cols[col] = 'sum'

    agg = {fp_col: 'sum'}
    agg.update(fg_cols)
    agg['_season'] = 'first'

    if 'player_id' not in k_df.columns:
        return {}

    # Group by player_id and season
    result = {}
    for season in k_df['_season'].unique():
        season_df = k_df[k_df['_season'] == season]
        games = season_df.groupby('player_id').size().reset_index(name='games')
        stats = season_df.groupby('player_id').agg(agg).reset_index()
        stats = stats.merge(games, on='player_id', how='left')

        for _, row in stats.iterrows():
            pid = row['player_id']
            if pd.isna(pid):
                continue
            fpts = float(row.get(fp_col, 0) or 0)
            games_played = int(row.get('games', 1) or 1)
            result.setdefault(pid, {})[int(season)] = {
                'fpts': round(fpts, 2),
                'fpts_per_game': round(fpts / max(games_played, 1), 2),
                'games': games_played,
                **{c: int(row.get(c, 0) or 0) for c in fg_cols if c != '_season'},
            }

    logger.info(f"Kicker stats from weekly: {len(result)} kickers")
    return result

def _fetch_schedule_sync(seasons: Iterable[int]):
    try:
        import nflreadpy as nfl
        import pandas as pd
    except ImportError:
        return {}

    next_opp: dict[str, dict] = {}
    try:
        sched = nfl.load_schedules(list(seasons))
        if hasattr(sched, 'to_pandas'):
            sched = sched.to_pandas()
        if sched is None or sched.empty:
            return next_opp

        today = pd.Timestamp(datetime.now(timezone.utc).date())
        if "gameday" in sched.columns:
            sched["gameday_dt"] = pd.to_datetime(sched["gameday"], errors="coerce")
        elif "game_date" in sched.columns:
            sched["gameday_dt"] = pd.to_datetime(sched["game_date"], errors="coerce")
        else:
            return next_opp

        game_type_col = "game_type" if "game_type" in sched.columns else None
        if game_type_col:
            future = sched[(sched[game_type_col] == "REG") & (sched["gameday_dt"] >= today)]
        else:
            future = sched[sched["gameday_dt"] >= today]

        if future.empty:
            latest_season = int(sched["season"].max()) if "season" in sched.columns else list(seasons)[-1]
            ss = sched[sched["season"] == latest_season] if "season" in sched.columns else sched
            if game_type_col:
                ss = ss[ss[game_type_col] == "REG"]
            if not ss.empty and "week" in ss.columns:
                future = ss[ss["week"] == ss["week"].max()]

        future = future.sort_values("gameday_dt") if not future.empty else future

        home_col = "home_team" if "home_team" in future.columns else None
        away_col = "away_team" if "away_team" in future.columns else None

        if not home_col or not away_col:
            return next_opp

        for _, g in future.iterrows():
            home, away = g.get(home_col), g.get(away_col)
            week = int(g.get("week", 0)) if "week" in g and not pd.isna(g.get("week")) else 0
            gameday = g.get("gameday") or g.get("game_date", "")
            if isinstance(home, str) and home not in next_opp:
                next_opp[home] = {"opponent": away, "home": True, "week": week, "gameday": str(gameday)}
            if isinstance(away, str) and away not in next_opp:
                next_opp[away] = {"opponent": home, "home": False, "week": week, "gameday": str(gameday)}
    except Exception as e:
        logger.warning(f"Schedule fetch failed: {e}")
    return next_opp

def _build_players_from_dataframes(seasonal_dfs: dict, roster_dfs: dict, kicking_dfs: dict | None = None, team_def_dfs: dict | None = None, kicker_stats: dict | None = None) -> list[dict]:
    import pandas as pd

    all_player_seasons: dict[str, dict] = {}
    rookie_meta: dict[str, dict] = {}

    # ── Step 1: Build seasonal stats ──
    for season, df in seasonal_dfs.items():
        if df is None or df.empty:
            continue
        roster = roster_dfs.get(season)
        if roster is None or roster.empty:
            continue

        roster_latest = roster.drop_duplicates(subset=["player_id"], keep="last") if "player_id" in roster.columns else roster

        merge_cols = ["player_id"]
        for col in ["player_name", "position", "team", "birth_date"]:
            if col in roster_latest.columns:
                merge_cols.append(col)

        if "player_id" in df.columns and "player_id" in roster_latest.columns:
            roster_merge = roster_latest[merge_cols].copy()
            merged = df.merge(roster_merge, on="player_id", how="left", suffixes=("", "_roster"))
            if "position" not in df.columns and "position_roster" in merged.columns:
                merged["position"] = merged["position_roster"]
            elif "position_roster" in merged.columns:
                merged["position"] = merged["position"].fillna(merged["position_roster"])
        else:
            merged = df

        if "position" in merged.columns:
            merged = merged[merged["position"].isin(FANTASY_POSITIONS)]
        else:
            continue

        if "games" in merged.columns:
            merged = merged[merged["games"].fillna(0) >= 1]

        for _, row in merged.iterrows():
            pid = row.get("player_id")
            if not pid or (isinstance(pid, float) and pd.isna(pid)):
                continue

            def _scalar(v):
                if v is None:
                    return None
                if hasattr(v, 'iloc'):
                    v = v.iloc[0] if len(v) > 0 else None
                elif hasattr(v, 'item'):
                    try:
                        v = v.item()
                    except Exception:
                        v = None
                return v

            name = _scalar(row.get("player_display_name")) or _scalar(row.get("player_name"))
            pos = _scalar(row.get("position"))
            team = _scalar(row.get("recent_team")) or _scalar(row.get("team"))

            if not name or not pos or (isinstance(name, float) and pd.isna(name)):
                continue

            entry = all_player_seasons.setdefault(pid, {
                "ext_id": pid,
                "name": str(name),
                "position": str(pos),
                "team": normalize_team(team) if team and not (isinstance(team, float) and pd.isna(team)) else "",
                "birth_date": row.get("birth_date"),
                "seasons": [],
            })
            if team and not (isinstance(team, float) and pd.isna(team)):
                entry["team"] = normalize_team(team)
            entry["seasons"].append(_season_record(dict(row), season))
            
    # ── Step 1b: Merge kicking stats into K player seasons ──
    if kicking_dfs:
        for season, kdf in kicking_dfs.items():
            if kdf is None or kdf.empty:
                continue
            for _, row in kdf.iterrows():
                pid = row.get("player_id")
                if not pid or (isinstance(pid, float) and pd.isna(pid)):
                    continue
                if pid not in all_player_seasons:
                    # Add kicker not in offensive stats
                    name = row.get("player_name") or ""
                    team = row.get("team") or ""
                    if not name or (isinstance(name, float) and pd.isna(name)):
                        continue
                    all_player_seasons[pid] = {
                        "ext_id": pid,
                        "name": str(name),
                        "position": "K",
                        "team": normalize_team(team) if team else "",
                        "birth_date": None,
                        "seasons": [],
                    }
                # Find or create season record for this kicker
                entry = all_player_seasons[pid]
                entry["position"] = "K"
                existing_season = next((s for s in entry["seasons"] if s["season"] == season), None)
                if existing_season is None:
                    existing_season = {
                        "season": season, "games": int(row.get("games", 0) or 0),
                        "pass_yds": 0, "pass_td": 0, "pass_int": 0,
                        "rush_yds": 0, "rush_td": 0, "rush_att": 0,
                        "receptions": 0, "targets": 0, "rec_yds": 0, "rec_td": 0,
                        "fumbles_lost": 0, "total_yards": 0, "total_tds": 0,
                        "fpts_standard": 0.0, "fpts_half_ppr": 0.0, "fpts_ppr": 0.0,
                        "fpts_per_game_standard": 0.0, "fpts_per_game_half_ppr": 0.0,
                        "fpts_per_game_ppr": 0.0,
                    }
                    entry["seasons"].append(existing_season)
                # Merge kicking stats
                for k_col in ['fg_made', 'fg_att', 'fg_pct', 'fg_long',
                               'fg_made_0_19', 'fg_made_20_29', 'fg_made_30_39',
                               'fg_made_40_49', 'fg_made_50_59', 'fg_made_60_',
                               'pat_made', 'pat_att']:
                    v = row.get(k_col)
                    if v is not None and not (isinstance(v, float) and pd.isna(v)):
                        existing_season[k_col] = float(v) if k_col in ('fg_pct',) else int(v)
                # Compute fantasy points for kicker
                fg = existing_season.get("fg_made", 0)
                pat = existing_season.get("pat_made", 0)
                fg_50 = existing_season.get("fg_made_50_59", 0) + existing_season.get("fg_made_60_", 0)
                fg_40 = existing_season.get("fg_made_40_49", 0)
                fg_under40 = fg - fg_40 - fg_50
                # Standard kicker scoring: FG < 40 = 3pts, 40-49 = 4pts, 50+ = 5pts, PAT = 1pt
                fpts = (fg_under40 * 3) + (fg_40 * 4) + (fg_50 * 5) + (pat * 1)
                games = max(existing_season.get("games", 1), 1)
                existing_season["fpts_standard"] = round(fpts, 2)
                existing_season["fpts_half_ppr"] = round(fpts, 2)
                existing_season["fpts_ppr"] = round(fpts, 2)
                existing_season["fpts_per_game_standard"] = round(fpts / games, 2)
                existing_season["fpts_per_game_half_ppr"] = round(fpts / games, 2)
                existing_season["fpts_per_game_ppr"] = round(fpts / games, 2)

    # ── Step 1c: Store team defensive stats ──
    team_def_lookup: dict[str, dict] = {}
    if team_def_dfs:
        for season, tdf in team_def_dfs.items():
            if tdf is None or tdf.empty:
                continue
            for _, row in tdf.iterrows():
                team = row.get("team")
                if not team or (isinstance(team, float) and pd.isna(team)):
                    continue
                team = normalize_team(str(team))
                if team not in team_def_lookup:
                    team_def_lookup[team] = {}
                team_def_lookup[team][season] = {
                    "season": season,
                    "sacks": int(row.get("def_sacks", 0) or 0),
                    "interceptions": int(row.get("def_interceptions", 0) or 0),
                    "fumbles_forced": int(row.get("def_fumbles_forced", 0) or 0),
                    "fumbles_recovered": int(row.get("def_fumbles_recovered", 0) or 0),
                    "def_tds": int(row.get("def_tds", 0) or 0),
                    "points_allowed": int(row.get("points_allowed", 0) or 0),
                    "yards_allowed": int(row.get("yards_allowed", 0) or 0),
                }
        logger.info(f"Team defense stats loaded: {len(team_def_lookup)} teams")

    # ── Step 1b: Apply kicker fantasy points from weekly data ──
    if kicker_stats:
        logger.info(f"Applying kicker stats for {len(kicker_stats)} kickers")
        applied = 0
        sample_kicker_pid = next(iter(kicker_stats), None)
        sample_player_pid = next((k for k, v in all_player_seasons.items() if v.get('position') == 'K'), None)
        logger.info(f"Sample kicker_stats pid: {repr(sample_kicker_pid)}, sample all_player_seasons K pid: {repr(sample_player_pid)}")
        for pid, seasons_data in kicker_stats.items():
            if pid not in all_player_seasons:
                continue
            entry = all_player_seasons[pid]
            for season, k_data in seasons_data.items():
                existing_season = next((s for s in entry["seasons"] if s["season"] == season), None)
                if existing_season:
                    fpts = k_data.get('fpts', 0)
                    games = max(k_data.get('games', 1), 1)
                    existing_season['fpts_standard'] = fpts
                    existing_season['fpts_half_ppr'] = fpts
                    existing_season['fpts_ppr'] = fpts
                    existing_season['fpts_per_game_standard'] = round(fpts / games, 2)
                    existing_season['fpts_per_game_half_ppr'] = round(fpts / games, 2)
                    existing_season['fpts_per_game_ppr'] = round(fpts / games, 2)
                    applied += 1
        logger.info(f"Kicker FPts applied to {applied} season records")
    
    # ── Step 2: Build rookie_meta ──
    available_roster_seasons = sorted(s for s, r in roster_dfs.items() if r is not None and not r.empty)
    latest_roster_season = available_roster_seasons[-1] if available_roster_seasons else None
    players_with_stats = set(all_player_seasons.keys())

    for season, roster in roster_dfs.items():
        if roster is None or roster.empty:
            continue

        if "entry_year" in roster.columns:
            rookie_mask = roster["entry_year"] == season
        elif "rookie_year" in roster.columns:
            rookie_mask = roster["rookie_year"] == season
        else:
            years_exp_col = next((c for c in ["years_exp", "years_experience", "experience"] if c in roster.columns), None)
            if not years_exp_col:
                continue
            rookie_mask = roster[years_exp_col] == 0

        if "position" in roster.columns:
            rookie_mask = rookie_mask & roster["position"].isin(FANTASY_POSITIONS)

        rookies = roster[rookie_mask]
        logger.info(f"Season {season}: found {len(rookies)} rookies")

        for _, row in rookies.iterrows():
            pid = row.get("player_id")
            if not pid or (isinstance(pid, float) and pd.isna(pid)):
                continue

            draft_num = row.get("draft_number") or row.get("draft_pick")
            draft_club = row.get("draft_club") or row.get("draft_team")
            college = row.get("college") or row.get("college_name")

            new_draft_num = None if not draft_num or (isinstance(draft_num, float) and pd.isna(draft_num)) else int(draft_num)
            new_draft_club = None if not draft_club or (isinstance(draft_club, float) and pd.isna(draft_club)) else str(draft_club)
            new_college = None if not college or (isinstance(college, float) and pd.isna(college)) else str(college)

            existing_rookie = rookie_meta.get(pid)
            if not existing_rookie or int(season) >= existing_rookie["rookie_year"]:
                rookie_meta[pid] = {
                    "rookie_year": int(season),
                    "draft_number": new_draft_num or (existing_rookie or {}).get("draft_number"),
                    "draft_club": new_draft_club or (existing_rookie or {}).get("draft_club"),
                    "college": new_college or (existing_rookie or {}).get("college"),
                }
            if pid not in all_player_seasons:
                name = row.get("player_name") or row.get("full_name") or ""
                pos = row.get("position", "")
                team = row.get("team") or row.get("current_team", "")
                all_player_seasons[pid] = {
                    "ext_id": pid,
                    "name": str(name),
                    "position": str(pos),
                    "team": normalize_team(team) if team else "",
                    "birth_date": row.get("birth_date"),
                    "seasons": [],
                }

    # ── Step 3: Latest roster overlay ──
    if available_roster_seasons:
        latest_season = available_roster_seasons[-1]
        latest_roster = roster_dfs[latest_season]
        if "player_id" in latest_roster.columns:
            latest_roster = latest_roster.drop_duplicates(subset=["player_id"], keep="last")
            for _, row in latest_roster.iterrows():
                pid = row.get("player_id")
                if not pid or (isinstance(pid, float) and pd.isna(pid)):
                    continue
                if pid not in all_player_seasons:
                    continue
                new_team = row.get("team") or row.get("current_team")
                if new_team and not (isinstance(new_team, float) and pd.isna(new_team)):
                    all_player_seasons[pid]["team"] = normalize_team(new_team)
                new_pos = row.get("position")
                if new_pos and not (isinstance(new_pos, float) and pd.isna(new_pos)):
                    all_player_seasons[pid]["position"] = str(new_pos)
        logger.info(f"Latest-roster overlay applied from {latest_season}")

    # ── Step 4: Filter to top-N per position ──
    per_position: dict[str, list[dict]] = {}
    rookies_with_no_seasons: list[dict] = []

    for entry in all_player_seasons.values():
        pos = entry["position"]
        if not entry["seasons"]:
            if entry["position"] == "K":
                entry["_latest_fpts"] = 0
                per_position.setdefault("K", []).append(entry)
                continue
            r = rookie_meta.get(entry["ext_id"])
            if r:
                entry["_rookie_score"] = -1 * (r.get("draft_number") or 999)
                rookies_with_no_seasons.append(entry)
            continue
        best = max((s.get("fpts_half_ppr", 0) for s in entry["seasons"]), default=0)
        entry["_latest_fpts"] = best
        per_position.setdefault(pos, []).append(entry)

    selected: list[dict] = []
    for pos, lst in per_position.items():
        cap = TOP_N.get(pos, 30)
        lst.sort(key=lambda e: e["_latest_fpts"], reverse=True)
        selected.extend(lst[:cap])

    rookies_with_no_seasons.sort(key=lambda e: e.get("_rookie_score", -999), reverse=True)
    selected.extend(rookies_with_no_seasons[:200])

    # ── Step 5: Build final player docs ──
    today = datetime.now(timezone.utc).date()
    final = []
    for e in selected:
        seasons = sorted(e["seasons"], key=lambda s: s["season"])
        age = None
        bd = e.get("birth_date")
        try:
            if bd is not None:
                bd_dt = pd.to_datetime(bd, errors="coerce")
                if bd_dt is not None and not pd.isna(bd_dt):
                    age = today.year - bd_dt.year - ((today.month, today.day) < (bd_dt.month, bd_dt.day))
        except Exception:
            age = None

        exp = len(seasons)
        tag = _detect_tag(seasons, e["position"])

        final.append({
            "id": str(uuid.uuid4()),
            "ext_id": e["ext_id"],
            "name": e["name"],
            "position": e["position"],
            "team": e["team"],
            "age": age,
            "experience": exp,
            "headshot": "",
            "tag": tag,
            "rookie_info": None,
            "seasons": seasons,
            "news": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    for p in final:
        rm = rookie_meta.get(p["ext_id"])
        if rm:
            p["rookie_info"] = rm
            if not p["seasons"] or all(s.get("season", 0) < rm["rookie_year"] for s in p["seasons"]):
                p["experience"] = 0

    return final


# ── Module-level caches ──
_NEXT_OPP_CACHE: dict[str, dict] = {}
_DVP_LIVE: dict[str, dict] = {}

def hydrate_dvp_cache(dvp: dict) -> None:
    global _DVP_LIVE
    if isinstance(dvp, dict) and dvp:
        _DVP_LIVE = dvp

def hydrate_next_opp_cache(no: dict) -> None:
    global _NEXT_OPP_CACHE
    if isinstance(no, dict) and no:
        _NEXT_OPP_CACHE = no

async def refresh_player_data(db, *, seasons: list[int] | None = None, force: bool = False) -> dict:
    if seasons is None:
        current_year = datetime.now(timezone.utc).year
        seasons = list(range(current_year - 4, current_year + 1))

    if not force:
        meta = await db.meta.find_one({"key": "last_refresh"}, {"_id": 0})
        if meta:
            last = datetime.fromisoformat(meta["value"])
            if datetime.now(timezone.utc) - last < timedelta(hours=24):
                count = await db.players.count_documents({})
                if count > 0:
                    return {"status": "skipped", "reason": "fresh", "players": count}

    loop = asyncio.get_event_loop()
    seasonal_dfs, roster_dfs, kicking_dfs, team_def_dfs = await loop.run_in_executor(None, _fetch_seasons_sync, seasons)

    available = [s for s, df in seasonal_dfs.items() if df is not None and not df.empty]
    available_rosters = [s for s, df in roster_dfs.items() if df is not None and not df.empty]

    sched_seasons = available_rosters or available
    next_opp = await loop.run_in_executor(None, _fetch_schedule_sync, sched_seasons)
    global _NEXT_OPP_CACHE
    if next_opp:
        _NEXT_OPP_CACHE = next_opp
        logger.info(f"Live schedule loaded: {len(next_opp)} teams")

    dvp_seasons = available or available_rosters
    weekly_df = await loop.run_in_executor(None, _fetch_weekly_sync, dvp_seasons)
    dvp_live = await loop.run_in_executor(None, _compute_dvp_from_weekly, weekly_df)
    kicker_stats = await loop.run_in_executor(None, _compute_kicker_stats_from_weekly, weekly_df)
    global _DVP_LIVE
    if dvp_live:
        _DVP_LIVE = dvp_live

    if not available and not available_rosters:
        return {"status": "error", "reason": "no_data"}

    players = await loop.run_in_executor(None, _build_players_from_dataframes, seasonal_dfs, roster_dfs, kicking_dfs, team_def_dfs, kicker_stats)
    if not players:
        return {"status": "error", "reason": "no_players_built"}

    existing = await db.players.find({}, {"_id": 0, "id": 1, "ext_id": 1, "news": 1, "team": 1}).to_list(length=10000)
    ext_to_existing = {e.get("ext_id"): e for e in existing if e.get("ext_id")}
    traded_player_ids: list[str] = []
    merged = []
    for p in players:
        prev = ext_to_existing.get(p["ext_id"])
        if prev:
            p["id"] = prev["id"]
            if prev.get("news"):
                p["news"] = prev["news"]
            if prev.get("team") and p.get("team") and prev["team"] != p["team"]:
                traded_player_ids.append(prev["id"])
        merged.append(p)

    await db.players.delete_many({})
    if merged:
        await db.players.insert_many(merged)

    outlooks_invalidated = 0
    if traded_player_ids:
        res = await db.outlooks.delete_many({"player_id": {"$in": traded_player_ids}})
        outlooks_invalidated = res.deleted_count or 0

    def_docs = []
    for code, full_name in NFL_TEAMS:
        def_docs.append({
            "id": str(uuid.uuid4()),
            "ext_id": f"DEF_{code}",
            "name": f"{full_name} D/ST",
            "position": "DEF",
            "team": code,
            "age": None, "experience": None, "headshot": "",
            "tag": None, "rookie_info": None, "seasons": [], "news": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    await db.players.insert_many(def_docs)

    await db.meta.replace_one(
        {"key": "last_refresh"},
        {"key": "last_refresh", "value": datetime.now(timezone.utc).isoformat(), "seasons": available, "count": len(merged)},
        upsert=True,
    )

    if dvp_live:
        await db.meta.replace_one(
            {"key": "dvp_live"},
            {"key": "dvp_live", "value": dvp_live, "updated_at": datetime.now(timezone.utc).isoformat()},
            upsert=True,
        )
    if next_opp:
        await db.meta.replace_one(
            {"key": "next_opp"},
            {"key": "next_opp", "value": next_opp, "updated_at": datetime.now(timezone.utc).isoformat()},
            upsert=True,
        )
    # Refresh ESPN news
    try:
        from .espn_injuries import refresh_news, _fetch_news_sync
        news_items = await loop.run_in_executor(None, _fetch_news_sync)
        news_updated = await refresh_news(db, news_items)
        logger.info(f"News refresh complete: {news_updated} players updated")
    except Exception as e:
        logger.warning(f"News refresh failed: {e}")
        
    return {
        "status": "ok",
        "players": len(merged),
        "seasons": available,
        "dvp_cells": sum(len(v) for v in (dvp_live or {}).values()),
        "trades_detected": len(traded_player_ids),
        "outlooks_invalidated": outlooks_invalidated,
    }


# ── Static fallback DvP (2024) ──
DEF_VS_POS_2024 = {
    "QB": {"BAL": 1, "PHI": 2, "MIN": 3, "DEN": 4, "PIT": 5, "GB": 6, "BUF": 7, "DET": 8, "NYG": 9, "SF": 10,
           "HOU": 11, "ARI": 12, "SEA": 13, "TB": 14, "LAC": 15, "KC": 16, "WAS": 17, "CHI": 18, "ATL": 19, "NE": 20,
           "JAX": 21, "MIA": 22, "LV": 23, "TEN": 24, "DAL": 25, "CIN": 26, "IND": 27, "NO": 28, "NYJ": 29, "CLE": 30, "LAR": 31, "CAR": 32},
    "RB": {"PHI": 1, "BAL": 2, "DEN": 3, "MIN": 4, "PIT": 5, "BUF": 6, "DET": 7, "GB": 8, "HOU": 9, "TB": 10,
           "WAS": 11, "ATL": 12, "SF": 13, "KC": 14, "NYG": 15, "LAC": 16, "CHI": 17, "ARI": 18, "MIA": 19, "TEN": 20,
           "JAX": 21, "SEA": 22, "NE": 23, "IND": 24, "NO": 25, "CIN": 26, "DAL": 27, "CLE": 28, "NYJ": 29, "LAR": 30, "LV": 31, "CAR": 32},
    "WR": {"DET": 1, "MIN": 2, "BAL": 3, "PHI": 4, "DEN": 5, "GB": 6, "BUF": 7, "PIT": 8, "TB": 9, "HOU": 10,
           "SF": 11, "KC": 12, "LAC": 13, "ARI": 14, "ATL": 15, "WAS": 16, "CHI": 17, "NYG": 18, "SEA": 19, "JAX": 20,
           "NE": 21, "DAL": 22, "MIA": 23, "TEN": 24, "IND": 25, "NO": 26, "CIN": 27, "LV": 28, "NYJ": 29, "CLE": 30, "LAR": 31, "CAR": 32},
    "TE": {"MIN": 1, "BAL": 2, "PHI": 3, "DEN": 4, "BUF": 5, "DET": 6, "PIT": 7, "GB": 8, "TB": 9, "KC": 10,
           "SF": 11, "HOU": 12, "ARI": 13, "WAS": 14, "ATL": 15, "CHI": 16, "LAC": 17, "NYG": 18, "JAX": 19, "SEA": 20,
           "DAL": 21, "MIA": 22, "TEN": 23, "NO": 24, "IND": 25, "NE": 26, "CLE": 27, "CIN": 28, "LV": 29, "NYJ": 30, "LAR": 31, "CAR": 32},
}

NEXT_OPPONENT = {
    "ARI": "SEA", "ATL": "TB", "BAL": "PIT", "BUF": "MIA", "CAR": "NO", "CHI": "GB", "CIN": "CLE", "CLE": "CIN",
    "DAL": "PHI", "DEN": "LV", "DET": "MIN", "GB": "CHI", "HOU": "JAX", "IND": "TEN", "JAX": "HOU", "KC": "LAC",
    "LAC": "KC", "LAR": "SF", "LV": "DEN", "MIA": "BUF", "MIN": "DET", "NE": "NYJ", "NO": "CAR", "NYG": "WAS",
    "NYJ": "NE", "PHI": "DAL", "PIT": "BAL", "SEA": "ARI", "SF": "LAR", "TB": "ATL", "TEN": "IND", "WAS": "NYG",
}

def get_next_opponent(team: str) -> dict | None:
    if team in _NEXT_OPP_CACHE:
        return _NEXT_OPP_CACHE[team]
    opp = NEXT_OPPONENT.get(team)
    if opp:
        return {"opponent": opp, "home": False, "week": 0, "gameday": None}
    return None

def get_next_opponent_team(team: str) -> str | None:
    info = get_next_opponent(team)
    return info["opponent"] if info else None

def player_news_search_url(player_name: str) -> str:
    from urllib.parse import quote_plus
    return f"https://news.google.com/search?q={quote_plus(player_name + ' NFL fantasy')}"

def get_def_rank(opp_team: str, position: str) -> int:
    live = _DVP_LIVE.get(position, {}).get(opp_team)
    if live and "rank" in live:
        return int(live["rank"])
    return DEF_VS_POS_2024.get(position, {}).get(opp_team, 16)

def get_def_dvp(opp_team: str, position: str) -> dict:
    live = _DVP_LIVE.get(position, {}).get(opp_team)
    if live and "rank" in live:
        return {**live, "source": "live"}
    rank = DEF_VS_POS_2024.get(position, {}).get(opp_team, 16)
    return {"rank": rank, "fpts_allowed_per_game": None, "games": None, "season": 2024, "source": "static"}

def get_dvp_table() -> dict:
    if _DVP_LIVE:
        return {"source": "live", "data": _DVP_LIVE}
    static_wrapped = {pos: {team: {"rank": rank, "fpts_allowed_per_game": None, "games": None, "season": 2024}
                            for team, rank in teams.items()}
                      for pos, teams in DEF_VS_POS_2024.items()}
    return {"source": "static", "data": static_wrapped}

def matchup_score(opp_team: str, position: str) -> float:
    rank = get_def_rank(opp_team, position)
    return round((rank - 16.5) / 7.75, 2)
