import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Plus, Trash2, X } from "lucide-react";
import { PositionBadge } from "../components/Badges";
import { toast } from "sonner";

export default function MyRankings() {
  const { user, loading } = useAuth();
  const [rankings, setRankings] = useState([]);
  const [creating, setCreating] = useState(false);

  // builder state
  const [title, setTitle] = useState("");
  const [scoring, setScoring] = useState("half_ppr");
  const [search, setSearch] = useState("");
  const [results, setResults] = useState([]);
  const [picked, setPicked] = useState([]);

  useEffect(() => {
    if (user && user !== false) api.get("/rankings/me").then((r) => setRankings(r.data));
  }, [user]);

  useEffect(() => {
    if (!creating) return;
    const t = setTimeout(() => {
      api.get("/players", { params: { search: search || undefined, scoring, limit: 30 } })
        .then((r) => setResults(r.data.items || []));
    }, 200);
    return () => clearTimeout(t);
  }, [search, scoring, creating]);

  if (loading) return <div className="min-h-screen"><Navbar /><div className="p-8 text-slate-500">Loading…</div></div>;
  if (user === false) return <Navigate to="/login" replace />;

  const addPick = (p) => {
    if (picked.find((x) => x.id === p.id)) return;
    setPicked([...picked, p]);
  };
  const removePick = (id) => setPicked(picked.filter((x) => x.id !== id));

  const save = async () => {
    if (!title.trim() || picked.length === 0) {
      toast.error("Add a title and at least one player");
      return;
    }
    try {
      const { data } = await api.post("/rankings", {
        title, scoring, player_ids: picked.map((p) => p.id),
      });
      setRankings([data, ...rankings]);
      setTitle(""); setPicked([]); setCreating(false);
      toast.success("Ranking saved");
    } catch (e) {
      toast.error("Failed to save ranking");
    }
  };

  const remove = async (id) => {
    await api.delete(`/rankings/${id}`);
    setRankings(rankings.filter((r) => r.id !== id));
    toast.success("Deleted");
  };

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <div className="border-b border-slate-200 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex items-end justify-between gap-4 flex-wrap">
          <div>
            <div className="text-xs font-bold tracking-[0.2em] uppercase text-slate-500 mb-2">◆ Draft Prep</div>
            <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight" data-testid="rankings-title">My Rankings</h1>
            <p className="text-slate-600 mt-2">Build and save your custom draft boards.</p>
          </div>
          <Button onClick={() => setCreating(!creating)} className="bg-black hover:bg-slate-800 text-white" data-testid="rankings-toggle-create">
            {creating ? <><X className="w-4 h-4 mr-1" /> Close</> : <><Plus className="w-4 h-4 mr-1" /> New Ranking</>}
          </Button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {creating && (
          <div className="bg-white border border-slate-200 rounded-md p-6" data-testid="ranking-builder">
            <h2 className="font-display text-xl font-bold mb-4">Build a new ranking</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
              <div className="md:col-span-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-600 block mb-1.5">Title</label>
                <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. My 2025 Half-PPR Top 50" data-testid="builder-title-input" />
              </div>
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-600 block mb-1.5">Scoring</label>
                <Select value={scoring} onValueChange={setScoring}>
                  <SelectTrigger data-testid="builder-scoring"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="half_ppr">Half PPR</SelectItem>
                    <SelectItem value="ppr">PPR</SelectItem>
                    <SelectItem value="standard">Standard</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-600 block mb-1.5">Search players</label>
                <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search…" data-testid="builder-search-input" />
                <div className="mt-2 border border-slate-200 rounded-md max-h-72 overflow-auto bg-white">
                  {results.map((p) => (
                    <button
                      key={p.id} onClick={() => addPick(p)}
                      className="w-full px-3 py-2 flex items-center justify-between hover:bg-slate-50 text-left border-b border-slate-100 last:border-b-0"
                      data-testid={`builder-add-${p.id}`}
                    >
                      <div className="flex items-center gap-2">
                        <PositionBadge position={p.position} />
                        <span className="font-semibold">{p.name}</span>
                        <span className="text-xs text-slate-500 font-mono-tab">{p.team}</span>
                      </div>
                      <Plus className="w-4 h-4 text-slate-400" />
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-600 block mb-1.5">Your picks ({picked.length})</label>
                <ol className="border border-slate-200 rounded-md max-h-72 overflow-auto bg-white" data-testid="builder-picks-list">
                  {picked.length === 0 && <li className="px-3 py-4 text-sm text-slate-500 text-center">Add players from the left.</li>}
                  {picked.map((p, i) => (
                    <li key={p.id} className="px-3 py-2 flex items-center justify-between border-b border-slate-100 last:border-b-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono-tab text-xs text-slate-500 w-6">{i + 1}.</span>
                        <PositionBadge position={p.position} />
                        <span className="font-semibold">{p.name}</span>
                      </div>
                      <button onClick={() => removePick(p.id)} className="text-slate-400 hover:text-red-600" data-testid={`builder-remove-${p.id}`}>
                        <X className="w-4 h-4" />
                      </button>
                    </li>
                  ))}
                </ol>
              </div>
            </div>

            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" onClick={() => { setCreating(false); setPicked([]); setTitle(""); }} data-testid="builder-cancel">Cancel</Button>
              <Button onClick={save} className="bg-black hover:bg-slate-800 text-white" data-testid="builder-save">Save Ranking</Button>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {rankings.length === 0 && (
            <div className="md:col-span-2 bg-slate-50 border border-dashed border-slate-300 rounded-md p-10 text-center text-slate-500" data-testid="rankings-empty">
              No rankings yet. Click <strong>New Ranking</strong> to build one.
            </div>
          )}
          {rankings.map((r) => (
            <div key={r.id} className="bg-white border border-slate-200 rounded-md p-5" data-testid={`ranking-${r.id}`}>
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="font-display font-bold text-xl">{r.title}</h3>
                  <div className="text-xs text-slate-500 font-mono-tab uppercase tracking-wider mt-0.5">
                    {r.scoring.replace("_", " ")} · {r.player_ids?.length || 0} players · {new Date(r.created_at).toLocaleDateString()}
                  </div>
                </div>
                <button onClick={() => remove(r.id)} className="text-slate-400 hover:text-red-600" data-testid={`ranking-delete-${r.id}`}>
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
