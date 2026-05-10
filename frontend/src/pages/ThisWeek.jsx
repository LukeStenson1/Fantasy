import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { api } from "../lib/api";
import { PositionBadge, TagBadge } from "../components/Badges";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { ExternalLink, Flame, ThumbsDown } from "lucide-react";
import AdSlot from "../components/AdSlot";

const SCORINGS = [{ v: "half_ppr", l: "Half PPR" }, { v: "ppr", l: "PPR" }, { v: "standard", l: "Standard" }];

export default function ThisWeek() {
  const [scoring, setScoring] = useState("half_ppr");
  const [data, setData] = useState({ plays: [], fades: [] });

  useEffect(() => {
    api.get("/this-week", { params: { scoring } }).then((r) => setData(r.data));
  }, [scoring]);

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />
      <div className="border-b border-slate-800 bg-slate-950/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex items-end justify-between flex-wrap gap-4">
          <div>
            <div className="text-[10px] font-bold tracking-[0.25em] uppercase text-emerald-400 mb-2">◆ The Lab · This Week's Edge</div>
            <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight text-white" data-testid="tw-title">Top Plays & Fades</h1>
            <p className="text-slate-400 mt-2 max-w-2xl">The 10 best matchup plays and 5 must-fades for the upcoming week. Drop this in your league chat.</p>
          </div>
          <div>
            <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">Scoring</label>
            <Select value={scoring} onValueChange={setScoring}>
              <SelectTrigger className="w-[160px] bg-slate-900 border-slate-700 text-white" data-testid="tw-scoring"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-700 text-white">
                {SCORINGS.map((s) => <SelectItem key={s.v} value={s.v}>{s.l}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <AdSlot slot="this-week-top" />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 bg-slate-950/60 border border-slate-800 rounded-md overflow-hidden" data-testid="tw-plays">
            <div className="px-5 py-3 border-b border-slate-800 flex items-center gap-2">
              <Flame className="w-5 h-5 text-emerald-400" />
              <h2 className="font-display font-bold text-xl text-white">Top 10 Plays</h2>
              <span className="ml-auto text-xs text-slate-500 font-mono-tab uppercase tracking-wider">Best matchup × production</span>
            </div>
            <ul>
              {(data.plays || []).map((p, i) => (
                <li key={p.id} className="px-5 py-3 border-b border-slate-800 last:border-b-0 flex items-center justify-between gap-3 hover:bg-slate-900" data-testid={`tw-play-${i}`}>
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-slate-600 font-mono-tab text-xs w-5">{i + 1}</span>
                    <PositionBadge position={p.position} />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-white">{p.name}</span>
                        <span className="text-xs text-slate-500 font-mono-tab">{p.team}</span>
                        <TagBadge tag={p.tag} />
                      </div>
                      <div className="text-xs text-slate-400">vs {p.opponent || "TBD"} · {p.factors?.fppg?.toFixed?.(1) ?? "—"} FPts/G last yr</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    {p.news_search_url && (
                      <a href={p.news_search_url} target="_blank" rel="noopener noreferrer"
                         className="text-emerald-400 hover:text-emerald-300" data-testid={`tw-play-news-${i}`}>
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                    <span className="font-mono-tab text-lg font-bold text-emerald-300">{p.lineup_score?.toFixed?.(1)}</span>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-slate-950/60 border border-slate-800 rounded-md overflow-hidden" data-testid="tw-fades">
            <div className="px-5 py-3 border-b border-slate-800 flex items-center gap-2">
              <ThumbsDown className="w-5 h-5 text-red-400" />
              <h2 className="font-display font-bold text-xl text-white">Top 5 Fades</h2>
            </div>
            <ul>
              {(data.fades || []).map((p, i) => (
                <li key={p.id} className="px-5 py-3 border-b border-slate-800 last:border-b-0 flex items-center justify-between gap-2 hover:bg-slate-900" data-testid={`tw-fade-${i}`}>
                  <div className="flex items-center gap-2 min-w-0">
                    <PositionBadge position={p.position} />
                    <span className="font-semibold text-white truncate">{p.name}</span>
                    <span className="text-xs text-slate-500 font-mono-tab">{p.team}→{p.opponent}</span>
                  </div>
                  <span className="font-mono-tab text-base font-bold text-red-400 shrink-0">{p.matchup_score?.toFixed?.(1)}</span>
                </li>
              ))}
              {(data.fades || []).length === 0 && (
                <li className="px-5 py-6 text-sm text-slate-500 text-center">No fade-worthy elites this week.</li>
              )}
            </ul>
          </div>
        </div>

        <AdSlot slot="this-week-bottom" />
      </div>
    </div>
  );
}
