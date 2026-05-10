import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { api } from "../lib/api";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { PositionBadge, TagBadge, InjuryBadge, MatchupBadge } from "../components/Badges";
import { Plus, X, ArrowRightLeft, Sparkles, Activity, Scale } from "lucide-react";
import { toast } from "sonner";
import AdSlot from "../components/AdSlot";

const SCORINGS = [
  { v: "half_ppr", l: "Half PPR" },
  { v: "ppr", l: "PPR" },
  { v: "standard", l: "Standard" },
];

const VERDICT_META = {
  side_a_strongly_wins: { label: "Side A wins decisively", color: "text-emerald-300", bar: "bg-emerald-400", side: "a" },
  side_a_wins: { label: "Side A wins", color: "text-emerald-300", bar: "bg-emerald-500", side: "a" },
  fair: { label: "Fair trade", color: "text-slate-300", bar: "bg-slate-500", side: null },
  side_b_wins: { label: "Side B wins", color: "text-emerald-300", bar: "bg-emerald-500", side: "b" },
  side_b_strongly_wins: { label: "Side B wins decisively", color: "text-emerald-300", bar: "bg-emerald-400", side: "b" },
};

export default function Trades() {
  const [scoring, setScoring] = useState("half_ppr");
  const [sideA, setSideA] = useState([]);
  const [sideB, setSideB] = useState([]);
  const [result, setResult] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);

  const reset = () => { setSideA([]); setSideB([]); setResult(null); };

  const analyze = async () => {
    if (sideA.length === 0 || sideB.length === 0) {
      toast.error("Add at least 1 player to each side");
      return;
    }
    setAnalyzing(true);
    setResult(null);
    try {
      const { data } = await api.post("/trade/analyze", {
        scoring,
        side_a_label: "Side A (you give)",
        side_b_label: "Side B (you get)",
        side_a_player_ids: sideA.map((p) => p.id),
        side_b_player_ids: sideB.map((p) => p.id),
      });
      setResult(data);
    } catch {
      toast.error("Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />

      <div className="border-b border-slate-800 bg-slate-950/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex items-end justify-between flex-wrap gap-4">
          <div>
            <div className="text-[10px] font-bold tracking-[0.25em] uppercase text-emerald-400 mb-2">◆ The Lab · Trade Analyzer</div>
            <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight text-white" data-testid="trades-title">Analyze Any Trade</h1>
            <p className="text-slate-400 mt-2 max-w-2xl">Add the players on each side. The Lab scores both using <strong className="text-emerald-300">live injuries</strong>, <strong className="text-emerald-300">live matchups</strong>, and AI commentary — so the verdict reflects whatever happened today, not last week.</p>
          </div>
          <div>
            <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">Scoring</label>
            <Select value={scoring} onValueChange={setScoring}>
              <SelectTrigger className="w-[160px] bg-slate-900 border-slate-700 text-white" data-testid="trades-scoring"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-700 text-white">
                {SCORINGS.map((s) => <SelectItem key={s.v} value={s.v}>{s.l}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto_1fr] items-start gap-4">
          <SideBuilder testid="side-a" title="Side A — You give" side={sideA} setSide={setSideA} otherSide={sideB} scoring={scoring} accent="red" />
          <div className="hidden lg:flex items-center justify-center pt-20">
            <ArrowRightLeft className="w-8 h-8 text-emerald-400" />
          </div>
          <SideBuilder testid="side-b" title="Side B — You get" side={sideB} setSide={setSideB} otherSide={sideA} scoring={scoring} accent="emerald" />
        </div>

        <div className="flex flex-wrap items-center gap-3 justify-center">
          <Button onClick={analyze} disabled={analyzing || sideA.length === 0 || sideB.length === 0}
            className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold px-6" data-testid="analyze-trade-btn">
            <Scale className="w-4 h-4 mr-1" />
            {analyzing ? "Analyzing…" : "Analyze Trade"}
          </Button>
          {(sideA.length > 0 || sideB.length > 0) && (
            <button onClick={reset} className="text-xs text-slate-500 hover:text-white uppercase tracking-wider" data-testid="reset-trade-btn">
              Reset
            </button>
          )}
        </div>

        <AdSlot slot="trades-mid" />

        {result && <TradeResult result={result} />}
      </div>
    </div>
  );
}

function SideBuilder({ title, side, setSide, otherSide, scoring, accent, testid }) {
  const [search, setSearch] = useState("");
  const [results, setResults] = useState([]);

  useEffect(() => {
    if (!search) { setResults([]); return; }
    const t = setTimeout(() => {
      api.get("/players", { params: { search, scoring, limit: 25 } }).then((r) => setResults(r.data.items || []));
    }, 200);
    return () => clearTimeout(t);
  }, [search, scoring]);

  const add = (p) => {
    if (side.find((x) => x.id === p.id) || otherSide.find((x) => x.id === p.id)) {
      toast.error("Player already on a side");
      return;
    }
    setSide([...side, p]);
    setSearch(""); setResults([]);
  };
  const remove = (id) => setSide(side.filter((x) => x.id !== id));

  const accentBar = accent === "red" ? "bg-red-500/20 border-red-500/40" : "bg-emerald-500/15 border-emerald-500/40";
  const accentText = accent === "red" ? "text-red-300" : "text-emerald-300";

  return (
    <div className={`bg-slate-950/60 border ${accentBar} rounded-md p-5`} data-testid={testid}>
      <div className={`text-[10px] font-bold tracking-[0.2em] uppercase ${accentText} mb-3`}>{title}</div>
      <div className="relative mb-3">
        <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search any player…"
          className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-500" data-testid={`${testid}-search`} />
        {results.length > 0 && (
          <div className="absolute top-full mt-1 left-0 right-0 bg-slate-900 border border-slate-700 rounded-md max-h-60 overflow-auto z-20 shadow-xl">
            {results.map((p) => (
              <button key={p.id} onClick={() => add(p)}
                className="w-full px-3 py-2 flex items-center justify-between hover:bg-slate-800 text-left border-b border-slate-800 last:border-b-0"
                data-testid={`${testid}-result-${p.id}`}>
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

      {side.length === 0 ? (
        <div className="border border-dashed border-slate-700 rounded-md p-6 text-center text-sm text-slate-500" data-testid={`${testid}-empty`}>
          Add at least one player.
        </div>
      ) : (
        <ul className="space-y-2" data-testid={`${testid}-list`}>
          {side.map((p) => (
            <li key={p.id} className="flex items-center justify-between bg-slate-900 border border-slate-700 rounded-md px-3 py-2">
              <div className="flex items-center gap-2 min-w-0">
                <PositionBadge position={p.position} />
                <span className="font-semibold text-white truncate">{p.name}</span>
                <span className="text-xs text-slate-500 font-mono-tab">{p.team}</span>
              </div>
              <button onClick={() => remove(p.id)} className="text-slate-500 hover:text-red-400 shrink-0" data-testid={`${testid}-remove-${p.id}`}>
                <X className="w-4 h-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TradeResult({ result }) {
  const meta = VERDICT_META[result.verdict] || VERDICT_META.fair;
  const diff = result.diff;
  const diffStr = diff > 0 ? `+${diff.toFixed(1)} for Side B` : diff < 0 ? `${Math.abs(diff).toFixed(1)} for Side A` : "Even";

  return (
    <div className="space-y-4" data-testid="trade-result">
      {/* Verdict header */}
      <div className="bg-slate-950/60 border border-slate-800 rounded-md p-5">
        <div className="flex items-center gap-3 flex-wrap">
          <div className={`w-1 h-10 ${meta.bar}`} />
          <div>
            <div className="text-[10px] font-bold tracking-[0.25em] uppercase text-slate-500">Verdict</div>
            <div className={`font-display text-2xl font-black ${meta.color}`} data-testid="trade-verdict-label">{meta.label}</div>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <div className="text-[10px] font-bold tracking-[0.2em] uppercase text-slate-500">Lab Score Δ</div>
            <div className="font-mono-tab text-2xl font-bold text-white" data-testid="trade-diff">{diffStr}</div>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2 text-xs text-slate-500 flex-wrap">
          <Activity className="w-3.5 h-3.5 text-emerald-400" />
          <span>Live injuries</span>
          <span className="text-slate-700">·</span>
          <span>Live matchups (DvP)</span>
          <span className="text-slate-700">·</span>
          <span>Self-learned bias correction</span>
        </div>
      </div>

      {/* Side breakdowns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SideResult label={result.side_a_label} side={result.side_a} testid="trade-side-a" />
        <SideResult label={result.side_b_label} side={result.side_b} testid="trade-side-b" />
      </div>

      {/* AI commentary */}
      <div className="bg-slate-950/60 border border-emerald-500/20 rounded-md" data-testid="trade-commentary">
        <div className="px-5 py-3 border-b border-slate-800 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-emerald-400" />
          <h3 className="font-display font-bold text-white">AI Verdict & Reasoning</h3>
        </div>
        <pre className="p-5 whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-200">{result.commentary}</pre>
      </div>
    </div>
  );
}

function SideResult({ label, side, testid }) {
  return (
    <div className="bg-slate-950/60 border border-slate-800 rounded-md overflow-hidden" data-testid={testid}>
      <div className="px-5 py-3 border-b border-slate-800 flex items-center gap-2">
        <h3 className="font-display font-bold text-white">{label}</h3>
        <span className="ml-auto text-xs text-slate-500 font-mono-tab">Total Lab Score</span>
        <span className="font-mono-tab text-xl font-bold text-emerald-300" data-testid={`${testid}-total`}>{side.total_lab_score?.toFixed?.(1)}</span>
      </div>
      <ul className="divide-y divide-slate-800">
        {side.players.map((p, i) => (
          <li key={p.id} className="px-5 py-3" data-testid={`${testid}-player-${i}`}>
            <div className="flex items-center gap-2 flex-wrap">
              <PositionBadge position={p.position} />
              <span className="font-semibold text-white">{p.name}</span>
              <span className="text-xs text-slate-500 font-mono-tab">{p.team}{p.next_opponent ? ` · vs ${p.next_opponent}` : ""}</span>
              <TagBadge tag={p.tag} />
              <InjuryBadge status={p.injury_status} />
              <MatchupBadge
                rank={p.factors?.def_rank}
                opp={p.factors?.opponent}
                position={p.position}
                fptsAllowed={p.factors?.def_fpts_allowed}
                source={p.factors?.def_rank_source}
                compact
              />
              <span className="ml-auto font-mono-tab text-base font-bold text-emerald-300">{p.lineup_score?.toFixed?.(1)}</span>
            </div>
            <div className="text-xs text-slate-400 mt-1">
              {p.current_fpts_per_game ? `${p.current_fpts_per_game.toFixed(1)} FPts/G last yr` : "Rookie / no prior season"}
              {p.factors?.def_fpts_allowed ? ` · ${p.factors.def_fpts_allowed.toFixed(1)} allowed/G to ${p.position}s` : ""}
              {p.injury_status ? ` · INJURY: ${p.injury_status}` : ""}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
