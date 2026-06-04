"""LLM service for player outlook generation using Google Gemini API (free tier)."""
import os
from google import genai

# ── NFL prompts ──────────────────────────────────────────────────────────────

NFL_SYSTEM_MSG = (
    "You are an expert fantasy football analyst. Given a player's recent stats, team context, "
    "depth chart situation, coaching/scheme, and recent news, you produce a concise, actionable "
    "fantasy outlook. Be specific, data-aware, and avoid generic platitudes. Format output as 3 short "
    "sections: Outlook (2-3 sentences), Risk Factors (2-3 bullets), Upside (2-3 bullets). Use plain text "
    "with section headings on their own line. No markdown."
)

NFL_ROOKIE_SYSTEM_MSG = (
    "You are an expert fantasy football analyst specializing in rookie projections. Given a rookie's draft slot, "
    "landing spot, college production, team scheme, depth chart, and projected role, produce a focused player+team "
    "outlook for their NFL career trajectory. Cover: 1) Team fit & how the offense will deploy them, "
    "2) Year-1 fantasy expectation (target/touch share, snap %), 3) Multi-year ceiling. "
    "Format as 3 short sections: Player + Team Fit, Year-1 Expectation, Long-Term Ceiling. Plain text, no markdown."
)

NFL_TRADE_SYSTEM_MSG = (
    "You are an expert fantasy football trade analyst. Given two sides of a proposed trade with each "
    "player's live Lab Score, current team, next opponent + matchup difficulty (DvP rank), live injury "
    "status, and tag (elite/breakout/sleeper/risk), produce a concise, opinionated verdict. Always factor "
    "in injury status — if a player is OUT/IR, they have no near-term value. "
    "Format: VERDICT (one line, who wins and by how much), "
    "WHY (3-5 bullets covering injury, matchup, value tier, age/role), RECOMMENDATION (1-2 sentences). "
    "Plain text. No markdown. Be direct and useful, not generic."
)

# ── NBA prompts ──────────────────────────────────────────────────────────────

NBA_SYSTEM_MSG = (
    "You are an expert fantasy basketball analyst. Given an NBA player's recent per-game stats, "
    "team context, role, and recent news, produce a concise actionable fantasy basketball outlook. "
    "Be specific about usage, minutes, and scoring format (standard points league). "
    "Format as 3 short sections: Outlook (2-3 sentences), Risk Factors (2-3 bullets), Upside (2-3 bullets). "
    "Plain text with section headings on their own line. No markdown."
)

NBA_TRADE_SYSTEM_MSG = (
    "You are an expert fantasy basketball trade analyst. Given two sides of a proposed trade with each "
    "player's Lab Score, position, team, stats, and tag (elite/breakout/sleeper/risk), produce a concise "
    "opinionated verdict for a standard points league. "
    "Format: VERDICT (one line), WHY (3-5 bullets), RECOMMENDATION (1-2 sentences). "
    "Plain text. No markdown. Be direct."
)

# ── MLB prompts ──────────────────────────────────────────────────────────────

MLB_BATTER_SYSTEM_MSG = (
    "You are an expert fantasy baseball analyst. Given a MLB hitter's recent stats (H, HR, RBI, SB, AVG, OPS), "
    "team context, lineup spot, and recent news, produce a concise actionable fantasy baseball outlook "
    "for a standard points league scoring. "
    "Format as 3 short sections: Outlook (2-3 sentences), Risk Factors (2-3 bullets), Upside (2-3 bullets). "
    "Plain text with section headings on their own line. No markdown."
)

MLB_PITCHER_SYSTEM_MSG = (
    "You are an expert fantasy baseball analyst. Given a MLB pitcher's recent stats (ERA, WHIP, K/9, W, IP), "
    "team context, rotation spot, and recent news, produce a concise actionable fantasy baseball outlook "
    "for a standard points league scoring. "
    "Format as 3 short sections: Outlook (2-3 sentences), Risk Factors (2-3 bullets), Upside (2-3 bullets). "
    "Plain text with section headings on their own line. No markdown."
)

MLB_TRADE_SYSTEM_MSG = (
    "You are an expert fantasy baseball trade analyst. Given two sides of a proposed trade with each "
    "player's Lab Score, position, team, stats, and tag (elite/breakout/sleeper/risk), produce a concise "
    "opinionated verdict for a standard points league. "
    "Format: VERDICT (one line), WHY (3-5 bullets covering stats, role, injury, value tier), "
    "RECOMMENDATION (1-2 sentences). Plain text. No markdown. Be direct."
)


def _get_system_msg(sport: str, player_type: str = "skill") -> str:
    if sport == "nba":
        return NBA_SYSTEM_MSG
    if sport == "mlb":
        return MLB_PITCHER_SYSTEM_MSG if player_type == "pitcher" else MLB_BATTER_SYSTEM_MSG
    return NFL_SYSTEM_MSG


def _get_trade_system_msg(sport: str) -> str:
    if sport == "nba":
        return NBA_TRADE_SYSTEM_MSG
    if sport == "mlb":
        return MLB_TRADE_SYSTEM_MSG
    return NFL_TRADE_SYSTEM_MSG


def _get_client(api_key: str):
    return genai.Client(api_key=api_key)


def _build_stat_line(player: dict, sport: str) -> str:
    """Build a sport-specific stat summary line."""
    last = (player.get("seasons") or [{}])[-1]
    sport = sport or "nfl"

    if sport == "nba":
        return (
            f"LAST SEASON ({last.get('season', '')}): "
            f"GP {last.get('games', 0)}, "
            f"PTS {last.get('pts', 0)}, REB {last.get('reb', 0)}, AST {last.get('ast', 0)}, "
            f"STL {last.get('stl', 0)}, BLK {last.get('blk', 0)}, TO {last.get('tov', 0)}, "
            f"3PM {last.get('fg3m', 0)}, "
            f"FPts/G {last.get('fpts_per_game', 0)}"
        )
    if sport == "mlb":
        player_type = player.get("player_type", "batter")
        if player_type == "pitcher":
            return (
                f"LAST SEASON ({last.get('season', '')}): "
                f"G {last.get('G', 0)}, IP {last.get('IP', 0)}, "
                f"W {last.get('W', 0)}, SV {last.get('SV', 0)}, "
                f"K {last.get('SO', 0)}, ERA {last.get('ERA', 0)}, "
                f"WHIP {last.get('WHIP', 0)}, "
                f"FPts/G {last.get('fpts_per_game', 0)}"
            )
        else:
            return (
                f"LAST SEASON ({last.get('season', '')}): "
                f"G {last.get('G', 0)}, H {last.get('H', 0)}, "
                f"HR {last.get('HR', 0)}, RBI {last.get('RBI', 0)}, "
                f"SB {last.get('SB', 0)}, AVG {last.get('AVG', 0):.3f}, "
                f"OPS {last.get('OPS', 0):.3f}, "
                f"FPts/G {last.get('fpts_per_game', 0)}"
            )
    # NFL
    return (
        f"LAST SEASON ({last.get('season', '')}): "
        f"GP {last.get('games', 0)}, "
        f"FPTS/G {last.get('fpts_per_game_half_ppr', 0)}, "
        f"YDs {last.get('total_yards', 0)}, TDs {last.get('total_tds', 0)}"
    )


async def generate_player_outlook(player: dict, news_items: list, scoring: str = "half_ppr") -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "AI outlook unavailable: GEMINI_API_KEY not configured."

    sport = player.get("sport", "nfl") or "nfl"
    player_type = player.get("player_type", "skill")
    is_rookie = (player.get("experience", 99) == 0) or (player.get("rookie_info") is not None)
    rinfo = player.get("rookie_info") or {}

    if is_rookie and sport == "nfl":
        prompt = (
            f"{NFL_ROOKIE_SYSTEM_MSG}\n\n"
            f"ROOKIE: {player.get('name')} | {player.get('position')} | {player.get('team')}\n"
            f"DRAFT: Round {((rinfo.get('draft_number') or 999) - 1) // 32 + 1 if rinfo.get('draft_number') else '?'} "
            f"(Pick #{rinfo.get('draft_number', '?')})\n"
            f"COLLEGE: {rinfo.get('college', '?')}\n"
            f"AGE: {player.get('age', '?')}\n"
            f"SCORING: {scoring.replace('_', ' ').upper()}\n\n"
            "Produce the rookie outlook as instructed."
        )
    else:
        fantasy_keywords = [
            "fantasy", "targets", "touches", "snap", "carries", "role",
            "starter", "backup", "injury", "return", "workload", "usage",
            "batting", "pitching", "rotation", "bullpen", "lineup",
            "points", "rebounds", "assists", "minutes",
        ]

        def _news_score(n):
            text = (n.get("headline", "") + " " + n.get("snippet", "")).lower()
            return sum(1 for kw in fantasy_keywords if kw in text)

        sorted_news = sorted(news_items, key=_news_score, reverse=True)
        news_summary = "\n".join(
            f"- ({n.get('date', '')}) {n.get('headline', '')}: {n.get('snippet', '')}"
            for n in sorted_news[:6]
        ) or "No recent news on record."

        inj_status = player.get("injury_status")
        inj_short = player.get("injury_short")
        inj_line = ""
        if inj_status:
            inj_line = f"INJURY (LIVE): {inj_status}"
            if inj_short:
                inj_line += f" — {inj_short[:200]}"
            inj_line += "\n"

        system_msg = _get_system_msg(sport, player_type)
        sport_label = (
            "NBA PLAYER" if sport == "nba"
            else ("MLB PITCHER" if player_type == "pitcher" else "MLB HITTER") if sport == "mlb"
            else "NFL PLAYER"
        )
        scoring_line = (
            f"SCORING: Standard NBA points league\n" if sport == "nba"
            else f"SCORING: Standard MLB points league\n" if sport == "mlb"
            else f"SCORING: {scoring.replace('_', ' ').upper()}\n"
        )

        prompt = (
            f"{system_msg}\n\n"
            f"{sport_label}: {player.get('name')} | {player.get('position')} | {player.get('team')}\n"
            f"AGE: {player.get('age', 'N/A')} | EXPERIENCE: {player.get('experience', 'N/A')} yrs\n"
            f"{scoring_line}"
            f"{inj_line}"
            f"{_build_stat_line(player, sport)}\n"
            f"NEWS:\n{news_summary}\n\n"
            "Produce the outlook as instructed."
        )

    try:
        client = _get_client(api_key)
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"AI outlook unavailable: {e}"


def _format_trade_side(label: str, side: dict) -> str:
    lines = [f"{label} (total Lab Score: {side['total_lab_score']}):"]
    for p in side["players"]:
        f = p.get("factors") or {}
        opp = f.get("opponent") or "—"
        rank = f.get("def_rank") or "—"
        fpa = f.get("def_fpts_allowed")
        inj = p.get("injury_status") or "healthy"
        tag = p.get("tag") or "—"
        fppg = p.get("current_fpts_per_game") or 0
        fpa_str = f", {fpa:.1f} allowed/G" if fpa else ""
        lines.append(
            f"  - {p['name']} ({p['position']}, {p['team']}) | LabScore {p['lineup_score']:.1f} | "
            f"{fppg:.1f} FPts/G | next: vs {opp} (D rank #{rank}{fpa_str}) | "
            f"injury: {inj} | tag: {tag}"
        )
    return "\n".join(lines)


async def generate_trade_verdict(*, side_a_label: str, side_b_label: str, side_a: dict, side_b: dict,
                                  diff: float, verdict: str, scoring: str, sport: str = "nfl") -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "AI verdict unavailable: GEMINI_API_KEY not configured."

    trade_system = _get_trade_system_msg(sport)

    prompt = (
        f"{trade_system}\n\n"
        f"SPORT: {sport.upper()}\n"
        f"SCORING: {scoring.replace('_', ' ').upper()}\n"
        f"LAB-SCORE DIFF: {diff:+.1f} ({verdict.replace('_', ' ')})\n\n"
        f"{_format_trade_side(side_a_label, side_a)}\n\n"
        f"{_format_trade_side(side_b_label, side_b)}\n\n"
        "Produce the trade verdict as instructed."
    )

    try:
        client = _get_client(api_key)
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"AI verdict unavailable: {e}"
