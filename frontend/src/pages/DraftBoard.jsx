import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { api } from "../lib/api";
import { Link } from "react-router-dom";
import { PositionBadge, TagBadge } from "../components/Badges";
import { useSport } from "../contexts/SportContext";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { TrendingUp, TrendingDown, Flame, Star, GraduationCap, Sparkles, ExternalLink } from "lucide-react";

const NFL_POSITIONS = ["ALL", "QB", "RB", "WR", "TE"];
const NBA_POSITIONS = ["ALL", "PG", "SG", "SF", "PF", "C"];
const MLB_POSITIONS = ["ALL", "C", "1B", "2B", "3B", "SS", "OF", "DH", "SP", "RP"];

const ROOKIE_FILTERS = [
  { v: "ALL",           l: "All Rookies" },
  { v: "elite_landing", l: "Elite Landing" },
  { v: "sleeper",       l: "Sleepers" },
  { v: "deep_dart",     l: "Deep Darts" },
];

const SPORT_DESC = {
  nfl: "Players grouped by fantasy outlook — auto-tagged from stat trajectories. Elites and breakouts ranked highest, sleepers are speculative, bust risks flagged.",
  nba: "NBA players grouped by fantasy outlook — based on per-game scoring, efficiency trends, and role changes.",
  mlb: "MLB players grouped by fantasy outlook — based on batting production, pitching performance, and trajectory.",
};

export default function DraftBoard() {
  const { sport, config } = useSport();
  const [data, setData] = useState({ sleepers: [], busts: [], breakouts: [], elites: [] });
  const [rookies, setRookies] = useState([]);
  const [rookieYear, setRookieYear] = useState(null);
  const [rookiePosition, setRookiePosition] = useState("ALL");
  const [rookieOutlook, setRookieOutlook] = useState("ALL");
  const [outlookCache, setOutlookCache] = useState({});
  const [activeId, setActiveId] = useState(null);

  useEffect(() => {
    api.get("/sleepers-busts", { params: { scoring: "half_ppr", sport } })
      .then((r) => setData(r.data))
      .catch(() => {});
    if (sport === "nfl") {
      api.get("/rookies")
        .then((r) => { setRookies(r.data.items || []); setRookieYear(r.data.rookie_year); })
        .catch(() => {});
    }
  }, [sport]);

  const positions = sport === "nba" ? NBA_POSITIONS : sport === "mlb" ? MLB_POSITIONS : NFL_POSITIONS;

  const filteredRookies = rookies.filter((r) =>
    (rookiePosition === "ALL" || r.position === rookiePosition) &&
    (rookieOutlook === "ALL" || r.outlook_label === rookieOutlook)
  );

  const loadOutlook = async (id) => {
    setActiveId(activeId === id ? null : id);
    if (outlookCache[id] || activeId === id) return;
    const { data } = await api.get(`/players/${id}/outlook`);
    setOutlookCache((prev) => ({ ...prev, [id]: data }));
  };

  const SECTIONS = [
    {
      key: "elites",
      title: "Elite Tier",
      icon: Star,
      desc: sport === "nba" ? "Top NBA fantasy producers this season."
        : sport === "mlb" ? "Elite batters and pitchers by FPts/G."
        : "Established top-shelf fantasy producers.",
    },
    {
      key: "breakouts",
      title: "Breakouts",
      icon: Flame,
      desc: sport === "nba" ? "Players whose production jumped significantly this season."
        : sport === "mlb" ? "Hitters and pitchers trending up from last season."
        : "Players whose recent trajectory points up — stats already back it up.",
    },
    {
      key: "sleepers",
      title: "Sleepers",
      icon: TrendingUp,
      desc: sport === "nba" ? "High-upside players with limited track record."
        : sport === "mlb" ? "Under-the-radar hitters and pitchers worth watching."
        : "Speculative upside picks — limited experience but promising path.",
    },
    {
      key: "busts",
      title: "Bust Risks",
      icon: TrendingDown,
      desc: sport === "nba" ? "Players with injury concerns or declining production."
        : sport === "mlb" ? "Pitchers or hitters with concerning metrics."
        : "Volatility, injury, or scheme concerns.",
    },
  ];

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />

      {/* HEADER */}
      <div className="border-b border-slate-800 bg-slate-950/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div
            className="text-[10px] font-bold tracking-[0.25em] uppercase mb-2"
            style={{ color: config.hex }}
          >
            ◆ The Lab · {sport === "nba" ? "NBA " : sport === "mlb" ? "MLB " : ""}Draft Board
          </div>
          <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight text-white">
            {sport === "nba" ? "NBA Player Board" : sport === "mlb" ? "MLB Player Board" : "Draft Board"}
          </h1>
          <p className="text-slate-400 mt-2 max-w-2xl">{SPORT_DESC[sport]}</p>
        </div>
      </div>

      {/* SECTIONS */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 grid grid-cols-1 md:grid-cols-2 gap-4">
        {SECTIONS.map((s) => {
          const Icon = s.icon;
          const list = data[s.key] || [];
          return (
            <div key={s.key} className="bg-slate-950/60 border border-slate-800 rounded-md overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-800 flex items-center gap-3">
                <div className="w-9 h-9 flex items-center justify-center rounded-md"
                  style={{
                    background: s.key === "elites" ? config.hex
                      : s.key === "breakouts" ? config.hexAlpha
                      : s.key === "busts" ? "#ef444420"
                      : "#8b5cf620",
                  }}>
                  <Icon className="w-4 h-4"
                    style={{
                      color: s.key === "elites" ? "#0a0e16"
                        : s.key === "breakouts" ? config.hex
                        : s.key === "busts" ? "#f87171"
                        : "#a78bfa",
                    }} />
                </div>
                <div className="flex-1">
                  <h2 className="font-display font-bold text-xl text-white leading-tight">{s.title}</h2>
                  <div className="text-xs text-slate-500">{s.desc}</div>
                </div>
                <span className="font-mono-tab text-sm text-slate-400 font-bold">{list.length}</span>
              </div>
              <ul className="max-h-[480px] overflow-auto">
                {list.length === 0 && (
                  <li className="px-5 py-6 text-sm text-slate-500 text-center">No players tagged here.</li>
                )}
                {list.map((p) => (
                  <li key={p.id}
                    className="px-5 py-3 border-b border-slate-800 last:border-b-0 flex items-center justify-between hover:bg-slate-900 transition-colors">
                    <div className="flex items-center gap-3">
                      <PositionBadge position={p.position} />
                      <Link to="/stats" className="font-semibold text-white hover:opacity-80 transition-opacity"
                        style={{ '--hover': config.hex }}>
                        {p.name}
                      </Link>
                      <span className="text-xs font-mono-tab text-slate-500">{p.team}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <TagBadge tag={p.tag} config={config} />
                      <span className="font-mono-tab text-sm font-bold"
                        style={{ color: config.hexLight }}>
                        {p.current_fpts_per_game?.toFixed?.(1) ?? "—"}/g
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      {/* ROOKIES — NFL only */}
      {sport === "nfl" && (
        <>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-4">
            <div className="flex items-center gap-4">
              <div className="flex-1 h-px bg-slate-800" />
              <div className="text-[10px] font-bold tracking-[0.25em] uppercase"
                style={{ color: config.hex }}>
                ◆ Rookie Class {rookieYear || ""}
              </div>
              <div className="flex-1 h-px bg-slate-800" />
            </div>
          </div>

          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
            <div className="flex flex-wrap gap-2 mb-6 items-center">
              <div className="flex flex-wrap gap-2">
                {ROOKIE_FILTERS.map((f) => (
                  <button
                    key={f.v}
                    onClick={() => setRookieOutlook(f.v)}
                    className="px-3 py-1.5 text-xs font-bold tracking-wider uppercase border rounded-md transition-colors"
                    style={rookieOutlook === f.v
                      ? { background: config.hex, color: "#0a0e16", borderColor: "transparent" }
                      : { background: "transparent", color: "#cbd5e1", borderColor: "#334155" }}
                  >
                    {f.l}
                  </button>
                ))}
              </div>
              <div className="ml-auto">
                <Select value={rookiePosition} onValueChange={setRookiePosition}>
                  <SelectTrigger className="w-[140px] bg-slate-900 border-slate-700 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700 text-white">
                    {NFL_POSITIONS.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="text-sm text-slate-400 mb-3 font-mono-tab">{filteredRookies.length} rookies</div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {filteredRookies.map((r) => (
                <RookieCard
                  key={r.id}
                  rookie={r}
                  expanded={activeId === r.id}
                  onToggle={() => loadOutlook(r.id)}
                  outlook={outlookCache[r.id]}
                  config={config}
                />
              ))}
              {filteredRookies.length === 0 && (
                <div className="md:col-span-2 bg-slate-950/40 border border-dashed border-slate-700 rounded-md p-10 text-center text-slate-500">
                  No rookies match these filters.
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* NBA/MLB — no rookies section, just padding */}
      {sport !== "nfl" && <div className="pb-20" />}
    </div>
  );
}

function RookieCard({ rookie, expanded, onToggle, outlook, config }) {
  const r = rookie;
  const labelColor = {
    elite_landing: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
    sleeper:       "bg-blue-500/15 text-blue-300 border-blue-500/40",
    deep_dart:     "bg-amber-500/15 text-amber-300 border-amber-500/40",
  }[r.outlook_label] || "bg-slate-700/30 text-slate-300 border-slate-700";

  const labelText = {
    elite_landing: "ELITE LANDING",
    sleeper:       "ROOKIE SLEEPER",
    deep_dart:     "DEEP DART",
  }[r.outlook_label] || "—";

  return (
    <div
      className="bg-slate-950/60 border rounded-md transition-all cursor-pointer"
      style={{ borderColor: expanded ? `${config.hex}80` : "" }}
      onClick={onToggle}
    >
      <div className="p-4 flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <PositionBadge position={r.position} />
            <span className={`px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase border rounded ${labelColor}`}>
              {labelText}
            </span>
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
          {r.draft_round && (
            <div className="border border-slate-800 rounded px-2 py-1 bg-slate-950">
              <div className="text-[9px] font-bold tracking-[0.15em] uppercase text-slate-500">Draft</div>
              <div className="font-mono-tab font-bold text-base"
                style={{ color: config.hexLight }}>
                R{r.draft_round} #{r.draft_number}
              </div>
            </div>
          )}
        </div>
      </div>

      {expanded && (
        <div className="border-t p-4"
          style={{ borderColor: `${config.hex}33`, background: "#0a0e1680" }}>
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4" style={{ color: config.hex }} />
            <h4 className="font-display font-bold text-white">Player + Team Outlook</h4>
            {r.news_search_url && (
              <a href={r.news_search_url} target="_blank" rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="ml-auto text-xs hover:opacity-80 flex items-center gap-1"
                style={{ color: config.hex }}>
                Latest news <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
          <p className="text-[11px] text-slate-500 mb-2">Outlook auto-updates as new game data flows into the Lab.</p>
          {!outlook ? (
            <p className="text-sm text-slate-500">Generating outlook…</p>
          ) : (
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-200">
              {outlook.outlook}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
