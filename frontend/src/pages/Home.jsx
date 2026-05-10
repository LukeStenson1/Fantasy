import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { Button } from "../components/ui/button";
import { api } from "../lib/api";
import { ArrowRight, BarChart3, Flame, Sparkles, TrendingUp, Trophy, Wand2 } from "lucide-react";
import { PositionBadge, TagBadge } from "../components/Badges";

export default function Home() {
  const [summary, setSummary] = useState({ total_players: 0, data_seasons: [], last_refresh: null });
  const [movers, setMovers] = useState({ sleepers: [], busts: [], breakouts: [], elites: [] });

  useEffect(() => {
    api.get("/stats/summary").then((r) => setSummary(r.data)).catch(() => {});
    api.get("/sleepers-busts", { params: { scoring: "half_ppr" } }).then((r) => setMovers(r.data)).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />

      {/* HERO */}
      <section className="relative overflow-hidden border-b border-slate-800" data-testid="hero-section">
        <div className="absolute inset-0 bg-grid opacity-30" />
        <div
          className="absolute inset-0 opacity-[0.10]"
          style={{
            backgroundImage:
              "url('https://images.unsplash.com/photo-1673846446973-bad1f01794f3?crop=entropy&cs=srgb&fm=jpg&q=85&w=2000')",
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[#0a0e16]/40 via-[#0a0e16]/70 to-[#0a0e16]" />
        <div className="absolute -top-32 -right-32 w-[500px] h-[500px] rounded-full bg-emerald-500/10 blur-3xl" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 text-[10px] font-bold tracking-[0.25em] uppercase text-emerald-400 mb-4 border border-emerald-500/30 bg-emerald-500/5 px-3 py-1 rounded">
              <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
              The Reference for Half-PPR · 12-Team Snake
            </div>
            <h1 className="font-display text-5xl sm:text-6xl lg:text-7xl font-black tracking-tight leading-[0.95] mb-6 text-white" data-testid="hero-title">
              Every stat.<br/>
              Every player.<br/>
              <span className="text-emerald-400">Engineered for fantasy.</span>
            </h1>
            <p className="text-lg text-slate-400 max-w-2xl mb-8">
              Real NFL seasonal data, AI-powered player outlooks, and a Lineup AI that builds your starters using
              matchup-adjusted Lab Scores. Sleepers, busts, and start/sit decisions — all in one place.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/stats">
                <Button size="lg" className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold h-12 px-6" data-testid="hero-browse-stats">
                  Browse Stats <ArrowRight className="ml-2 w-4 h-4" />
                </Button>
              </Link>
              <Link to="/lineup">
                <Button size="lg" variant="outline" className="h-12 px-6 border-slate-700 bg-transparent text-slate-200 hover:bg-slate-800 hover:text-white" data-testid="hero-lineup">
                  Build My Lineup <Wand2 className="ml-2 w-4 h-4" />
                </Button>
              </Link>
            </div>
          </div>

          {/* Data status strip */}
          <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-px bg-slate-800 border border-slate-800 rounded-md overflow-hidden max-w-3xl">
            <Stat icon={<BarChart3 className="w-4 h-4" />} label="Players" value={summary.total_players || "—"} />
            <Stat icon={<TrendingUp className="w-4 h-4" />} label="Seasons" value={(summary.data_seasons || []).join(" · ") || "—"} />
            <Stat icon={<Sparkles className="w-4 h-4" />} label="Source" value="nflverse" />
            <Stat icon={<Flame className="w-4 h-4" />} label="Updated" value={summary.last_refresh ? "Live" : "Cached"} />
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-[10px] font-bold tracking-[0.25em] uppercase text-emerald-400 mb-3">◆ The Toolkit</div>
        <h2 className="font-display text-3xl sm:text-4xl font-black tracking-tight text-white mb-12 max-w-2xl">Everything you need to win the week.</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <FeatureCard title="Stats Browser" desc="Filter & sort every fantasy-relevant player across multiple seasons. Click any row for the full profile, AI outlook, and team news." icon={<BarChart3 className="w-5 h-5" />} to="/stats" testid="feature-stats" />
          <FeatureCard title="Lineup AI" desc="Auto-built starting lineup using composite Lab Score: production, matchup, availability, and trend." icon={<Wand2 className="w-5 h-5" />} to="/lineup" testid="feature-lineup" highlight />
          <FeatureCard title="Start / Sit" desc="Add the players on your roster — we tell you exactly who to start this week with full reasoning." icon={<Trophy className="w-5 h-5" />} to="/start-sit" testid="feature-startsit" />
          <FeatureCard title="Sleepers & Busts" desc="Pre-tagged breakouts, sleepers, elites, and bust risks based on stat trajectories." icon={<Flame className="w-5 h-5" />} to="/sleepers-busts" testid="feature-radar" />
        </div>
      </section>

      {/* MOVERS */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <MoverList title="Breakout Candidates" players={movers.breakouts} accent="emerald" testid="mover-breakouts" />
          <MoverList title="Bust Risks" players={movers.busts} accent="red" testid="mover-busts" />
        </div>
      </section>

      <footer className="border-t border-slate-800 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="text-sm text-slate-500 font-mono-tab">FantasyLab · half-ppr default · 12-team snake</div>
          <div className="text-xs text-slate-600">Data via nflverse · refreshes daily · auto-rolls to next season when available.</div>
        </div>
      </footer>
    </div>
  );
}

function Stat({ icon, label, value }) {
  return (
    <div className="bg-[#0a0e16] p-4 flex flex-col gap-1">
      <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">{icon} {label}</div>
      <div className="font-display font-black text-xl tracking-tight text-white">{value}</div>
    </div>
  );
}

function FeatureCard({ title, desc, icon, to, testid, highlight = false }) {
  return (
    <Link to={to} className="block group" data-testid={testid}>
      <div className={`bg-slate-950/60 border h-full rounded-md p-5 transition-all hover:-translate-y-0.5 ${highlight ? "border-emerald-500/40 hover:border-emerald-500" : "border-slate-800 hover:border-slate-600"}`}>
        <div className={`w-10 h-10 ${highlight ? "bg-emerald-500 text-slate-950" : "bg-slate-800 text-emerald-400 group-hover:bg-emerald-500 group-hover:text-slate-950"} flex items-center justify-center rounded-md mb-4 transition-colors`}>
          {icon}
        </div>
        <h3 className="font-display text-lg font-bold mb-2 text-white">{title}</h3>
        <p className="text-sm text-slate-400 leading-relaxed">{desc}</p>
        <div className="mt-4 text-xs font-bold uppercase tracking-wider flex items-center gap-1 text-emerald-400">
          Open <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
        </div>
      </div>
    </Link>
  );
}

function MoverList({ title, players, accent, testid }) {
  const accentBar = accent === "emerald" ? "bg-emerald-500" : "bg-red-500";
  return (
    <div className="bg-slate-950/60 border border-slate-800 rounded-md overflow-hidden" data-testid={testid}>
      <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2">
        <div className={`w-1 h-5 ${accentBar}`} />
        <h3 className="font-display font-bold text-lg text-white">{title}</h3>
        <span className="text-xs text-slate-500 font-mono-tab ml-auto">{players?.length || 0} players</span>
      </div>
      <ul>
        {(players || []).slice(0, 8).map((p) => (
          <li key={p.id} className="px-4 py-3 border-b border-slate-800 last:border-b-0 flex items-center justify-between hover:bg-slate-900">
            <div className="flex items-center gap-3">
              <PositionBadge position={p.position} />
              <Link to={`/stats?focus=${p.id}`} className="font-semibold text-white hover:text-emerald-400" data-testid={`mover-link-${p.id}`}>{p.name}</Link>
              <span className="text-xs font-mono-tab text-slate-500">{p.team}</span>
            </div>
            <div className="flex items-center gap-3">
              <TagBadge tag={p.tag} />
              <span className="font-mono-tab text-sm text-emerald-300 font-bold">{p.current_fpts_per_game?.toFixed?.(1) ?? "—"}/g</span>
            </div>
          </li>
        ))}
        {(!players || players.length === 0) && (
          <li className="px-4 py-6 text-sm text-slate-500 text-center">No players in this category yet.</li>
        )}
      </ul>
    </div>
  );
}
