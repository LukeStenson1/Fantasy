import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { api } from "../lib/api";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { PositionBadge, TagBadge, InjuryBadge } from "../components/Badges";
import { Plus, X, Trophy, Sparkles, Save, ExternalLink, Wand2 } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import AdSlot from "../components/AdSlot";

const SCORINGS = [
  { v: "half_ppr", l: "Half PPR" },
  { v: "ppr", l: "PPR" },
  { v: "standard", l: "Standard" },
];

const SLOT_ORDER = ["QB", "RB", "WR", "TE", "FLEX", "K", "DEF"];

export default function Lineup() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [scoring, setScoring] = useState("half_ppr");
  const [search, setSearch] = useState("");
  const [results, setResults] = useState([]);
  const [roster, setRoster] = useState([]);
  const [built, setBuilt] = useState(null);
  const [building, setBuilding] = useState(false);
  const [savedTitle, setSavedTitle] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!search) { setResults([]); return; }
    const t = setTimeout(() => {
      api.get("/players", { params: { search, scoring, limit: 25 } })
        .then((r) => setResults(r.data.items || []));
    }, 200);
    return () => clearTimeout(t);
  }, [search, scoring]);

  const addPlayer = (p) => {
    if (roster.find((x) => x.id === p.id)) return;
    setRoster([...roster, p]);
    setSearch("");
    setResults([]);
  };
  const removePlayer = (id) => setRoster(roster.filter((x) => x.id !== id));

  const build = async () => {
    if (roster.length < 2) {
      toast.error("Add at least 2 players to your roster");
      return;
    }
    setBuilding(true);
    try {
      const { data } = await api.post("/lineup/build", {
        player_ids: roster.map((p) => p.id), scoring,
      });
      setBuilt(data);
    } catch (e) {
      toast.error("Build failed");
    } finally {
      setBuilding(false);
    }
  };

  const handleSave = async () => {
    if (!user || user === false) {
      toast.error("Sign in to save lineups");
      navigate("/login");
      return;
    }
    if (!savedTitle.trim()) { toast.error("Add a title"); return; }
    if (!built) { toast.error("Build a lineup first"); return; }
    setSaving(true);
    const starters_payload = [];
    Object.entries(built.starters).forEach(([slot, arr]) => {
      arr.forEach((p) => starters_payload.push({ slot, player_id: p.id }));
    });
    const benchIds = (built.bench || []).map((p) => p.id);
    try {
      await api.post("/lineups", { title: savedTitle, scoring, starters: starters_payload, bench: benchIds });
      toast.success("Lineup saved!");
      setSavedTitle("");
    } catch { toast.error("Save failed"); }
    finally { setSaving(false); }
  };

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />

      <div className="border-b border-slate-800 bg-slate-950/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex items-end justify-between flex-wrap gap-4">
          <div>
            <div className="text-[10px] font-bold tracking-[0.25em] uppercase text-emerald-400 mb-2">◆ The Lab · Lineup AI + Start/Sit</div>
            <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight text-white" data-testid="lineup-title">Build Your Lineup</h1>
            <p className="text-slate-400 mt-2 max-w-2xl">Add every player on your roster. The Lab auto-picks 1 QB / 2 RB / 2 WR / 1 TE / 1 FLEX / 1 K / 1 DEF with Lab Score and per-player reasoning.</p>
          </div>
          <div>
            <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">Scoring</label>
            <Select value={scoring} onValueChange={setScoring}>
              <SelectTrigger className="w-[160px] bg-slate-900 border-slate-700 text-white" data-testid="lineup-scoring"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-700 text-white">
                {SCORINGS.map((s) => <SelectItem key={s.v} value={s.v}>{s.l}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Roster builder */}
        <div className="bg-slate-950/60 border border-slate-800 rounded-md p-5" data-testid="roster-builder">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div>
              <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">Add player to roster</label>
              <div className="relative">
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search any player (incl. rookies, K, DEF)…"
                  className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
                  data-testid="roster-search-input"
                />
                {results.length > 0 && (
                  <div className="absolute top-full mt-1 left-0 right-0 bg-slate-900 border border-slate-700 rounded-md max-h-72 overflow-auto z-20 shadow-xl">
                    {results.map((p) => (
                      <button key={p.id} onClick={() => addPlayer(p)}
                        className="w-full px-3 py-2 flex items-center justify-between hover:bg-slate-800 text-left border-b border-slate-800 last:border-b-0"
                        data-testid={`roster-result-${p.id}`}>
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
              <p className="text-xs text-slate-500 mt-2">Tip: search "D/ST" or a team name (e.g. "Bills") for defenses.</p>
            </div>
            <div>
              <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">Your roster ({roster.length})</label>
              {roster.length === 0 ? (
                <div className="border border-dashed border-slate-700 rounded-md p-6 text-center text-sm text-slate-500" data-testid="roster-empty">
                  Add at least 2 players to start.
                </div>
              ) : (
                <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-72 overflow-auto" data-testid="roster-list">
                  {roster.map((p) => (
                    <li key={p.id} className="flex items-center justify-between bg-slate-900 border border-slate-700 rounded-md px-3 py-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <PositionBadge position={p.position} />
                        <span className="font-semibold text-white truncate">{p.name}</span>
                        <span className="text-xs text-slate-500 font-mono-tab">{p.team}</span>
                      </div>
                      <button onClick={() => removePlayer(p.id)} className="text-slate-500 hover:text-red-400 shrink-0" data-testid={`roster-remove-${p.id}`}>
                        <X className="w-4 h-4" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <Button onClick={build} disabled={roster.length < 2 || building} className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold" data-testid="build-lineup-btn">
              <Wand2 className="w-4 h-4 mr-1" />
              {building ? "Building…" : "Auto-Pick Starters"}
            </Button>
            {roster.length > 0 && (
              <button onClick={() => { setRoster([]); setBuilt(null); }} className="text-xs text-slate-500 hover:text-white uppercase tracking-wider" data-testid="clear-roster-btn">
                Clear roster
              </button>
            )}
          </div>
        </div>

        <AdSlot slot="lineup-mid" />

        {/* Built lineup */}
        {built && (
          <div className="space-y-4" data-testid="built-result">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {SLOT_ORDER.flatMap((slot) =>
                (built.starters[slot] || []).map((p, i) => (
                  <SlotCard key={`${slot}-${i}`} slotLabel={slot === "RB" || slot === "WR" ? `${slot}${i + 1}` : slot} player={p} />
                ))
              )}
            </div>

            {built.bench?.length > 0 && (
              <div className="bg-slate-950/60 border border-slate-800 rounded-md overflow-hidden" data-testid="bench-list">
                <div className="px-5 py-3 border-b border-slate-800 flex items-center gap-2">
                  <h3 className="font-display font-bold text-lg text-white">Bench</h3>
                  <span className="ml-auto text-xs text-slate-500 font-mono-tab">{built.bench.length} players · ranked by Lab Score</span>
                </div>
                <ul className="divide-y divide-slate-800">
                  {built.bench.map((p, i) => (
                    <li key={p.id} className="px-5 py-3 flex items-center justify-between gap-3 hover:bg-slate-900" data-testid={`bench-${i}`}>
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="text-slate-600 font-mono-tab text-xs w-5">{i + 1}</span>
                        <PositionBadge position={p.position} />
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-white">{p.name}</span>
                            <span className="text-xs text-slate-500 font-mono-tab">{p.team}</span>
                            <TagBadge tag={p.tag} />
                          </div>
                          <div className="text-xs text-slate-400 truncate">{p.reasoning}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        {p.news_search_url && (
                          <a href={p.news_search_url} target="_blank" rel="noopener noreferrer"
                            className="text-emerald-400 hover:text-emerald-300" data-testid={`bench-news-${i}`}>
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        )}
                        <span className="font-mono-tab text-base font-bold text-emerald-300">{p.lineup_score?.toFixed?.(1)}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Save bar */}
            <div className="bg-slate-950/40 border border-slate-800 rounded-md p-4 flex flex-wrap items-center gap-3" data-testid="lineup-save-bar">
              <div className="flex items-center gap-2 text-sm text-slate-300">
                <Save className="w-4 h-4 text-emerald-400" />
                {user && user !== false ? "Save this lineup so the Lab can score predictions and learn over time." : "Sign in to save lineups."}
              </div>
              <Input value={savedTitle} onChange={(e) => setSavedTitle(e.target.value)} placeholder="Lineup title (e.g. Week 1)"
                className="md:max-w-xs bg-slate-900 border-slate-700 text-white" data-testid="save-lineup-title" />
              <Button onClick={handleSave} disabled={saving} className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold" data-testid="save-lineup-btn">
                {saving ? "Saving…" : (user && user !== false ? "Save Lineup" : "Login to Save")}
              </Button>
            </div>

            <div className="bg-slate-950/40 border border-emerald-500/20 rounded-md p-4 flex items-start gap-3">
              <Sparkles className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
              <div className="text-xs text-slate-400">
                <strong className="text-emerald-300">Lab Score</strong> = FPts/G + matchup adj (live opposing D rank) + availability + trend boost + self-learned correction. Higher = better start.
                K and D/ST scored using opposing-team profile.
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function SlotCard({ slotLabel, player }) {
  const p = player;
  return (
    <div className="bg-slate-950/60 border border-slate-800 hover:border-emerald-500/50 rounded-md p-4 transition-colors" data-testid={`slot-${slotLabel}`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-emerald-400">{slotLabel}</span>
        <Trophy className="w-3.5 h-3.5 text-emerald-400/40" />
      </div>
      <div className="flex items-center gap-2 mb-1 flex-wrap">
        <PositionBadge position={p.position} />
        <TagBadge tag={p.tag} />
        <InjuryBadge status={p.factors?.injury_status} />
      </div>
      <div className="font-display font-bold text-lg text-white leading-tight">{p.name}</div>
      <div className="text-xs font-mono-tab text-slate-400">{p.team}</div>
      <div className="mt-3 pt-3 border-t border-slate-800">
        <div className="flex items-baseline justify-between">
          <div className="text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500">Lab Score</div>
          <div className="font-mono-tab text-2xl font-bold text-emerald-300">{p.lineup_score?.toFixed?.(1)}</div>
        </div>
        <div className="text-xs text-slate-400 mt-2 leading-snug">{p.reasoning}</div>
        {p.news_search_url && (
          <a href={p.news_search_url} target="_blank" rel="noopener noreferrer"
            className="mt-2 inline-flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300">
            Latest news <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
    </div>
  );
}
