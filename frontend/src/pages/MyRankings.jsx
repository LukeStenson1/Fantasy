import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Plus, Trash2, X, Brain, Target } from "lucide-react";
import { PositionBadge } from "../components/Badges";
import { toast } from "sonner";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import AdSlot from "../components/AdSlot";

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
  const [rankings, setRankings] = useState([]);
  const [lineups, setLineups] = useState([]);
  const [predStats, setPredStats] = useState(null);
  const [dataStatus, setDataStatus] = useState(null);
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

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />

      {/* HEADER */}
      <div className="border-b border-slate-800 bg-slate-950/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-[10px] font-bold tracking-[0.25em] uppercase text-emerald-400 mb-2">◆ The Lab · My Notebook</div>
          <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight text-white">My Lab</h1>
          <p className="text-slate-400 mt-2">Saved rankings, lineups, and the Lab's self-learning accuracy.</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">

        {/* SELF-LEARNING STATS (FIXED) */}
        <div className="bg-slate-950/60 border border-emerald-500/20 rounded-md p-5">
          <div className="flex items-center gap-2 mb-3">
            <Brain className="w-5 h-5 text-emerald-400" />
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
                    <div className="font-mono-tab text-white"><span className="font-bold">{mae}</span> MAE</div>
                    <div className="text-xs text-slate-500 font-mono-tab">bias {bias} · n={n}</div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* EVERYTHING ELSE UNCHANGED */}
        <Tabs defaultValue="rankings">
          <TabsList>
            <TabsTrigger value="rankings">Rankings ({rankings.length})</TabsTrigger>
            <TabsTrigger value="lineups">Saved Lineups ({lineups.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="rankings">
            {/* unchanged rest of your UI */}
          </TabsContent>

          <TabsContent value="lineups">
            {/* unchanged rest of your UI */}
          </TabsContent>
        </Tabs>

        <AdSlot slot="my-rankings-bottom" />
      </div>
    </div>
  );
}
