import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { Button } from "../components/ui/button";
import { api } from "../lib/api";
import { ArrowRight, BarChart3, Flame, TrendingDown, TrendingUp, Users } from "lucide-react";
import { PositionBadge, TagBadge } from "../components/Badges";

export default function Home() {
  const [summary, setSummary] = useState({ total_players: 0, total_users: 0, total_rankings: 0 });
  const [movers, setMovers] = useState({ sleepers: [], busts: [], breakouts: [], elites: [] });

  useEffect(() => {
    api.get("/stats/summary").then((r) => setSummary(r.data)).catch(() => {});
    api.get("/sleepers-busts", { params: { scoring: "half_ppr" } }).then((r) => setMovers(r.data)).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      {/* HERO */}
      <section className="relative overflow-hidden border-b border-slate-200" data-testid="hero-section">
        <div
          className="absolute inset-0 opacity-[0.18]"
          style={{
            backgroundImage:
              "url('https://images.unsplash.com/photo-1673846446973-bad1f01794f3?crop=entropy&cs=srgb&fm=jpg&q=85&w=2000')",
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-white/85 via-white/70 to-white" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28">
          <div className="max-w-3xl">
            <div className="text-xs font-bold tracking-[0.2em] uppercase text-emerald-700 mb-4">
              ◆ The Reference for Half-PPR · 12-Team Snake
            </div>
            <h1 className="font-display text-5xl sm:text-6xl lg:text-7xl font-black tracking-tight leading-[0.95] mb-6" data-testid="hero-title">
              Every stat.<br/>
              Every player.<br/>
              <span className="text-emerald-600">Built for fantasy.</span>
            </h1>
            <p className="text-lg text-slate-700 max-w-2xl mb-8">
              A clean, modern reference for fantasy football — multi-season filterable stats, player profiles
              with AI-powered outlooks, recent team news, and sleeper/bust signals to find your edge.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/stats">
                <Button size="lg" className="bg-black hover:bg-slate-800 text-white h-12 px-6" data-testid="hero-browse-stats">
                  Browse Stats <ArrowRight className="ml-2 w-4 h-4" />
                </Button>
              </Link>
              <Link to="/sleepers-busts">
                <Button size="lg" variant="outline" className="h-12 px-6" data-testid="hero-sleepers-busts">
                  Sleepers & Busts <Flame className="ml-2 w-4 h-4" />
                </Button>
              </Link>
            </div>
          </div>

          {/* Stats strip */}
          <div className="mt-16 grid grid-cols-3 gap-px bg-slate-200 border border-slate-200 rounded-md overflow-hidden max-w-2xl">
            <Stat icon={<Users className="w-4 h-4" />} label="Players" value={summary.total_players} />
            <Stat icon={<BarChart3 className="w-4 h-4" />} label="Seasons" value="2022 · 23 · 24" />
            <Stat icon={<TrendingUp className="w-4 h-4" />} label="Custom Rankings" value={summary.total_rankings} />
          </div>
        </div>
      </section>

      {/* FEATURE GRID */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <h2 className="font-display text-3xl font-bold tracking-tight mb-8">Tools to win your league.</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <FeatureCard
            title="Filterable Stats Browser"
            desc="Sort & filter every fantasy-relevant player by position, team, season, and scoring format. Pro Football Reference, modernized."
            icon={<BarChart3 className="w-5 h-5" />}
            to="/stats"
            cta="Open the table"
            testid="feature-stats"
          />
          <FeatureCard
            title="AI Player Outlooks"
            desc="Each profile generates a fresh fantasy outlook — accounting for stats, depth chart, scheme changes, and recent team news."
            icon={<Flame className="w-5 h-5" />}
            to="/stats"
            cta="See player profiles"
            testid="feature-outlooks"
          />
          <FeatureCard
            title="Sleeper & Bust Radar"
            desc="Identify breakout candidates, hidden gems, and players whose ADP doesn't match their outlook. Built for redraft."
            icon={<TrendingDown className="w-5 h-5" />}
            to="/sleepers-busts"
            cta="View the radar"
            testid="feature-radar"
          />
        </div>
      </section>

      {/* MOVERS */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <MoverList title="Breakout Candidates" players={movers.breakouts} accent="emerald" testid="mover-breakouts" />
          <MoverList title="Bust Risks" players={movers.busts} accent="red" testid="mover-busts" />
        </div>
      </section>

      <footer className="border-t border-slate-200 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-sm text-slate-600 font-mono-tab">FantasyRef · half-ppr default · 12-team snake</div>
          <div className="text-xs text-slate-500">Stats are reference data. Always verify with official sources.</div>
        </div>
      </footer>
    </div>
  );
}

function Stat({ icon, label, value }) {
  return (
    <div className="bg-white p-4 flex flex-col gap-1">
      <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500">{icon} {label}</div>
      <div className="font-display font-black text-2xl tracking-tight">{value}</div>
    </div>
  );
}

function FeatureCard({ title, desc, icon, to, cta, testid }) {
  return (
    <Link to={to} className="block group" data-testid={testid}>
      <div className="bg-white border border-slate-200 rounded-md p-6 h-full hover:border-black transition-colors">
        <div className="w-10 h-10 bg-slate-100 group-hover:bg-black group-hover:text-white flex items-center justify-center rounded-md mb-4 transition-colors">
          {icon}
        </div>
        <h3 className="font-display text-xl font-bold mb-2">{title}</h3>
        <p className="text-sm text-slate-600 mb-4 leading-relaxed">{desc}</p>
        <div className="text-sm font-semibold flex items-center gap-1 text-black">
          {cta} <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
        </div>
      </div>
    </Link>
  );
}

function MoverList({ title, players, accent, testid }) {
  const accentBar = accent === "emerald" ? "bg-emerald-600" : "bg-red-600";
  return (
    <div className="bg-white border border-slate-200 rounded-md overflow-hidden" data-testid={testid}>
      <div className="px-4 py-3 border-b border-slate-200 flex items-center gap-2">
        <div className={`w-1 h-5 ${accentBar}`} />
        <h3 className="font-display font-bold text-lg">{title}</h3>
        <span className="text-xs text-slate-500 font-mono-tab ml-auto">{players?.length || 0} players</span>
      </div>
      <ul>
        {(players || []).slice(0, 8).map((p) => (
          <li key={p.id} className="px-4 py-3 border-b border-slate-100 last:border-b-0 flex items-center justify-between hover:bg-slate-50">
            <div className="flex items-center gap-3">
              <PositionBadge position={p.position} />
              <Link to={`/player/${p.id}`} className="font-semibold hover:underline" data-testid={`mover-link-${p.id}`}>{p.name}</Link>
              <span className="text-xs font-mono-tab text-slate-500">{p.team}</span>
            </div>
            <div className="flex items-center gap-3">
              <TagBadge tag={p.tag} />
              <span className="font-mono-tab text-sm text-slate-700">{p.current_fpts_per_game?.toFixed?.(1) ?? "—"}/g</span>
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
