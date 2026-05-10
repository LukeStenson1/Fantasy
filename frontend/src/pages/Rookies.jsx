import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { api } from "../lib/api";
import { PositionBadge, TagBadge } from "../components/Badges";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { ExternalLink, GraduationCap, Sparkles, Trophy } from "lucide-react";
import { Button } from "../components/ui/button";

const POSITIONS = ["ALL", "QB", "RB", "WR", "TE"];
const FILTERS = [
  { v: "ALL", l: "All Outlooks", color: "bg-slate-700" },
  { v: "elite_landing", l: "Elite Landing Spots", color: "bg-emerald-500" },
  { v: "sleeper", l: "Rookie Sleepers", color: "bg-blue-500" },
  { v: "deep_dart", l: "Deep Dart Throws", color: "bg-amber-500" },
];

export default function Rookies() {
  const [rookies, setRookies] = useState([]);
  const [year, setYear] = useState(null);
  const [position, setPosition] = useState("ALL");
  const [outlook, setOutlook] = useState("ALL");
  const [outlookCache, setOutlookCache] = useState({});
  const [activeId, setActiveId] = useState(null);

  useEffect(() => {
    api.get("/rookies").then((r) => { setRookies(r.data.items || []); setYear(r.data.rookie_year); });
  }, []);

  const filtered = rookies.filter((r) =>
    (position === "ALL" || r.position === position) &&
    (outlook === "ALL" || r.outlook_label === outlook)
  );

  const loadOutlook = async (id) => {
    setActiveId(activeId === id ? null : id);
    if (outlookCache[id] || activeId === id) return;
    const { data } = await api.get(`/players/${id}/outlook`);
    setOutlookCache({ ...outlookCache, [id]: data });
  };

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />
      <div className="border-b border-slate-800 bg-slate-950/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-[10px] font-bold tracking-[0.25em] uppercase text-emerald-400 mb-2">◆ The Lab · Rookie Class {year || ""}</div>
          <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight text-white" data-testid="rookies-title">Rookie Sleepers & Busts</h1>
          <p className="text-slate-400 mt-2 max-w-2xl">Latest NFL draft class auto-pulled from rosters. Sorted by draft slot · click any rookie for an AI-generated year-1 outlook covering team fit, scheme, and projected role.</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Filter bar */}
        <div className="flex flex-wrap gap-2 mb-6" data-testid="rookies-filter-bar">
          <div className="flex flex-wrap gap-2">
            {FILTERS.map((f) => (
              <button
                key={f.v}
                onClick={() => setOutlook(f.v)}
                className={`px-3 py-1.5 text-xs font-bold tracking-wider uppercase border rounded-md transition-colors ${
                  outlook === f.v
                    ? `${f.color} text-slate-950 border-transparent`
                    : "bg-transparent text-slate-300 border-slate-700 hover:bg-slate-800"
                }`}
                data-testid={`rookies-filter-${f.v}`}
              >
                {f.l}
              </button>
            ))}
          </div>
          <div className="ml-auto">
            <Select value={position} onValueChange={setPosition}>
              <SelectTrigger className="w-[140px] bg-slate-900 border-slate-700 text-white" data-testid="rookies-position-filter">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-700 text-white">
                {POSITIONS.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="text-sm text-slate-400 mb-3 font-mono-tab" data-testid="rookies-count">{filtered.length} rookies</div>

        {/* Grid of rookie cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="rookies-grid">
          {filtered.map((r) => (
            <RookieCard
              key={r.id}
              rookie={r}
              expanded={activeId === r.id}
              onToggle={() => loadOutlook(r.id)}
              outlook={outlookCache[r.id]}
            />
          ))}
          {filtered.length === 0 && (
            <div className="md:col-span-2 bg-slate-950/40 border border-dashed border-slate-700 rounded-md p-10 text-center text-slate-500">
              No rookies match these filters.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function RookieCard({ rookie, expanded, onToggle, outlook }) {
  const r = rookie;
  const labelColor = {
    elite_landing: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
    sleeper: "bg-blue-500/15 text-blue-300 border-blue-500/40",
    deep_dart: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  }[r.outlook_label] || "bg-slate-700/30 text-slate-300 border-slate-700";
  const labelText = { elite_landing: "ELITE LANDING", sleeper: "ROOKIE SLEEPER", deep_dart: "DEEP DART" }[r.outlook_label] || "—";

  return (
    <div
      className={`bg-slate-950/60 border rounded-md transition-all cursor-pointer ${
        expanded ? "border-emerald-500/50" : "border-slate-800 hover:border-slate-600"
      }`}
      onClick={onToggle}
      data-testid={`rookie-card-${r.id}`}
    >
      <div className="p-4 flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <PositionBadge position={r.position} />
            <span className={`px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase border rounded ${labelColor}`}>{labelText}</span>
            <TagBadge tag={r.tag} />
          </div>
          <div className="font-display text-lg font-bold text-white leading-tight">{r.name}</div>
          <div className="text-xs text-slate-400 mt-0.5 font-mono-tab">
            {r.team} · Round {r.draft_round || "?"} (Pick #{r.draft_number || "?"})
          </div>
          {r.college && (
            <div className="text-xs text-slate-500 mt-1 flex items-center gap-1">
              <GraduationCap className="w-3 h-3" /> {r.college.split(";")[0].trim()}
            </div>
          )}
        </div>
        <div className="text-right shrink-0">
          {r.next_opponent && (
            <div className="border border-slate-800 rounded px-2 py-1 bg-slate-950">
              <div className="text-[9px] font-bold tracking-[0.15em] uppercase text-slate-500">vs {r.position} D</div>
              <div className={`font-mono-tab font-bold text-base ${
                (r.matchup_def_rank || 16) >= 24 ? "text-emerald-400" :
                (r.matchup_def_rank || 16) <= 8 ? "text-red-400" : "text-slate-300"
              }`}>
                {r.next_opponent} #{r.matchup_def_rank ?? "?"}
              </div>
            </div>
          )}
        </div>
      </div>

      {expanded && (
        <div className="border-t border-emerald-500/20 bg-slate-950/40 p-4 expand-row">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <h4 className="font-display font-bold text-white">AI Year-1 Outlook</h4>
            {r.news_search_url && (
              <a href={r.news_search_url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}
                className="ml-auto text-xs text-emerald-400 hover:underline flex items-center gap-1" data-testid={`rookie-news-link-${r.id}`}>
                Latest news <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
          {!outlook ? (
            <p className="text-sm text-slate-500">Generating outlook…</p>
          ) : (
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-200" data-testid={`rookie-outlook-${r.id}`}>
              {outlook.outlook}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
