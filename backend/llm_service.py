"""LLM service for player outlook generation using Claude Sonnet 4.5 via Emergent LLM key."""
import os
import uuid
from emergentintegrations.llm.chat import LlmChat, UserMessage


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
    "outlook for their NFL career trajectory — NOT a single-week matchup. Cover: 1) Team fit & how the offense will "
    "deploy them, 2) Year-1 fantasy expectation (target/touch share, snap %), 3) Multi-year ceiling. As real-season "
    "games happen, this outlook should update naturally because new stats feed back into the dataset. "
    "Format as 3 short sections: Player + Team Fit, Year-1 Expectation, Long-Term Ceiling. Plain text, no markdown."
)


async def generate_player_outlook(player: dict, news_items: list, scoring: str = "half_ppr") -> str:
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return "AI outlook unavailable: EMERGENT_LLM_KEY not configured."

    is_rookie = (player.get("experience", 99) == 0) or (player.get("rookie_info") is not None)
    rinfo = player.get("rookie_info") or {}

    if is_rookie:
        prompt = (
            f"ROOKIE: {player.get('name')} | {player.get('position')} | {player.get('team')}\n"
            f"DRAFT: Round {((rinfo.get('draft_number') or 999) - 1) // 32 + 1 if rinfo.get('draft_number') else '?'} "
            f"(Pick #{rinfo.get('draft_number','?')})\n"
            f"COLLEGE: {rinfo.get('college','?')}\n"
            f"AGE: {player.get('age','?')}\n"
            f"SCORING: {scoring.replace('_',' ').upper()}\n\n"
            "Produce the rookie outlook as instructed."
        )
        sys_msg = ROOKIE_SYSTEM_MSG
    else:
        last_season = (player.get("seasons") or [{}])[-1]
        news_summary = "\n".join(
            f"- ({n.get('date','')}) {n.get('headline','')}: {n.get('snippet','')}" for n in news_items[:6]
        ) or "No recent news on record."
        prompt = (
            f"PLAYER: {player.get('name')} | {player.get('position')} | {player.get('team')}\n"
            f"AGE: {player.get('age', 'N/A')} | EXPERIENCE: {player.get('experience','N/A')} yrs\n"
            f"SCORING: {scoring.replace('_',' ').upper()}\n"
            f"LAST SEASON ({last_season.get('season','')}): "
            f"GP {last_season.get('games',0)}, FPTS/G {last_season.get('fpts_per_game_half_ppr',0)}, "
            f"YDs {last_season.get('total_yards',0)}, TDs {last_season.get('total_tds',0)}\n"
            f"NEWS:\n{news_summary}\n\n"
            "Produce the outlook as instructed."
        )
        sys_msg = SYSTEM_MSG

    chat = LlmChat(
        api_key=api_key,
        session_id=f"outlook-{player.get('id', uuid.uuid4())}",
        system_message=sys_msg,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    try:
        resp = await chat.send_message(UserMessage(text=prompt))
        return str(resp).strip()
    except Exception as e:
        return f"AI outlook unavailable: {e}"
