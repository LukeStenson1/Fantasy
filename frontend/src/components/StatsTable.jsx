import { useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronDown, ChevronRight, ExternalLink, RefreshCcw, Sparkles, Newspaper } from "lucide-react";
import { PositionBadge, TagBadge, InjuryBadge, MatchupBadge } from "./Badges";
import { api } from "../lib/api";
import { Button } from "./ui/button";

const COLUMNS_SKILL = [
  { key: "name", label: "Player", sortable: true },
  { key: "position", label: "Pos", sortable: true },
  { key: "team", label: "Tm", sortable: true },
  { key: "games", label: "G", sortable: true, fromCurrent: true, type: "num" },
  { key: "pass_yds", label: "Pass Yd", sortable: true, fromCurrent: true, type: "num" },
  { key: "pass_td", label: "Pass TD", sortable: true, fromCurrent: true, type: "num" },
  { key: "rush_yds", label: "Rush Yd", sortable: true, fromCurrent: true, type: "num" },
  { key: "rush_td", label: "Rush TD", sortable: true, fromCurrent: true, type: "num" },
  { key: "receptions", label: "Rec", sortable: true, fromCurrent: true, type: "num" },
  { key: "rec_yds", label: "Rec Yd", sortable: true, fromCurrent: true, type: "num" },
  { key: "rec_td", label: "Rec TD", sortable: true, fromCurrent: true, type: "num" },
  { key: "current_fpts", label: "FPts", sortable: true, type: "num", emphasize: true },
  { key: "current_fpts_per_game", label: "FPts/G", sortable: true, type: "num", emphasize: true },
];

const COLUMNS_K = [
  { key: "name", label: "Player", sortable: true },
  { key: "position", label: "Pos", sortable: true },
  { key: "team", label: "Tm", sortable: true },
  { key: "games", label: "G", sortable: true, fromCurrent: true, type: "num" },
  { key: "fg_made", label: "FGM", sortable: true, fromCurrent: true, type: "num" },
  { key: "fg_att", label: "FGA", sortable: true, fromCurrent: true, type: "num" },
  { key: "fg_pct", label: "FG%", sortable: true, fromCurrent: true, type: "num" },
  { key: "fg_made_40_49", label: "40-49", sortable: true, fromCurrent: true, type: "num" },
  { key: "fg_made_50_59", label: "50-59", sortable: true, fromCurrent: true, type: "num" },
  { key: "fg_made_60_", label: "60+", sortable: true, fromCurrent: true, type: "num" },
  { key: "pat_made", label: "PAT", sortable: true, fromCurrent: true, type: "num" },
  { key: "current_fpts", label: "FPts", sortable: true, type: "num", emphasize: true },
  { key: "current_fpts_per_game", label: "FPts/G", sortable: true, type: "num", emphasize: true },
];

const COLUMNS_DEF = [
  { key: "name", label: "Team D/ST", sortable: true },
  { key: "position", label: "Pos", sortable: true },
  { key: "team", label: "Tm", sortable: true },
  { key: "sacks", label: "Sacks", sortable: true, fromCurrent: true, type: "num" },
  { key: "interceptions", label: "INT", sortable: true, fromCurrent: true, type: "num" },
  { key: "fumbles_forced", label: "FF", sortable: true, fromCurrent: true, type: "num" },
  { key: "def_tds", label: "TD", sortable: true, fromCurrent: true, type: "num" },
  { key: "points_allowed", label: "Pts All", sortable: true, fromCurrent: true, type: "num" },
  { key: "pass_yards_allowed", label: "Pass Yds", sortable: true, fromCurrent: true, type: "num" },
  { key: "rush_yards_allowed", label: "Rush Yds", sortable: true, fromCurrent: true, type: "num" },
  { key: "yards_allowed", label: "Tot Yds", sortable: true, fromCurrent: true, type: "num" },
  { key: "next_opponent", label: "Next Opp", sortable: false },
  { key: "matchup_score", label: "Matchup", sortable: false },
];

const COLUMNS_NBA = [
  { key: "name", label: "Player", sortable: true },
  { key: "position", label: "Pos", sortable: true },
  { key: "team", label: "Tm", sortable: true },
  { key: "games", label: "G", sortable: true, fromCurrent: true, type: "num" },
  { key: "pts", label: "PTS", sortable: true, fromCurrent: true, type: "num" },
  { key: "reb", label: "REB", sortable: true, fromCurrent: true, type: "num" },
  { key: "ast", label: "AST", sortable: true, fromCurrent: true, type: "num" },
  { key: "stl", label: "STL", sortable: true, fromCurrent: true, type: "num" },
  { key: "blk", label: "BLK", sortable: true, fromCurrent: true, type: "num" },
  { key: "tov", label: "TO", sortable: true, fromCurrent: true, type: "num" },
  { key: "fg3m", label: "3PM", sortable: true, fromCurrent: true, type: "num" },
  { key: "current_fpts", label: "FPts", sortable: true, type: "num", emphasize: true },
  { key: "current_fpts_per_game", label: "FPts/G", sortable: true, type: "num", emphasize: true },
];

const COLUMNS_MLB_BATTER = [
  { key: "name", label: "Player", sortable: true },
  { key: "position", label: "Pos", sortable: true },
  { key: "team", label: "Tm", sortable: true },
  { key: "G", label: "G", sortable: true, fromCurrent: true, type: "num" },
  { key: "H", label: "HA", sortable: true, fromCurrent: true, type: "num" },
  { key: "R", label: "R", sortable: true, fromCurrent: true, type: "num" },
  { key: "HR", label: "HR", sortable: true, fromCurrent: true, type: "num" },
  { key: "RBI", label: "RBI", sortable: true, fromCurrent: true, type: "num" },
  { key: "SB", label: "SB", sortable: true, fromCurrent: true, type: "num" },
  { key: "AVG", label: "AVG", sortable: true, fromCurrent: true, type: "num" },
  { key: "OPS", label: "OPS", sortable: true, fromCurrent: true, type: "num" },
  { key: "current_fpts", label: "FPts", sortable: true, type: "num", emphasize: true },
  { key: "current_fpts_per_game", label: "FPts/G", sortable: true, type: "num", emphasize: true },
];

const COLUMNS_MLB_PITCHER = [
  { key: "name", label: "Player", sortable: true },
  { key: "position", label: "Pos", sortable: true },
  { key: "team", label: "Tm", sortable: true },
  { key: "G", label: "G", sortable: true, fromCurrent: true, type: "num" },
  { key: "IP", label: "IP", sortable: true, fromCurrent: true, type: "num" },
  { key: "W", label: "W", sortable: true, fromCurrent: true, type: "num" },
  { key: "SV", label: "SV", sortable: true, fromCurrent: true, type: "num" },
  { key: "SO", label: "K", sortable: true, fromCurrent: true, type: "num" },
  { key: "ERA", label: "ERA", sortable: true, fromCurrent: true, type: "num" },
  { key: "WHIP", label: "WHIP", sortable: true, fromCurrent: true, type: "num" },
  { key: "current_fpts", label: "FPts", sortable: true, type: "num", emphasize: true },
  { key: "current_fpts_per_game", label: "FPts/G", sortable: true, type: "num", emphasize: true },
];

function getColumns(rows, sport) {
  if (sport === "nba") return COLUMNS_NBA;
  if (sport === "mlb") {
    const positions = new Set((rows || []).map(r => r.position));
    const hasPitcher = positions.has("SP") || positions.has("RP");
    const hasBatter = positions.has("C") || positions.has("1B") || positions.has("2B") ||
      positions.has("3B") || positions.has("SS") || positions.has("OF") || positions.has("DH");
    if (hasPitcher && !hasBatter) return COLUMNS_MLB_PITCHER;
    return COLUMNS_MLB_BATTER;
  }
  if (!rows || rows.length === 0) return COLUMNS_SKILL;
  const positions = new Set(rows.map((r) => r.position));
  if (positions.has("DEF") && positions.size === 1) return COLUMNS_DEF;
  if (positions.has("K") && positions.size === 1) return COLUMNS_K;
  return COLUMNS_SKILL;
}

function getValue(p, col) {
  if (col.key === "current_fpts" || col.key === "current_fpts_per_game") return p[col.key];
  if (col.key === "next_opponent") return p.next_opponent || "—";
  if (col.key === "matchup_score") return p.matchup_score;
  if (col.fromCurrent) return p.current_season?.[col.key];
  return p[col.key];
}

export default function StatsTable({ rows, scoring, sport = "nfl" }) {
  const [sortKey, setSortKey] = useState("current_fpts");
  const [dir, setDir] = useState("desc");
  const [expandedId, setExpandedId] = useState(null);

  const columns = useMemo(() => getColumns(rows, sport), [rows, sport]);

  const sorted = useMemo(() => {
    const arr = [...rows];
    arr.sort((a, b) => {
      const col = columns.find((c) => c.key === sortKey) || columns[0];
      const av = getValue(a, col);
      const bv = getValue(b, col);
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "number" && typeof bv === "number")
        return dir === "asc" ? av - bv : bv - av;
      return dir === "asc"
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
    return arr;
  }, [rows, sortKey, dir, columns]);

  const onSort = (key) => {
    if (sortKey === key) setDir(dir === "asc" ? "desc" : "asc");
    else { setSortKey(key); setDir("desc"); }
  };

  const SortIcon = ({ k }) => {
    if (sortKey !== k) return <ArrowUpDown className="w-3 h-3 inline opacity-30" />;
    return dir === "asc" ? <ArrowUp className="w-3 h-3 inline text-emerald-400" /> : <ArrowDown className="w-3 h-3 inline text-emerald-400" />;
  };

  return (
    <div className="overflow-auto border border-slate-800 rounded-md bg-slate-950/60" data-testid="stats-table-wrapper">
      <table className="pfr-table w-full" data-testid="stats-table">
        <thead>
          <tr>
            <th style={{width: 28}}></th>
            {columns.map((c) => (
              <th key={c.key} onClick={() => c.sortable && onSort(c.key)}
                className={`text-left whitespace-nowrap ${c.emphasize ? "text-emerald-300" : ""}`}
                data-testid={`col-header-${c.key}`}>
                {c.label} {c.sortable && <SortIcon k={c.key} />}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 && (
            <tr><td colSpan={columns.length + 1} className="text-center py-8 text-slate-500">No players match these filters.</td></tr>
          )}
          {sorted.map((p) => (
            <PlayerRow
              key={p.id}
              player={p}
              expanded={expandedId === p.id}
              onToggle={() => setExpandedId(expandedId === p.id ? null : p.id)}
              scoring={scoring}
              columns={columns}
              sport={sport}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PlayerRow({ player, expanded, onToggle, scoring, columns, sport }) {
  const p = player;
  return (
    <>
      <tr className="pfr-row" onClick={onToggle} data-testid={`row-${p.id}`}>
        <td className="px-2 text-slate-500">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </td>
        <td className="font-semibold text-white">
          <div className="flex items-center gap-2">
            <span data-testid={`player-name-${p.id}`}>{p.name}</span>
            <TagBadge tag={p.tag} />
            <InjuryBadge status={p.injury_status} short={p.injury_short} />
          </div>
        </td>
        <td><PositionBadge position={p.position} /></td>
        <td className="font-mono-tab text-slate-400">{p.team}</td>
        {columns.slice(3).map((c) => {
          const v = getValue(p, c);
          let formatted;
          if (c.key === "matchup_score") {
            if (v == null) formatted = "—";
            else {
              const color = v >= 1 ? "text-emerald-400" : v <= -1 ? "text-red-400" : "text-slate-300";
              formatted = <span className={`font-mono-tab font-bold ${color}`}>{v > 0 ? `+${v}` : v}</span>;
            }
          } else {
            const MLB_RATIO_KEYS = new Set(["AVG", "OBP", "SLG", "OPS", "fg_pct", "ft_pct"]);
            formatted = v == null ? "—" :
              c.key === "season" ? String(v) :
              MLB_RATIO_KEYS.has(c.key) ? (typeof v === "number" ? v.toFixed(3).replace(/^0\./, ".") : v) :
              typeof v === "number" ? v.toLocaleString() : v;
          }
          return (
            <td key={c.key} className={`font-mono-tab ${c.emphasize ? "font-bold text-emerald-300" : "text-slate-300"}`}>
              {formatted}
            </td>
          );
        })}
      </tr>
      {expanded && (
        <tr className="expand-row" data-testid={`expand-row-${p.id}`}>
          <td colSpan={columns.length + 1} className="bg-slate-900/40 border-t border-emerald-500/20 p-0">
            <ExpandedContent player={p} scoring={scoring} sport={sport} />
          </td>
        </tr>
      )}
    </>
  );
}

function ExpandedContent({ player, scoring, sport = "nfl" }) {
  const [full, setFull] = useState(null);
  const [outlook, setOutlook] = useState(null);
  const [loadingOutlook, setLoadingOutlook] = useState(false);

  useEffect(() => {
    api.get(`/players/${player.id}`, { params: { scoring } }).then((r) => setFull(r.data));
  }, [player.id, scoring]);

  const loadOutlook = (regen = false) => {
    setLoadingOutlook(true);
    if (regen) {
      api.post(`/players/${player.id}/outlook/regenerate`, null, { params: { scoring } })
        .then((r) => setOutlook(r.data))
        .finally(() => setLoadingOutlook(false));
    } else {
      api.get(`/players/${player.id}/outlook`, { params: { scoring } })
        .then((r) => setOutlook(r.data))
        .finally(() => setLoadingOutlook(false));
    }
  };

  if (!full) return <div className="p-6 text-slate-500 text-sm">Loading…</div>;
  const seasons = full.seasons || [];
  const isDef = full.position === "DEF";
  const isK = full.position === "K";

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-wrap items-center gap-4">
        <div>
          <div className="text-[10px] font-bold tracking-[0.2em] uppercase text-slate-500">Player</div>
          <div className="font-display text-2xl font-bold text-white">{full.name}</div>
        </div>
        <div className="flex flex-wrap gap-3 ml-auto">
          {!isDef && !isK && <Stat label="Age" value={full.age ?? "—"} />}
          {!isDef && !isK && <Stat label="Yrs" value={full.experience ?? "—"} />}
          {full.next_opponent && <Stat label="Next Opp" value={full.next_opponent} />}
          {full.matchup_def_rank && !isDef && (
            <div className="border border-slate-800 rounded-md px-3 py-2 bg-slate-950/40">
              <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-slate-500">vs {full.position} D</div>
              <div className="flex items-center gap-2 mt-0.5">
                <MatchupBadge
                  rank={full.matchup_def_rank}
                  opp={full.next_opponent}
                  position={full.position}
                  fptsAllowed={full.matchup_def_fpts_allowed}
                  source={full.matchup_def_source}
                />
                {full.matchup_def_fpts_allowed && (
                  <span className="text-[10px] font-mono-tab text-slate-400">{full.matchup_def_fpts_allowed.toFixed(1)} allowed/G</span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Career stats — position-appropriate */}
      {!isDef && seasons.length > 0 && (
        <div>
          <div className="text-[10px] font-bold tracking-[0.2em] uppercase text-slate-500 mb-2">Career Production</div>
          <div className="overflow-auto border border-slate-800 rounded-md bg-slate-950/40">
            <table className="pfr-table w-full" data-testid={`career-table-${player.id}`}>
              <thead><tr>
                <th>Season</th><th>G</th>
                {sport === "nba" && <><th>PTS</th><th>REB</th><th>AST</th><th>STL</th><th>BLK</th><th>TO</th><th>3PM</th><th>FG%</th><th>FT%</th></>}
                {sport === "mlb" && full.player_type === "pitcher" && <><th>IP</th><th>W</th><th>SV</th><th>K</th><th>ERA</th><th>WHIP</th></>}
                {sport === "mlb" && full.player_type !== "pitcher" && <><th>H</th><th>R</th><th>HR</th><th>RBI</th><th>SB</th><th>AVG</th><th>OPS</th></>}
                {sport === "nfl" && !isK && <><th>Pass Yd</th><th>Pass TD</th><th>INT</th><th>Rush Yd</th><th>Rush TD</th><th>Rec</th><th>Tgt</th><th>Rec Yd</th><th>Rec TD</th></>}
                {sport === "nfl" && isK && <><th>FGM</th><th>FGA</th><th>FG%</th><th>40-49</th><th>50-59</th><th>60+</th><th>PAT</th></>}
                <th className="text-emerald-300">FPts</th><th className="text-emerald-300">FPts/G</th>
              </tr></thead>
              <tbody>
                {seasons.map((s) => (
                  <tr key={s.season}>
                    <td className="font-bold text-white">{s.season}</td>
                    <td className="font-mono-tab">{s.games ?? s.G}</td>
                    {sport === "nba" && <>
                      <td className="font-mono-tab">{s.pts ?? "—"}</td>
                      <td className="font-mono-tab">{s.reb ?? "—"}</td>
                      <td className="font-mono-tab">{s.ast ?? "—"}</td>
                      <td className="font-mono-tab">{s.stl ?? "—"}</td>
                      <td className="font-mono-tab">{s.blk ?? "—"}</td>
                      <td className="font-mono-tab">{s.tov ?? "—"}</td>
                      <td className="font-mono-tab">{s.fg3m ?? "—"}</td>
                      <td className="font-mono-tab">{s.fg_pct ?? "—"}</td>
                      <td className="font-mono-tab">{s.ft_pct ?? "—"}</td>
                    </>}
                    {sport === "mlb" && full.player_type === "pitcher" && <>
                      <td className="font-mono-tab">{s.IP ?? "—"}</td>
                      <td className="font-mono-tab">{s.W ?? "—"}</td>
                      <td className="font-mono-tab">{s.SV ?? "—"}</td>
                      <td className="font-mono-tab">{s.SO ?? "—"}</td>
                      <td className="font-mono-tab">{s.ERA ?? "—"}</td>
                      <td className="font-mono-tab">{s.WHIP ?? "—"}</td>
                    </>}
                    {sport === "mlb" && full.player_type !== "pitcher" && <>
                      <td className="font-mono-tab">{s.H ?? "—"}</td>
                      <td className="font-mono-tab">{s.R ?? "—"}</td>
                      <td className="font-mono-tab">{s.HR ?? "—"}</td>
                      <td className="font-mono-tab">{s.RBI ?? "—"}</td>
                      <td className="font-mono-tab">{s.SB ?? "—"}</td>
                      <td className="font-mono-tab">{s.AVG != null ? s.AVG.toFixed(3).replace(/^0\./, ".") : "—"}</td>
                      <td className="font-mono-tab">{s.OPS != null ? s.OPS.toFixed(3).replace(/^0\./, ".") : "—"}</td>
                    </>}
                    {sport === "nfl" && !isK && <>
                      <td className="font-mono-tab">{s.pass_yds?.toLocaleString() || "—"}</td>
                      <td className="font-mono-tab">{s.pass_td || "—"}</td>
                      <td className="font-mono-tab">{s.pass_int || "—"}</td>
                      <td className="font-mono-tab">{s.rush_yds?.toLocaleString() || "—"}</td>
                      <td className="font-mono-tab">{s.rush_td || "—"}</td>
                      <td className="font-mono-tab">{s.receptions || "—"}</td>
                      <td className="font-mono-tab">{s.targets || "—"}</td>
                      <td className="font-mono-tab">{s.rec_yds?.toLocaleString() || "—"}</td>
                      <td className="font-mono-tab">{s.rec_td || "—"}</td>
                    </>}
                    {sport === "nfl" && isK && <>
                      <td className="font-mono-tab">{s.fg_made ?? "—"}</td>
                      <td className="font-mono-tab">{s.fg_att ?? "—"}</td>
                      <td className="font-mono-tab">{s.fg_pct ? `${s.fg_pct}%` : "—"}</td>
                      <td className="font-mono-tab">{s.fg_made_40_49 ?? "—"}</td>
                      <td className="font-mono-tab">{s.fg_made_50_59 ?? "—"}</td>
                      <td className="font-mono-tab">{s.fg_made_60_ ?? "—"}</td>
                      <td className="font-mono-tab">{s.pat_made ?? "—"}</td>
                    </>}
                    <td className="font-mono-tab font-bold text-emerald-300">
                      {sport === "nfl" ? s[`fpts_${scoring}`] : s.fpts}
                    </td>
                    <td className="font-mono-tab font-bold text-emerald-300">
                      {sport === "nfl" ? s[`fpts_per_game_${scoring}`] : s.fpts_per_game}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {isDef && seasons.length > 0 && (
        <div>
          <div className="text-[10px] font-bold tracking-[0.2em] uppercase text-slate-500 mb-2">Defensive Stats</div>
          <div className="overflow-auto border border-slate-800 rounded-md bg-slate-950/40">
            <table className="pfr-table w-full">
              <thead><tr>
                <th>Season</th>
                <th>Sacks</th>
                <th>INT</th>
                <th>FF</th>
                <th>FR</th>
                <th>DEF TD</th>
                <th>Pts Allowed</th>
                <th>Pass Yds</th>
                <th>Rush Yds</th>
                <th>Tot Yds</th>
              </tr></thead>
              <tbody>
                {seasons.map((s) => (
                  <tr key={s.season}>
                    <td className="font-bold text-white">{s.season}</td>
                    <td className="font-mono-tab">{s.sacks ?? "—"}</td>
                    <td className="font-mono-tab">{s.interceptions ?? "—"}</td>
                    <td className="font-mono-tab">{s.fumbles_forced ?? "—"}</td>
                    <td className="font-mono-tab">{s.fumbles_recovered ?? "—"}</td>
                    <td className="font-mono-tab">{s.def_tds ?? "—"}</td>
                    <td className="font-mono-tab">{s.points_allowed ?? "—"}</td>
                    <td className="font-mono-tab">{s.pass_yards_allowed?.toLocaleString() ?? "—"}</td>
                    <td className="font-mono-tab">{s.rush_yards_allowed?.toLocaleString() ?? "—"}</td>
                    <td className="font-mono-tab">{s.yards_allowed?.toLocaleString() ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {isDef && seasons.length === 0 && (
        <div className="bg-slate-950/40 border border-slate-800 rounded-md p-4">
          <div className="text-[10px] font-bold tracking-[0.2em] uppercase text-slate-500 mb-2">Defense Info</div>
          <p className="text-sm text-slate-400">
            D/ST units are scored using opponent offensive profile. Check the matchup score above for this week's outlook.
            Use the Lineup tool to get a full Lab Score for your D/ST.
          </p>
        </div>
      )}

      {/* AI Outlook + News */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-slate-950/40 border border-slate-800 rounded-md" data-testid={`outlook-${player.id}`}>
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              <h3 className="font-display font-bold text-white">AI Outlook</h3>
            </div>
            <div className="flex gap-1">
              <Button variant="ghost" size="sm" onClick={() => loadOutlook(false)} disabled={loadingOutlook}
                className="h-7 text-xs border border-slate-700 bg-transparent hover:bg-slate-800 text-slate-300">
                {outlook ? "Reload" : "Generate"}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => loadOutlook(true)} disabled={loadingOutlook}
                className="h-7 text-xs border border-slate-700 bg-transparent hover:bg-slate-800 text-slate-300">
                <RefreshCcw className="w-3 h-3" />
              </Button>
            </div>
          </div>
          <div className="p-4">
            {!outlook && !loadingOutlook && <p className="text-sm text-slate-500">Click Generate to produce an AI fantasy outlook.</p>}
            {loadingOutlook && <p className="text-sm text-slate-500">Generating outlook…</p>}
            {outlook && (
              <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-200" data-testid={`outlook-text-${player.id}`}>
                {outlook.outlook}
              </pre>
            )}
          </div>
        </div>

        <div className="bg-slate-950/40 border border-slate-800 rounded-md" data-testid={`news-${player.id}`}>
          <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800">
            <Newspaper className="w-4 h-4 text-slate-400" />
            <h3 className="font-display font-bold text-white">Team News & Insights</h3>
            {full.news_search_url && (
              <a href={full.news_search_url} target="_blank" rel="noopener noreferrer"
                className="ml-auto text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
                data-testid={`news-search-link-${player.id}`}>
                Latest news <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
          <div className="p-4">
            {(full.news || []).length === 0 && (
              <p className="text-sm text-slate-500">
                No indexed beat-reporter news yet. Click "Latest news" above to see real headlines from credible NFL sources, or generate the AI Outlook for trajectory-based analysis.
              </p>
            )}
            <ul className="space-y-3">
              {(full.news || []).map((n, i) => (
                <li key={i} className="text-sm">
                  <div className="text-[10px] font-mono-tab text-slate-500 mb-0.5">{n.date} · <span className="font-bold uppercase">{n.source}</span></div>
                  {n.url ? (
                    <a href={n.url} target="_blank" rel="noopener noreferrer" className="font-bold text-white hover:text-emerald-400">
                      {n.headline} <ExternalLink className="inline w-3 h-3" />
                    </a>
                  ) : (
                    <div className="font-bold text-white">{n.headline}</div>
                  )}
                  <div className="text-slate-400">{n.snippet}</div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, accent = "text-slate-200" }) {
  return (
    <div className="border border-slate-800 rounded-md px-3 py-2 bg-slate-950/40">
      <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-slate-500">{label}</div>
      <div className={`font-mono-tab font-bold text-base ${accent}`}>{value}</div>
    </div>
  );
}
