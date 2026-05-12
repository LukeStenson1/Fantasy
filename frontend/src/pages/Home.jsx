import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { Button } from "../components/ui/button";
import { api } from "../lib/api";
import { ArrowRight, ArrowRightLeft, Activity, BarChart3, Database, Flame, Sparkles, TrendingUp, Trophy, Wand2 } from "lucide-react";
import { PositionBadge, TagBadge, MatchupBadge } from "../components/Badges";
import AdSlot from "../components/AdSlot";

export default function Home() {
  const [summary, setSummary] = useState({ total_players: 0, data_seasons: [], last_refresh: null });
  const [movers, setMovers] = useState({ sleepers: [], busts: [], breakouts: [], elites: [] });
  const [matchups, setMatchups] = useState(null);

  useEffect(() => {
    api.get("/stats/summary").then((r) => setSummary(r.data)).catch(() => {});
    api.get("/sleepers-busts", { params: { scoring: "half_ppr" } }).then((r) => setMovers(r.data)).catch(() => {});
    api.get("/matchups/this-week").then((r) => setMatchups(r.data)).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />

      {/* HERO */}
      <section className="relative overflow-hidden border-b border-slate-800">
        <div className="absolute inset-0 bg-grid opacity-30" />
        <div className="relative max-w-7xl mx-auto px-4 py-20">

          {/* content unchanged... */}

        </div>
      </section>

      {/* MATCHUPS OF THE WEEK */}
      {matchups?.by_position && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {["RB", "WR", "QB", "TE"].map((pos) => (
              <MatchupColumn
                key={pos}
                pos={pos}
                data={matchups?.by_position?.[pos] ?? { soft: [], tough: [] }}
              />
            ))}
          </div>
        </section>
      )}

      {/* MOVERS */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <MoverList title="Breakout Candidates" players={movers?.breakouts ?? []} accent="emerald" />
          <MoverList title="Bust Risks" players={movers?.busts ?? []} accent="red" />
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
        <AdSlot slot="home-bottom" />
      </section>
    </div>
  );
}

/* ---------------- SAFE COMPONENTS ---------------- */

function MatchupColumn({ pos, data }) {
  const soft = data?.soft ?? [];
  const tough = data?.tough ?? [];

  return (
    <div className="bg-slate-950/60 border border-slate-800 rounded-md overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2">
        <PositionBadge position={pos} />
        <h3 className="font-bold text-white">{pos}s</h3>
      </div>

      <div className="px-4 pt-3 pb-1 text-[10px] uppercase text-emerald-400">Smash spots</div>
      <ul className="px-2">
        {soft.slice(0, 3).map((r, i) => (
          <li key={`s-${i}`} className="text-xs flex justify-between">
            <span>{r.offense_team}</span>
          </li>
        ))}
        {soft.length === 0 && <li className="text-xs text-slate-600">—</li>}
      </ul>

      <div className="px-4 pt-3 pb-1 text-[10px] uppercase text-red-400">Avoid</div>
      <ul className="px-2 pb-3">
        {tough.slice(0, 3).map((r, i) => (
          <li key={`t-${i}`} className="text-xs flex justify-between">
            <span>{r.offense_team}</span>
          </li>
        ))}
        {tough.length === 0 && <li className="text-xs text-slate-600">—</li>}
      </ul>
    </div>
  );
}

function MoverList({ title, players = [], accent }) {
  return (
    <div className="bg-slate-950/60 border border-slate-800 rounded-md">
      <div className="px-4 py-3 border-b border-slate-800">
        <h3 className="font-bold text-white">{title}</h3>
      </div>

      <ul>
        {(players ?? []).slice(0, 8).map((p) => (
          <li key={p.id} className="px-4 py-2 text-sm text-white">
            {p.name}
          </li>
        ))}
        {(!players || players.length === 0) && (
          <li className="px-4 py-4 text-sm text-slate-500">No players yet.</li>
        )}
      </ul>
    </div>
  );
}
