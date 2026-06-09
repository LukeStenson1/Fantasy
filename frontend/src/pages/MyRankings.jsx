import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import { useAuth } from "../contexts/AuthContext";
import { useSport } from "../contexts/SportContext";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Plus, Trash2, X, Brain, RefreshCw, Database, Shield } from "lucide-react";
import { PositionBadge } from "../components/Badges";
import { toast } from "sonner";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";

function relativeTime(iso) {
  if (!iso) return "never";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function MyRankings() {
  const { user, loading } = useAuth();
  const { config } = useSport();
  const [rankings, setRankings] = useState([]);
  const [lineups, setLineups] = useState([]);
  const [predStats, setPredStats] = useState(null);
  const [dataStatus, setDataStatus] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [scoring, setScoring] = useState("half_ppr");
  const [search, setSearch] = useState("");
  const [results, setResults] = useState([]);
  const [picked, setPicked] = useState([]);

  useEffect(() => {
    if (user && user !== false) {
      api.get("/rankings/me").then((r) => setRankings(r.data));
      api.get("/lineups/me").then((r) => setLineups(r.data));
      api.get("/predictions/stats").then((r) => setPredStats(r.data));
      if (user.role === "admin") api.get("/admin/data-status").then((r) => setDataStatus(r.data));
    }
  }, [user]);

  useEffect(() => {
    if (!creating) return;
    const t = setTimeout(() => {
      api.get("/players", { params: { search: search || undefined, scoring, limit: 30 } })
        .then((r) => setResults(r.data.items || []));
    }, 200);
    return () => clearTimeout(t);
  }, [search, scoring, creating]);

  if (loading) return <div className="min-h-screen bg-[#0a0e16]"><Navbar /><div className="p-8 text-slate-500">Loading…</div></div>;
  if (user === false) return <Navigate to="/login" replace />;

  const addPick = (p) => { if (!picked.find((x) => x.id === p.id)) setPicked([...picked, p]); };
  const removePick = (id) => setPicked(picked.filter((x) => x.id !== id));

  const save = async () => {
    if (!title.trim() || picked.length === 0) { toast.error("Add a title and at least one player"); return; }
    try {
      const { data } = await api.post("/rankings", { title, scoring, player_ids: picked.map((p) => p.id) });
      setRankings([data, ...rankings]);
      setTitle(""); setPicked([]); setCreating(false);
      toast.success("Ranking saved");
    } catch { toast.error("Failed to save"); }
  };

  const removeRanking = async (id) => {
    await api.delete(`/rankings/${id}`);
    setRankings(rankings.filter((r) => r.id !== id));
    toast.success("Deleted");
  };

  const removeLineup = async (id) => {
    await api.delete(`/lineups/${id}`);
    setLineups(lineups.filter((l) => l.id !== id));
    toast.success("Deleted");
  };

  const forceRefresh = async () => {
    setRefreshing(true);
    toast.info("Refresh started — this takes 2-3 minutes for all sports...");
    try {
      const response = await api.post("/admin/refresh-data", null, {
        params: { force: true },
        timeout: 300000,
      });
      const data = response.data;
      if (data.status === "ok") {
        toast.success(`Data refreshed — ${data.players} players updated`);
      } else if (data.status === "skipped") {
        toast.info(`Skipped — data is fresh (${data.players} players)`);
      } else {
        toast.error(`Refresh returned: ${JSON.stringify(data)}`);
      }
      api.get("/admin/data-status").then((r) => setDataStatus(r.data));
    } catch (e) {
      if (e.code === "ECONNABORTED" || e.message?.includes("timeout")) {
        toast.success("Refresh is running in the background — check back in a few minutes!");
      } else {
        toast.error(`Refresh failed: ${e.message}`);
      }
    } finally {
      setRefreshing(false);
    }
  };

  const refreshInjuries = async () => {
    setRefreshing(true);
    try {
      const { data } = await api.post("/admin/refresh-injuries");
      toast.success(`Injuries refreshed — ${data.matched || 0} players updated`);
      api.get("/admin/data-status").then((r) => setDataStatus(r.data));
    } catch {
      toast.error("Injury refresh failed");
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />

      {/* HEADER */}
      <div className="border-b border-slate-800 bg-slate-950/60" style={{ borderTopColor: config.hex, borderTopWidth: 2 }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div
            className="text-[10px] font-bold tracking-[0.25em] uppercase mb-2"
            style={{ color: config.hex }}
          >
            ◆ The Lab · My Notebook
          </div>
          <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight text-white">My Lab</h1>
          <p className="text-slate-400 mt-2">Saved rankings, lineups, and the Lab's self-learning accuracy.</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">

        {/* ADMIN PANEL */}
        {user?.role === "admin" && (
          <div className="bg-slate-950/60 border border-amber-500/20 rounded-md p-5">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-5 h-5 text-amber-400" />
              <h2 className="font-display font-bold text-lg text-white">Admin Panel</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
              <div className="bg-slate-900 border border-slate-800 rounded-md p-3">
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Players</div>
                <div className="font-mono-tab text-xl font-bold text-white">{dataStatus?.player_count ?? "—"}</div>
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-md p-3">
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Seasons</div>
                <div className="font-mono-tab text-sm font-bold text-white">
                  {dataStatus?.last_refresh?.seasons?.join(", ") ?? "—"}
                </div>
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-md p-3">
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Last Refresh</div>
                <div className="font-mono-tab text-sm font-bold text-white">
                  {relativeTime(dataStatus?.last_refresh?.value)}
                </div>
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-md p-3">
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Injured</div>
                <div className="font-mono-tab text-xl font-bold text-white">{dataStatus?.injured_count ?? "—"}</div>
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button
                onClick={forceRefresh}
                disabled={refreshing}
                className="font-bold text-slate-950"
                style={{ background: config.hex }}
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
                {refreshing ? "Refreshing…" : "Force Refresh Player Data"}
              </Button>
              <Button
                onClick={refreshInjuries}
                disabled={refreshing}
                variant="outline"
                className="border-slate-700 text-slate-300 hover:bg-slate-800"
              >
                <Database className="w-4 h-4 mr-2" />
                Refresh Injuries
              </Button>
            </div>
            <p className="text-xs text-slate-500 mt-3">
              Force refresh pulls latest data including new seasons, trades, and roster changes for all sports.
            </p>
          </div>
        )}

        {/* SELF-LEARNING STATS */}
        <div className="bg-slate-950/60 border rounded-md p-5"
          style={{ borderColor: `${config.hex}33` }}>
          <div className="flex items-center gap-2 mb-3">
            <Brain className="w-5 h-5" style={{ color: config.hex }} />
            <h2 className="font-display font-bold text-lg text-white">Self-Learning Accuracy</h2>
            <span className="ml-auto text-xs text-slate-500 font-mono-tab">
              {predStats ? `${predStats.settled}/${predStats.total} predictions settled` : "loading…"}
            </span>
          </div>
          {(!predStats || Object.keys(predStats?.by_position || {}).length === 0) && (
            <p className="text-sm text-slate-400">
              The Lab logs every Lineup AI suggestion as a prediction. Once data is available, accuracy will appear here.
            </p>
          )}
          {predStats && Object.keys(predStats?.by_position || {}).length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {Object.entries(predStats?.by_position || {}).map(([pos, s]) => {
                const mae = typeof s?.mae === "number" ? s.mae.toFixed(1) : "—";
                const bias = typeof s?.bias === "number"
                  ? `${s.bias > 0 ? "+" : ""}${s.bias.toFixed(1)}`
                  : "—";
                const n = s?.n ?? 0;
                return (
                  <div key={pos} className="border border-slate-800 rounded-md p-3 bg-slate-950/40">
                    <div className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">{pos}</div>
                    <div className="font-mono-tab text-white">
                      <span className="font-bold" style={{ color: config.hexLight }}>{mae}</span> MAE
                    </div>
                    <div className="text-xs text-slate-500 font-mono-tab">bias {bias} · n={n}</div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* RANKINGS & LINEUPS */}
        <Tabs defaultValue="rankings">
          <TabsList>
            <TabsTrigger value="rankings">Rankings ({rankings.length})</TabsTrigger>
            <TabsTrigger value="lineups">Saved Lineups ({lineups.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="rankings">
            <div className="mt-4 space-y-3">
              <Button
                onClick={() => setCreating(!creating)}
                className="font-bold text-slate-950"
                style={{ background: config.hex }}
              >
                <Plus className="w-4 h-4 mr-1" /> New Ranking
              </Button>

              {creating && (
                <div className="bg-slate-950/60 border border-slate-800 rounded-md p-5 space-y-4">
                  <Input value={title} onChange={(e) => setTitle(e.target.value)}
                    placeholder="Ranking title…"
                    className="bg-slate-900 border-slate-700 text-white" />
                  <div className="relative">
                    <Input value={search} onChange={(e) => setSearch(e.target.value)}
                      placeholder="Search players…"
                      className="bg-slate-900 border-slate-700 text-white" />
                    {results.length > 0 && (
                      <div className="absolute top-full mt-1 left-0 right-0 bg-slate-900 border border-slate-700 rounded-md max-h-60 overflow-auto z-20">
                        {results.map((p) => (
                          <button key={p.id} onClick={() => addPick(p)}
                            className="w-full px-3 py-2 flex items-center gap-2 hover:bg-slate-800 text-left border-b border-slate-800 last:border-0">
                            <PositionBadge position={p.position} />
                            <span className="text-white font-semibold">{p.name}</span>
                            <span className="text-xs text-slate-500">{p.team}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  {picked.length > 0 && (
                    <ul className="space-y-1">
                      {picked.map((p, i) => (
                        <li key={p.id} className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded px-3 py-2">
                          <span className="text-slate-500 text-xs w-5">{i + 1}</span>
                          <PositionBadge position={p.position} />
                          <span className="text-white font-semibold flex-1">{p.name}</span>
                          <button onClick={() => removePick(p.id)}>
                            <X className="w-4 h-4 text-slate-500 hover:text-red-400" />
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                  <div className="flex gap-2">
                    <Button
                      onClick={save}
                      className="font-bold text-slate-950"
                      style={{ background: config.hex }}
                    >
                      Save Ranking
                    </Button>
                    <Button variant="outline" onClick={() => setCreating(false)}
                      className="border-slate-700 text-slate-300">
                      Cancel
                    </Button>
                  </div>
                </div>
              )}

              {rankings.length === 0 && !creating && (
                <p className="text-slate-500 text-sm">No rankings saved yet.</p>
              )}
              {rankings.map((r) => (
                <div key={r.id} className="bg-slate-950/60 border border-slate-800 rounded-md p-4 flex items-center justify-between">
                  <div>
                    <div className="font-bold text-white">{r.title}</div>
                    <div className="text-xs text-slate-500">
                      {r.player_ids?.length} players · {r.scoring} · {relativeTime(r.created_at)}
                    </div>
                  </div>
                  <button onClick={() => removeRanking(r.id)}>
                    <Trash2 className="w-4 h-4 text-slate-500 hover:text-red-400" />
                  </button>
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="lineups">
            <div className="mt-4 space-y-3">
              {lineups.length === 0 && <p className="text-slate-500 text-sm">No lineups saved yet.</p>}
              {lineups.map((l) => (
                <div key={l.id} className="bg-slate-950/60 border border-slate-800 rounded-md p-4 flex items-center justify-between">
                  <div>
                    <div className="font-bold text-white">{l.title}</div>
                    <div className="text-xs text-slate-500">{l.scoring} · {relativeTime(l.created_at)}</div>
                  </div>
                  <button onClick={() => removeLineup(l.id)}>
                    <Trash2 className="w-4 h-4 text-slate-500 hover:text-red-400" />
                  </button>
                </div>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
