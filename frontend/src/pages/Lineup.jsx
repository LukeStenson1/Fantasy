import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { api } from "../lib/api";
import { PositionBadge, TagBadge } from "../components/Badges";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Sparkles, Trophy, Users, Save } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { useAuth } from "../contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import AdSlot from "../components/AdSlot";

const SCORINGS = [
  { v: "half_ppr", l: "Half PPR" },
  { v: "ppr", l: "PPR" },
  { v: "standard", l: "Standard" },
];

const SLOTS = [
  { key: "QB", label: "QB", count: 1 },
  { key: "RB", label: "RB1", count: 2, idx: 0 },
  { key: "RB", label: "RB2", count: 2, idx: 1 },
  { key: "WR", label: "WR1", count: 2, idx: 0 },
  { key: "WR", label: "WR2", count: 2, idx: 1 },
  { key: "TE", label: "TE", count: 1 },
  { key: "FLEX", label: "FLEX", count: 1 },
];

export default function Lineup() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [scoring, setScoring] = useState("half_ppr");
  const [data, setData] = useState(null);
  const [activeSlot, setActiveSlot] = useState(null);
  const [overrides, setOverrides] = useState({});
  const [saving, setSaving] = useState(false);
  const [savedTitle, setSavedTitle] = useState("");

  useEffect(() => {
    api.get("/lineup/suggest", { params: { scoring } }).then((r) => setData(r.data));
    setOverrides({});
  }, [scoring]);

  if (!data) return <div className="min-h-screen bg-[#0a0e16]"><Navbar /><div className="p-8 text-slate-500">Building lineup…</div></div>;

  const getStarter = (slot) => {
    if (overrides[slot.label]) return overrides[slot.label];
    const list = data.starters[slot.key] || [];
    return list[slot.idx ?? 0] || null;
  };

  const swapTo = (slot, player) => {
    setOverrides({ ...overrides, [slot.label]: player });
    setActiveSlot(null);
  };

  const handleSave = async () => {
    if (!user || user === false) {
      toast.error("Sign in to save lineups");
      navigate("/login");
      return;
    }
    if (!savedTitle.trim()) {
      toast.error("Add a title for this lineup");
      return;
    }
    setSaving(true);
    const starters_payload = SLOTS.map((s) => {
      const p = getStarter(s);
      return p ? { slot: s.label, player_id: p.id } : null;
    }).filter(Boolean);
    const benchIds = [];
    Object.values(data?.bench_alternatives || {}).forEach((arr) =>
      arr.slice(0, 3).forEach((p) => benchIds.push(p.id))
    );
    try {
      await api.post("/lineups", { title: savedTitle, scoring, starters: starters_payload, bench: benchIds });
      toast.success("Lineup saved!");
      setSavedTitle("");
    } catch (e) {
      toast.error("Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />
      <div className="border-b border-slate-800 bg-slate-950/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex items-end justify-between flex-wrap gap-4">
          <div>
            <div className="text-[10px] font-bold tracking-[0.25em] uppercase text-emerald-400 mb-2">◆ The Lab · Lineup AI</div>
            <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight text-white" data-testid="lineup-title">Suggested Lineup</h1>
            <p className="text-slate-400 mt-2 max-w-2xl">Auto-built starting lineup using composite Lab Score: production · matchup · availability · trend.</p>
          </div>
          <div>
            <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">Scoring</label>
            <Select value={scoring} onValueChange={setScoring}>
              <SelectTrigger className="w-[160px] bg-slate-900 border-slate-700 text-white" data-testid="lineup-scoring">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-700 text-white">
                {SCORINGS.map((s) => <SelectItem key={s.v} value={s.v}>{s.l}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Save row */}
        <div className="bg-slate-950/40 border border-slate-800 rounded-md p-4 flex flex-wrap items-center gap-3" data-testid="lineup-save-bar">
          <div className="flex items-center gap-2 text-sm text-slate-300">
            <Save className="w-4 h-4 text-emerald-400" />
            {user && user !== false
              ? "Save this lineup so the Lab can score predictions and learn over time."
              : "Sign in to save lineups so the Lab can track predictions over time."}
          </div>
          <Input
            value={savedTitle}
            onChange={(e) => setSavedTitle(e.target.value)}
            placeholder="Lineup title (e.g. Week 1 plan)"
            className="md:max-w-xs bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
            data-testid="save-lineup-title"
          />
          <Button onClick={handleSave} disabled={saving} className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold" data-testid="save-lineup-btn">
            {saving ? "Saving…" : (user && user !== false ? "Save Lineup" : "Login to Save")}
          </Button>
        </div>

        <AdSlot slot="lineup-mid" />
        {/* Starting lineup grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="starters-grid">
          {SLOTS.map((slot) => {
            const p = getStarter(slot);
            return (
              <div key={slot.label} className="bg-slate-950/60 border border-slate-800 rounded-md p-4 hover:border-emerald-500/50 transition-colors" data-testid={`slot-${slot.label}`}>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-emerald-400">{slot.label}</span>
                  <Trophy className="w-3.5 h-3.5 text-emerald-400/40" />
                </div>
                {p ? (
                  <>
                    <div className="flex items-center gap-2 mb-1">
                      <PositionBadge position={p.position} />
                      <TagBadge tag={p.tag} />
                    </div>
                    <div className="font-display font-bold text-lg text-white leading-tight">{p.name}</div>
                    <div className="text-xs font-mono-tab text-slate-400">{p.team}</div>
                    <div className="mt-3 pt-3 border-t border-slate-800">
                      <div className="flex items-baseline justify-between">
                        <div className="text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500">Lab Score</div>
                        <div className="font-mono-tab text-2xl font-bold text-emerald-300" data-testid={`slot-${slot.label}-score`}>{p.lineup_score?.toFixed?.(1)}</div>
                      </div>
                      <div className="text-xs text-slate-400 mt-2 leading-snug" data-testid={`slot-${slot.label}-reasoning`}>{p.reasoning}</div>
                    </div>
                    <button
                      onClick={() => setActiveSlot(slot)}
                      className="mt-3 w-full text-xs uppercase tracking-wider font-bold border border-slate-700 hover:border-emerald-500 hover:text-emerald-400 text-slate-400 py-2 transition-colors"
                      data-testid={`slot-${slot.label}-swap-btn`}
                    >
                      Swap Player
                    </button>
                  </>
                ) : (
                  <div className="text-sm text-slate-500">No suggestion</div>
                )}
              </div>
            );
          })}
        </div>

        {/* Swap modal/picker */}
        {activeSlot && (
          <SwapPicker
            slot={activeSlot}
            data={data}
            onSelect={(p) => swapTo(activeSlot, p)}
            onClose={() => setActiveSlot(null)}
          />
        )}

        {/* Bench alternatives */}
        <div className="bg-slate-950/60 border border-slate-800 rounded-md" data-testid="bench-section">
          <div className="px-5 py-4 border-b border-slate-800 flex items-center gap-2">
            <Users className="w-4 h-4 text-slate-400" />
            <h2 className="font-display font-bold text-xl text-white">Top Alternatives by Position</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-slate-800">
            {["QB", "RB", "WR", "TE"].map((pos) => (
              <div key={pos} className="p-4">
                <div className="text-[10px] font-bold tracking-[0.2em] uppercase text-emerald-400 mb-2">{pos}</div>
                <ul className="space-y-2">
                  {(data.bench_alternatives[pos] || []).slice(0, 6).map((p, i) => (
                    <li key={p.id} className="flex items-center justify-between text-sm" data-testid={`bench-${pos}-${i}`}>
                      <div className="flex items-center gap-2">
                        <span className="text-slate-500 font-mono-tab w-4">{i + 1}</span>
                        <span className="text-white font-medium">{p.name}</span>
                        <span className="text-xs text-slate-500 font-mono-tab">{p.team}</span>
                      </div>
                      <span className="font-mono-tab text-emerald-300 font-bold">{p.lineup_score?.toFixed?.(1)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-950/40 border border-emerald-500/20 rounded-md p-4 flex items-start gap-3" data-testid="lineup-disclaimer">
          <Sparkles className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
          <div className="text-xs text-slate-400">
            <strong className="text-emerald-300">How Lab Score works:</strong> base FPts/G from last season + matchup adjustment (opposing
            defense rank vs position) + availability factor (penalty for missed games) + trend tag boost. Higher = better start.
          </div>
        </div>
      </div>
    </div>
  );
}

function SwapPicker({ slot, data, onSelect, onClose }) {
  const positions = slot.key === "FLEX" ? ["RB", "WR", "TE"] : [slot.key];
  const all = [];
  positions.forEach((pos) => {
    (data.starters[pos] || []).forEach((p) => all.push(p));
    (data.bench_alternatives[pos] || []).forEach((p) => all.push(p));
  });
  const seen = new Set();
  const unique = all.filter((p) => (seen.has(p.id) ? false : seen.add(p.id)));
  unique.sort((a, b) => b.lineup_score - a.lineup_score);

  return (
    <div className="fixed inset-0 bg-black/70 z-40 flex items-center justify-center p-4" onClick={onClose} data-testid="swap-picker">
      <div className="bg-slate-950 border border-slate-700 rounded-md w-full max-w-2xl max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <div className="text-[10px] font-bold tracking-[0.2em] uppercase text-emerald-400">Swap {slot.label}</div>
            <h3 className="font-display text-xl font-bold text-white">Choose a player</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-2xl leading-none">×</button>
        </div>
        <ul className="overflow-auto divide-y divide-slate-800">
          {unique.map((p, i) => (
            <li key={p.id}>
              <button onClick={() => onSelect(p)} className="w-full px-5 py-3 flex items-center justify-between hover:bg-slate-900 text-left" data-testid={`swap-option-${p.id}`}>
                <div className="flex items-center gap-3">
                  <span className="text-slate-600 font-mono-tab text-xs w-5">{i + 1}</span>
                  <PositionBadge position={p.position} />
                  <div>
                    <div className="font-semibold text-white">{p.name}</div>
                    <div className="text-xs text-slate-400">{p.reasoning}</div>
                  </div>
                </div>
                <div className="font-mono-tab text-lg font-bold text-emerald-300">{p.lineup_score?.toFixed?.(1)}</div>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
