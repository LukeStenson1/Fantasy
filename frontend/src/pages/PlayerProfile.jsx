import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Navbar from "../components/Navbar";
import { api } from "../lib/api";
import { PositionBadge, TagBadge } from "../components/Badges";
import { Button } from "../components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { ArrowLeft, RefreshCcw, Sparkles, Newspaper } from "lucide-react";
import { toast } from "sonner";

const SCORINGS = [
  { v: "half_ppr", l: "Half PPR" },
  { v: "ppr", l: "PPR" },
  { v: "standard", l: "Standard" },
];

export default function PlayerProfile() {
  const { id } = useParams();
  const [player, setPlayer] = useState(null);
  const [outlook, setOutlook] = useState(null);
  const [loadingOutlook, setLoadingOutlook] = useState(false);
  const [scoring, setScoring] = useState("half_ppr");

  useEffect(() => {
    api.get(`/players/${id}`, { params: { scoring } }).then((r) => setPlayer(r.data));
  }, [id, scoring]);

  const loadOutlook = (regen = false) => {
    setLoadingOutlook(true);
    const url = regen ? `/players/${id}/outlook/regenerate` : `/players/${id}/outlook`;
    const method = regen ? api.post : api.get;
    method(url, regen ? null : { params: { scoring } }, { params: { scoring } })
      .then((r) => setOutlook(r.data))
      .catch((e) => toast.error("Failed to load outlook"))
      .finally(() => setLoadingOutlook(false));
  };

  useEffect(() => { setOutlook(null); }, [id, scoring]);

  if (!player) return (
    <div className="min-h-screen"><Navbar /><div className="max-w-7xl mx-auto p-8 text-slate-500">Loading player…</div></div>
  );

  const cur = player.current_season;
  const seasons = player.seasons || [];

  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      <div className="border-b border-slate-200 bg-slate-50" data-testid="player-header">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Link to="/stats" className="text-sm text-slate-600 hover:text-black flex items-center gap-1 mb-4" data-testid="back-to-stats">
            <ArrowLeft className="w-4 h-4" /> Back to stats
          </Link>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <PositionBadge position={player.position} />
                <span className="text-xs font-mono-tab text-slate-600">{player.team}</span>
                <TagBadge tag={player.tag} />
              </div>
              <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight" data-testid="player-name">{player.name}</h1>
              <div className="text-sm text-slate-600 mt-2 font-mono-tab">
                Age {player.age} · Year {player.experience}
              </div>
            </div>
            <div className="flex items-end gap-2">
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-600 block mb-1.5">Scoring</label>
                <Select value={scoring} onValueChange={setScoring}>
                  <SelectTrigger className="w-[140px]" data-testid="profile-scoring">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SCORINGS.map((s) => <SelectItem key={s.v} value={s.v}>{s.l}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Quick stat strip */}
          {cur && (
            <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-px bg-slate-200 border border-slate-200 rounded-md overflow-hidden" data-testid="player-quickstats">
              <Quick label={`${cur.season} FPts`} value={cur[`fpts_${scoring}`]} />
              <Quick label={`${cur.season} FPts/G`} value={cur[`fpts_per_game_${scoring}`]} />
              <Quick label="Total Yds" value={cur.total_yards?.toLocaleString()} />
              <Quick label="Total TDs" value={cur.total_tds} />
            </div>
          )}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs defaultValue="stats">
          <TabsList data-testid="profile-tabs">
            <TabsTrigger value="stats" data-testid="tab-stats">Career Stats</TabsTrigger>
            <TabsTrigger value="outlook" data-testid="tab-outlook">AI Outlook</TabsTrigger>
            <TabsTrigger value="news" data-testid="tab-news">Team News</TabsTrigger>
          </TabsList>

          <TabsContent value="stats" className="mt-6">
            <div className="overflow-auto border border-slate-200 rounded-md bg-white">
              <table className="pfr-table w-full" data-testid="career-table">
                <thead><tr>
                  <th>Season</th><th>G</th><th>Pass Yds</th><th>Pass TD</th><th>INT</th>
                  <th>Rush Yds</th><th>Rush TD</th><th>Rec</th><th>Rec Yds</th><th>Rec TD</th>
                  <th>FPts</th><th>FPts/G</th>
                </tr></thead>
                <tbody>
                  {seasons.map((s) => (
                    <tr key={s.season} data-testid={`season-row-${s.season}`}>
                      <td className="font-bold">{s.season}</td>
                      <td className="font-mono-tab">{s.games}</td>
                      <td className="font-mono-tab">{s.pass_yds?.toLocaleString() || "—"}</td>
                      <td className="font-mono-tab">{s.pass_td || "—"}</td>
                      <td className="font-mono-tab">{s.pass_int || "—"}</td>
                      <td className="font-mono-tab">{s.rush_yds?.toLocaleString() || "—"}</td>
                      <td className="font-mono-tab">{s.rush_td || "—"}</td>
                      <td className="font-mono-tab">{s.receptions || "—"}</td>
                      <td className="font-mono-tab">{s.rec_yds?.toLocaleString() || "—"}</td>
                      <td className="font-mono-tab">{s.rec_td || "—"}</td>
                      <td className="font-mono-tab font-bold">{s[`fpts_${scoring}`]}</td>
                      <td className="font-mono-tab font-bold">{s[`fpts_per_game_${scoring}`]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="outlook" className="mt-6">
            <div className="bg-white border border-slate-200 rounded-md p-6" data-testid="outlook-panel">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-emerald-600" />
                  <h2 className="font-display text-2xl font-bold">Fantasy Outlook</h2>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => loadOutlook(false)} disabled={loadingOutlook} data-testid="outlook-load-btn">
                    {outlook ? "Reload" : "Generate"}
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => loadOutlook(true)} disabled={loadingOutlook} data-testid="outlook-regen-btn">
                    <RefreshCcw className="w-4 h-4 mr-1" /> Regenerate
                  </Button>
                </div>
              </div>
              {!outlook && !loadingOutlook && (
                <p className="text-slate-500 text-sm">Click <strong>Generate</strong> to produce an AI-powered fantasy outlook based on this player's stats and recent news.</p>
              )}
              {loadingOutlook && <p className="text-slate-500 text-sm">Generating outlook…</p>}
              {outlook && (
                <div className="prose prose-slate max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-[15px] leading-relaxed text-slate-800" data-testid="outlook-text">{outlook.outlook}</pre>
                  <div className="text-xs text-slate-400 mt-3 font-mono-tab">Generated {new Date(outlook.generated_at).toLocaleString()} · {scoring.replace("_"," ").toUpperCase()}</div>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="news" className="mt-6">
            <div className="bg-white border border-slate-200 rounded-md" data-testid="news-panel">
              <div className="px-6 py-4 border-b border-slate-200 flex items-center gap-2">
                <Newspaper className="w-5 h-5 text-slate-700" />
                <h2 className="font-display text-2xl font-bold">Team News & Insights</h2>
              </div>
              <ul>
                {(player.news || []).length === 0 && (
                  <li className="px-6 py-8 text-sm text-slate-500 text-center">No recent news indexed for this player.</li>
                )}
                {(player.news || []).map((n, i) => (
                  <li key={i} className="px-6 py-4 border-b border-slate-100 last:border-b-0" data-testid={`news-item-${i}`}>
                    <div className="flex items-center gap-2 text-xs font-mono-tab text-slate-500 mb-1">
                      <span>{n.date}</span> · <span className="font-bold uppercase">{n.source}</span>
                      <span className={`ml-auto px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${
                        n.sentiment === "positive" ? "bg-emerald-50 text-emerald-700" :
                        n.sentiment === "negative" ? "bg-red-50 text-red-700" :
                        "bg-slate-100 text-slate-700"
                      }`}>{(n.sentiment || "neutral").toUpperCase()}</span>
                    </div>
                    <h3 className="font-bold text-slate-900">{n.headline}</h3>
                    <p className="text-sm text-slate-600 mt-1">{n.snippet}</p>
                  </li>
                ))}
              </ul>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function Quick({ label, value }) {
  return (
    <div className="bg-white p-4">
      <div className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500 mb-1">{label}</div>
      <div className="font-display font-black text-2xl font-mono-tab tracking-tight">{value ?? "—"}</div>
    </div>
  );
}
