"""LLM service for player outlook generation using Google Gemini API (free tier)."""
import os
from google import genai

SYSTEM_MSG = (
    "You are an expert fantasy football analyst. Given a player's recent stats, team context, "
    "depth chart situation, coaching/scheme, and recent news, you produce a concise, actionable "
    "fantasy outlook. Be specific, data-aware, and avoid generic platitudes. Format output as 3 short "
    "sections: Outlook (2-3 sentences), Risk Factors (2-3 bullets), Upside (2-3 bullets). Use plain text "
    "with section headings on their own line. No markdown."
)

ROOKIE_SYSTEM_MSG = (
    "You are an expert fantasy football analyst specializing in rookie projections. Given a rookie's draft slot, "
    "landing spot, college production, team scheme, depth chart, and projected role, produce a focused player+team "
    "outlook for their NFL career trajectory. Cover: 1) Team fit & how the offense will deploy them, "
    "2) Year-1 fantasy expectation (target/touch share, snap %), 3) Multi-year ceiling. "
    "Format as 3 short sections: Player + Team Fit, Year-1 Expectation, Long-Term Ceiling. Plain text, no markdown."
)

TRADE_SYSTEM_MSG = (
    "You are an expert fantasy football trade analyst. Given two sides of a proposed trade with each "
    "player's live Lab Score, current team, next opponent + matchup difficulty (DvP rank), live injury "
    "status, and tag (elite/breakout/sleeper/risk), produce a concise, opinionated verdict. Always factor "
    "in injury status — if a player is OUT/IR, they have no near-term value. "
    "Format: VERDICT (one line, who wins and by how much), "
    "WHY (3-5 bullets covering injury, matchup, value tier, age/role), RECOMMENDATION (1-2 sentences). "
    "Plain text. No markdown. Be direct and useful, not generic."
)


def _get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=None,
    )


async def generate_player_outlook(player: dict, news_items: list, scoring: str = "half_ppr") -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "AI outlook unavailable: GEMINI_API_KEY not configured."

    is_rookie = (player.get("experience", 99) == 0) or (player.get("rookie_info") is not None)
    rinfo = player.get("rookie_info") or {}

    if is_rookie:
        prompt = (
            f"{ROOKIE_SYSTEM_MSG}\n\n"
            f"ROOKIE: {player.get('name')} | {player.get('position')} | {player.get('team')}\n"
            f"DRAFT: Round {((rinfo.get('draft_number') or 999) - 1) // 32 + 1 if rinfo.get('draft_number') else '?'} "
            f"(Pick #{rinfo.get('draft_number','?')})\n"
            f"COLLEGE: {rinfo.get('college','?')}\n"
            f"AGE: {player.get('age','?')}\n"
            f"SCORING: {scoring.replace('_',' ').upper()}\n\n"
            "Produce the rookie outlook as instructed."
        )
    else:
        last_season = (player.get("seasons") or [{}])[-1]
        news_summary = "\n".join(
            f"- ({n.get('date','')}) {n.get('headline','')}: {n.get('snippet','')}" for n in news_items[:6]
        ) or "No recent news on record."

        inj_status = player.get("injury_status")
        inj_short = player.get("injury_short")
        inj_line = ""
        if inj_status:
            inj_line = f"INJURY (LIVE): {inj_status}"
            if inj_short:
                inj_line += f" — {inj_short[:200]}"
            inj_line += "\n"

        prompt = (
            f"{SYSTEM_MSG}\n\n"
            f"PLAYER: {player.get('name')} | {player.get('position')} | {player.get('team')}\n"
            f"AGE: {player.get('age', 'N/A')} | EXPERIENCE: {player.get('experience','N/A')} yrs\n"
            f"SCORING: {scoring.replace('_', ' ').upper()}\n"
            f"{inj_line}"
            f"LAST SEASON ({last_season.get('season','')}): "
            f"GP {last_season.get('games',0)}, FPTS/G {last_season.get('fpts_per_game_half_ppr',0)}, "
            f"YDs {last_season.get('total_yards',0)}, TDs {last_season.get('total_tds',0)}\n"
            f"NEWS:\n{news_summary}\n\n"
            "Produce the outlook as instructed."
        )

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = await model.generate_content_async(prompt)
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
            f"{fppg:.1f} FPts/G last yr | next: vs {opp} (D rank #{rank}{fpa_str}) | "
            f"injury: {inj} | tag: {tag}"
        )
    return "\n".join(lines)


async def generate_trade_verdict(*, side_a_label: str, side_b_label: str, side_a: dict, side_b: dict,
                                  diff: float, verdict: str, scoring: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "AI verdict unavailable: GEMINI_API_KEY not configured."

    prompt = (
        f"{TRADE_SYSTEM_MSG}\n\n"
        f"SCORING: {scoring.replace('_', ' ').upper()}\n"
        f"LAB-SCORE DIFF: {diff:+.1f} ({verdict.replace('_', ' ')})\n\n"
        f"{_format_trade_side(side_a_label, side_a)}\n\n"
        f"{_format_trade_side(side_b_label, side_b)}\n\n"
        "Produce the trade verdict as instructed."
    )

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = await model.generate_content_async(prompt)
        return response.text.strip()
    except Exception as e:
        return f"AI verdict unavailable: {e}"
