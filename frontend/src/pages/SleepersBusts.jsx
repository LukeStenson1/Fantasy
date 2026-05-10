import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { api } from "../lib/api";
import { Link } from "react-router-dom";
import { PositionBadge, TagBadge } from "../components/Badges";
import { TrendingUp, TrendingDown, Flame, Star } from "lucide-react";

const SECTIONS = [
  { key: "elites", title: "Elite Tier", icon: Star, accent: "bg-emerald-500", desc: "Established top-shelf fantasy producers." },
  { key: "breakouts", title: "Breakouts", icon: Flame, accent: "bg-emerald-500/30", desc: "Players whose recent trajectory points up." },
  { key: "sleepers", title: "Sleepers", icon: TrendingUp, accent: "bg-blue-500/40", desc: "Undervalued targets with upside paths." },
  { key: "busts", title: "Bust Risks", icon: TrendingDown, accent: "bg-red-500/40", desc: "Volatility, injury, or scheme concerns." },
];

export default function SleepersBusts() {
  const [data, setData] = useState({ sleepers: [], busts: [], breakouts: [], elites: [] });

  useEffect(() => {
    api.get("/sleepers-busts", { params: { scoring: "half_ppr" } }).then((r) => setData(r.data));
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />
      <div className="border-b border-slate-800 bg-slate-950/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-[10px] font-bold tracking-[0.25em] uppercase text-emerald-400 mb-2">◆ The Lab · Draft Radar</div>
          <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight text-white" data-testid="sb-title">Sleepers & Busts</h1>
          <p className="text-slate-400 mt-2">Players grouped by fantasy outlook tag — auto-tagged from stat trajectories. Tuned for half-PPR, 12-team snake.</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 grid grid-cols-1 md:grid-cols-2 gap-4">
        {SECTIONS.map((s) => {
          const Icon = s.icon;
          const list = data[s.key] || [];
          return (
            <div key={s.key} className="bg-slate-950/60 border border-slate-800 rounded-md overflow-hidden" data-testid={`section-${s.key}`}>
              <div className="px-5 py-4 border-b border-slate-800 flex items-center gap-3">
                <div className={`w-9 h-9 ${s.accent} text-slate-950 flex items-center justify-center rounded-md`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="flex-1">
                  <h2 className="font-display font-bold text-xl text-white leading-tight">{s.title}</h2>
                  <div className="text-xs text-slate-500">{s.desc}</div>
                </div>
                <span className="font-mono-tab text-sm text-slate-400 font-bold">{list.length}</span>
              </div>
              <ul className="max-h-[480px] overflow-auto">
                {list.length === 0 && <li className="px-5 py-6 text-sm text-slate-500 text-center">No players tagged here.</li>}
                {list.map((p) => (
                  <li key={p.id} className="px-5 py-3 border-b border-slate-800 last:border-b-0 flex items-center justify-between hover:bg-slate-900">
                    <div className="flex items-center gap-3">
                      <PositionBadge position={p.position} />
                      <Link to={`/stats`} className="font-semibold text-white hover:text-emerald-400" data-testid={`sb-link-${p.id}`}>{p.name}</Link>
                      <span className="text-xs font-mono-tab text-slate-500">{p.team}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <TagBadge tag={p.tag} />
                      <span className="font-mono-tab text-sm text-emerald-300 font-bold">{p.current_fpts_per_game?.toFixed?.(1) ?? "—"}/g</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}
