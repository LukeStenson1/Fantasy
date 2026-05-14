import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { api } from "../lib/api";
import AdSlot from "../components/AdSlot";
import { PositionBadge } from "../components/Badges";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { TrendingUp, TrendingDown, Zap, Star, ChevronRight } from "lucide-react";

const SCORINGS = [
  { v: "half_ppr", l: "Half PPR" },
  { v: "ppr", l: "PPR" },
  { v: "standard", l: "Standard" },
];

const TAG_STYLES = {
  elite:    "bg-emerald-500/15 text-emerald-300 border border-emerald-500/40",
  breakout: "bg-blue-500/15 text-blue-300 border border-blue-500/40",
  sleeper:  "bg-violet-500/15 text-violet-300 border border-violet-500/40",
  risk:     "bg-red-500/15 text-red-300 border border-red-500/40",
};

const TAG_LABELS = {
  elite:    "ELITE",
  breakout: "BREAKOUT",
  sleeper:  "SLEEPER",
  risk:     "BUST RISK",
};

const safeObject = (v, fallback = {}) =>
  v && typeof v === "object" ? v : fallback;

export default function Home() {
  const [scoring, setScoring] = useState("half_ppr");
  const [summary, setSummary] = useState({ total_players: 0, data_seasons: [], last_refresh: null });
  const [movers, setMovers] = useState({ sleepers: [], busts: [], breakouts: [], elites: [] });
  const [matchups, setMatchups] = useState({});
  const [loadingMovers, setLoadingMovers] = useState(true);

  useEffect(() => {
    api.get("/stats/summary")
      .then((r) => setSummary(safeObject(r.data)))
      .catch(() => {});
    api.get("/matchups/this-week")
      .then((r) => setMatchups(safeObject(r.data)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setLoadingMovers(true);
    api.get("/sleepers-busts", { params: { scoring } })
      .then((r) => {
        setMovers({
          sleepers:  r.data?.sleepers  || [],
          busts:     r.data?.busts     || [],
          breakouts: r.data?.breakouts || [],
          elites:    r.data?.elites    || [],
        });
      })
      .catch(() => {})
      .finally(() => setLoadingMovers(false));
  }, [scoring]);

  const byPos = matchups?.by_position ?? {};
  const week  = matchups?.week;

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />

      {/* HEADER */}
      <div className="border-b border-slate-800 bg-slate-950/60">
        <div className="max-w-7xl mx-auto px-4 py-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="text-[10px] font-bold tracking-[0.25em] uppercase text-emerald-400 mb-2">◆ The Lab · Command Center</div>
            <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight text-white">Dashboard</h1>
            <p className="text-slate-400 mt-2">
              {summary.total_players > 0
                ? `${summary.total_players} players · seasons ${(summary.data_seasons || []).join(", ")}`
                : "Live fantasy intelligence"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400 uppercase tracking-widest">Scoring</span>
            <Select value={scoring} onValueChange={setScoring}>
              <SelectTrigger className="w-[130px] bg-slate-900 text-white border-slate-700">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SCORINGS.map((s) => (
                  <SelectItem key={s.v} value={s.v}>{s.l}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* MATCHUPS */}
      <section className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-white font-bold text-lg tracking-tight">
            This Week's Matchups
            {week ? <span className="ml-2 text-slate-500 text-sm font-normal">Week {week}</span> : null}
          </h2>
          <Link to="/stats" className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1">
            All players <ChevronRight className="w-3 h-3" />
          </Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {["RB", "WR", "QB", "TE"].map((pos) => (
            <MatchupColumn key={pos} pos={pos} data={byPos[pos] || { soft: [], tough: [] }} />
          ))}
        </div>
      </section>

      {/* MOVERS */}
      <section className="max-w-7xl mx-auto px-4 pb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-white font-bold text-lg tracking-tight">Players to Watch</h2>
          <Link to="/sleepers-busts" className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1">
            Full analysis <ChevronRight className="w-3 h-3" />
          </Link>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <MoverList title="Breakout Candidates" icon={<Zap className="w-4 h-4 text-blue-400" />} players={movers.breakouts} tag="breakout" loading={loadingMovers} scoring={scoring} />
          <MoverList title="Elite Producers" icon={<Star className="w-4 h-4 text-emerald-400" />} players={movers.elites} tag="elite" loading={loadingMovers} scoring={scoring} />
          <MoverList title="Sleeper Picks" icon={<TrendingUp className="w-4 h-4 text-violet-400" />} players={movers.sleepers} tag="sleeper" loading={loadingMovers} scoring={scoring} />
          <MoverList title="Bust Risks" icon={<TrendingDown className="w-4 h-4 text-red-400" />} players={movers.busts} tag="risk" loading={loadingMovers} scoring={scoring} />
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 pb-20">
        <AdSlot slot="home-bottom" />
      </section>
    </div>
  );
}

function MatchupColumn({ pos, data }) {
  const soft  = data?.soft  || [];
  const tough = data?.tough || [];

  return (
    <div className="bg-slate-950/60 border border-slate-800 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800">
        <PositionBadge position={pos} />
        <span className="text-white font-bold text-sm">{pos} Matchups</span>
      </div>
      <div className="px-4 pt-3 pb-1">
        <div className="text-[10px] font-bold tracking-widest text-emerald-400 uppercase mb-2">✦ Smash</div>
        {soft.slice(0, 3).map((r, i) => (
          <div key={i} className="flex items-center justify-between py-1.5 border-b border-slate-800/50 last:border-0">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 w-4">{i + 1}</span>
              <span className="text-sm text-white font-semibold">{r.offense_team || "—"}</span>
              <span className="text-xs text-slate-500">vs {r.opp_team || "—"}</span>
            </div>
            {r.fpts_allowed_per_game != null && (
              <span className="text-xs text-emerald-400 font-mono">{r.fpts_allowed_per_game.toFixed(1)}</span>
            )}
          </div>
        ))}
        {soft.length === 0 && <div className="text-xs text-slate-600 py-2">No data</div>}
      </div>
      <div className="px-4 pt-2 pb-3">
        <div className="text-[10px] font-bold tracking-widest text-red-400 uppercase mb-2">✦ Avoid</div>
        {tough.slice(0, 3).map((r, i) => (
          <div key={i} className="flex items-center justify-between py-1.5 border-b border-slate-800/50 last:border-0">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 w-4">{i + 1}</span>
              <span className="text-sm text-white font-semibold">{r.offense_team || "—"}</span>
              <span className="text-xs text-slate-500">vs {r.opp_team || "—"}</span>
            </div>
            {r.fpts_allowed_per_game != null && (
              <span className="text-xs text-red-400 font-mono">{r.fpts_allowed_per_game.toFixed(1)}</span>
            )}
          </div>
        ))}
        {tough.length === 0 && <div className="text-xs text-slate-600 py-2">No data</div>}
      </div>
    </div>
  );
}

function MoverList({ title, icon, players = [], tag, loading, scoring }) {
  const safePlayers = Array.isArray(players) ? players : [];
  const fppgKey = `fpts_per_game_${scoring}`;

  return (
    <div className="bg-slate-950/60 border border-slate-800 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800">
        {icon}
        <span className="text-white font-bold text-sm">{title}</span>
        <span className="ml-auto text-xs text-slate-500">{safePlayers.length} players</span>
      </div>
      <div>
        {loading && <div className="px-4 py-6 text-slate-500 text-sm">Loading...</div>}
        {!loading && safePlayers.length === 0 && (
          <div className="px-4 py-6 text-slate-500 text-sm">No players tagged.</div>
        )}
        {!loading && safePlayers.slice(0, 6).map((p, i) => {
          const fppg = p.current_fpts_per_game ?? p[fppgKey] ?? p.current_season?.[fppgKey];
          const season = p.current_season?.season ?? p.season;
          return (
            <Link
              key={p.id}
              to={`/stats?search=${encodeURIComponent(p.name)}`}
              className="flex items-center gap-3 px-4 py-3 border-b border-slate-800/50 last:border-0 hover:bg-slate-800/40 transition-colors group"
            >
              <span className="text-xs text-slate-600 w-4 shrink-0">{i + 1}</span>
              <PositionBadge position={p.position} />
              <div className="flex-1 min-w-0">
                <div className="text-sm text-white font-semibold truncate group-hover:text-emerald-400 transition-colors">
                  {p.name}
                </div>
                <div className="text-xs text-slate-500">{p.team}{season ? ` · ${season}` : ""}</div>
              </div>
              {tag && (
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${TAG_STYLES[tag]}`}>
                  {TAG_LABELS[tag]}
                </span>
              )}
              {fppg != null && (
                <div className="text-right shrink-0">
                  <div className="text-sm text-white font-mono font-semibold">{Number(fppg).toFixed(1)}</div>
                  <div className="text-[10px] text-slate-500">pts/g</div>
                </div>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
