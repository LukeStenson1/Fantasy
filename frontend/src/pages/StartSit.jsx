import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { api } from "../lib/api";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { PositionBadge, TagBadge } from "../components/Badges";
import { Plus, X, Trophy, Sparkles } from "lucide-react";

const SCORINGS = [
  { v: "half_ppr", l: "Half PPR" },
  { v: "ppr", l: "PPR" },
  { v: "standard", l: "Standard" },
];

const SLOTS = [
  { v: "ALL", l: "All Positions" },
  { v: "QB", l: "QB" }, { v: "RB", l: "RB" }, { v: "WR", l: "WR" }, { v: "TE", l: "TE" }, { v: "FLEX", l: "FLEX" },
];

export default function StartSit() {
  const [search, setSearch] = useState("");
  const [results, setResults] = useState([]);
  const [picked, setPicked] = useState([]);
  const [scoring, setScoring] = useState("half_ppr");
  const [slot, setSlot] = useState("ALL");
  const [ranked, setRanked] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!search) { setResults([]); return; }
    const t = setTimeout(() => {
      api.get("/players", { params: { search, scoring, limit: 20 } })
        .then((r) => setResults(r.data.items || []));
    }, 200);
    return () => clearTimeout(t);
  }, [search, scoring]);

  const addPlayer = (p) => {
    if (picked.find((x) => x.id === p.id)) return;
    setPicked([...picked, p]);
    setSearch("");
    setResults([]);
  };
  const remove = (id) => setPicked(picked.filter((x) => x.id !== id));

  const decide = async () => {
    if (picked.length < 2) return;
    setLoading(true);
    try {
      const { data } = await api.post("/start-sit", {
        player_ids: picked.map((p) => p.id),
        scoring,
        slot: slot === "ALL" ? null : slot,
      });
      setRanked(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />
      <div className="border-b border-slate-800 bg-slate-950/60">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-[10px] font-bold tracking-[0.25em] uppercase text-emerald-400 mb-2">◆ The Lab · Start / Sit</div>
          <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight text-white" data-testid="ss-title">Decide Who to Start</h1>
          <p className="text-slate-400 mt-2 max-w-2xl">Add the players on your roster — the Lab ranks them by matchup-adjusted Lab Score and tells you exactly who to play.</p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Picker */}
        <div className="bg-slate-950/60 border border-slate-800 rounded-md p-5" data-testid="ss-picker">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
            <div className="md:col-span-2">
              <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">Add player</label>
              <div className="relative">
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search player name…"
                  className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
                  data-testid="ss-search-input"
                />
                {results.length > 0 && (
                  <div className="absolute top-full mt-1 left-0 right-0 bg-slate-900 border border-slate-700 rounded-md max-h-72 overflow-auto z-20 shadow-xl">
                    {results.map((p) => (
                      <button key={p.id} onClick={() => addPlayer(p)}
                        className="w-full px-3 py-2 flex items-center justify-between hover:bg-slate-800 text-left border-b border-slate-800 last:border-b-0"
                        data-testid={`ss-result-${p.id}`}>
                        <div className="flex items-center gap-2">
                          <PositionBadge position={p.position} />
                          <span className="font-semibold text-white">{p.name}</span>
                          <span className="text-xs text-slate-500 font-mono-tab">{p.team}</span>
                        </div>
                        <Plus className="w-4 h-4 text-slate-500" />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">Slot</label>
                <Select value={slot} onValueChange={setSlot}>
                  <SelectTrigger className="bg-slate-900 border-slate-700 text-white" data-testid="ss-slot"><SelectValue /></SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700 text-white">
                    {SLOTS.map((s) => <SelectItem key={s.v} value={s.v}>{s.l}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">Scoring</label>
                <Select value={scoring} onValueChange={setScoring}>
                  <SelectTrigger className="bg-slate-900 border-slate-700 text-white" data-testid="ss-scoring"><SelectValue /></SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700 text-white">
                    {SCORINGS.map((s) => <SelectItem key={s.v} value={s.v}>{s.l}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Picked list */}
          <div className="mb-4">
            <div className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 mb-2">Your roster ({picked.length})</div>
            {picked.length === 0 ? (
              <div className="border border-dashed border-slate-700 rounded-md p-6 text-center text-sm text-slate-500" data-testid="ss-empty">
                Add at least 2 players to compare.
              </div>
            ) : (
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2" data-testid="ss-picked-list">
                {picked.map((p) => (
                  <li key={p.id} className="flex items-center justify-between bg-slate-900 border border-slate-700 rounded-md px-3 py-2">
                    <div className="flex items-center gap-2">
                      <PositionBadge position={p.position} />
                      <span className="font-semibold text-white">{p.name}</span>
                      <span className="text-xs text-slate-500 font-mono-tab">{p.team}</span>
                    </div>
                    <button onClick={() => remove(p.id)} className="text-slate-500 hover:text-red-400" data-testid={`ss-remove-${p.id}`}>
                      <X className="w-4 h-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <Button onClick={decide} disabled={picked.length < 2 || loading}
            className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold w-full md:w-auto" data-testid="ss-decide-btn">
            {loading ? "Analyzing…" : "Tell me who to start"}
          </Button>
        </div>

        {/* Result */}
        {ranked && ranked.recommendation && (
          <div className="space-y-4" data-testid="ss-result">
            <div className="bg-emerald-500/10 border border-emerald-500/40 rounded-md p-6" data-testid="ss-recommendation">
              <div className="flex items-center gap-2 mb-2">
                <Trophy className="w-5 h-5 text-emerald-400" />
                <div className="text-[10px] font-bold tracking-[0.2em] uppercase text-emerald-400">Start This Player</div>
              </div>
              <div className="flex items-center gap-3">
                <PositionBadge position={ranked.recommendation.position} />
                <div className="font-display text-3xl font-black text-white">{ranked.recommendation.name}</div>
                <span className="text-sm text-slate-400 font-mono-tab">{ranked.recommendation.team}</span>
                <TagBadge tag={ranked.recommendation.tag} />
              </div>
              <div className="text-sm text-slate-300 mt-2">{ranked.recommendation.reasoning}</div>
              <div className="mt-3 flex items-center gap-2">
                <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500">Lab Score</span>
                <span className="font-mono-tab text-3xl font-black text-emerald-300">{ranked.recommendation.lineup_score.toFixed(1)}</span>
              </div>
            </div>

            <div className="bg-slate-950/60 border border-slate-800 rounded-md overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-800">
                <h3 className="font-display font-bold text-lg text-white">Full Ranking</h3>
              </div>
              <ul className="divide-y divide-slate-800" data-testid="ss-full-ranking">
                {ranked.ranked.map((p, i) => (
                  <li key={p.id} className="px-5 py-3 flex items-start justify-between gap-3" data-testid={`ss-rank-${i}`}>
                    <div className="flex items-start gap-3 min-w-0">
                      <span className="text-slate-600 font-mono-tab text-xs w-5 mt-1">{i + 1}</span>
                      <PositionBadge position={p.position} />
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-white">{p.name}</span>
                          <span className="text-xs text-slate-500 font-mono-tab">{p.team}</span>
                          <TagBadge tag={p.tag} />
                        </div>
                        <div className="text-xs text-slate-400 mt-0.5">{p.reasoning}</div>
                      </div>
                    </div>
                    <span className="font-mono-tab text-lg font-bold text-emerald-300 shrink-0">{p.lineup_score.toFixed(1)}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-slate-950/40 border border-emerald-500/20 rounded-md p-4 flex items-start gap-3">
              <Sparkles className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
              <div className="text-xs text-slate-400">
                <strong className="text-emerald-300">Lab Score</strong> = FPts/G + matchup adj (opposing D rank) + availability + trend boost. Higher = better start.
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
