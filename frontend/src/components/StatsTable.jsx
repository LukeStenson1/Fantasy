import { useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronDown, ChevronRight, RefreshCcw, Sparkles, Newspaper } from "lucide-react";
import { PositionBadge, TagBadge } from "./Badges";
import { api } from "../lib/api";
import { Button } from "./ui/button";

const COLUMNS = [
  { key: "name", label: "Player", sortable: true },
  { key: "position", label: "Pos", sortable: true },
  { key: "team", label: "Tm", sortable: true },
  { key: "season", label: "Yr", sortable: true, fromCurrent: true, type: "num" },
  { key: "games", label: "G", sortable: true, fromCurrent: true, type: "num" },
  { key: "pass_yds", label: "Pass Yd", sortable: true, fromCurrent: true, type: "num" },
  { key: "pass_td", label: "Pass TD", sortable: true, fromCurrent: true, type: "num" },
  { key: "rush_yds", label: "Rush Yd", sortable: true, fromCurrent: true, type: "num" },
  { key: "rush_td", label: "Rush TD", sortable: true, fromCurrent: true, type: "num" },
  { key: "receptions", label: "Rec", sortable: true, fromCurrent: true, type: "num" },
  { key: "rec_yds", label: "Rec Yd", sortable: true, fromCurrent: true, type: "num" },
  { key: "rec_td", label: "Rec TD", sortable: true, fromCurrent: true, type: "num" },
  { key: "current_fpts", label: "FPts", sortable: true, type: "num", emphasize: true },
  { key: "current_fpts_per_game", label: "FPts/G", sortable: true, type: "num", emphasize: true },
];

function getValue(p, col) {
  if (col.key === "current_fpts" || col.key === "current_fpts_per_game") return p[col.key];
  if (col.fromCurrent) return p.current_season?.[col.key];
  return p[col.key];
}

export default function StatsTable({ rows, scoring }) {
  const [sortKey, setSortKey] = useState("current_fpts");
  const [dir, setDir] = useState("desc");
  const [expandedId, setExpandedId] = useState(null);

  const sorted = useMemo(() => {
    const arr = [...rows];
    arr.sort((a, b) => {
      const col = COLUMNS.find((c) => c.key === sortKey) || COLUMNS[0];
      const av = getValue(a, col);
      const bv = getValue(b, col);
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "number" && typeof bv === "number")
        return dir === "asc" ? av - bv : bv - av;
      return dir === "asc"
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
    return arr;
  }, [rows, sortKey, dir]);

  const onSort = (key) => {
    if (sortKey === key) setDir(dir === "asc" ? "desc" : "asc");
    else { setSortKey(key); setDir("desc"); }
  };

  const SortIcon = ({ k }) => {
    if (sortKey !== k) return <ArrowUpDown className="w-3 h-3 inline opacity-30" />;
    return dir === "asc" ? <ArrowUp className="w-3 h-3 inline text-emerald-400" /> : <ArrowDown className="w-3 h-3 inline text-emerald-400" />;
  };

  return (
    <div className="overflow-auto border border-slate-800 rounded-md bg-slate-950/60" data-testid="stats-table-wrapper">
      <table className="pfr-table w-full" data-testid="stats-table">
        <thead>
          <tr>
            <th style={{width: 28}}></th>
            {COLUMNS.map((c) => (
              <th key={c.key} onClick={() => c.sortable && onSort(c.key)}
                className={`text-left whitespace-nowrap ${c.emphasize ? "text-emerald-300" : ""}`}
                data-testid={`col-header-${c.key}`}>
                {c.label} {c.sortable && <SortIcon k={c.key} />}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 && (
            <tr><td colSpan={COLUMNS.length + 1} className="text-center py-8 text-slate-500">No players match these filters.</td></tr>
          )}
          {sorted.map((p) => (
            <PlayerRow
              key={p.id}
              player={p}
              expanded={expandedId === p.id}
              onToggle={() => setExpandedId(expandedId === p.id ? null : p.id)}
              scoring={scoring}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PlayerRow({ player, expanded, onToggle, scoring }) {
  const p = player;
  return (
    <>
      <tr className="pfr-row" onClick={onToggle} data-testid={`row-${p.id}`}>
        <td className="px-2 text-slate-500">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </td>
        <td className="font-semibold text-white">
          <div className="flex items-center gap-2">
            <span data-testid={`player-name-${p.id}`}>{p.name}</span>
            <TagBadge tag={p.tag} />
          </div>
        </td>
        <td><PositionBadge position={p.position} /></td>
        <td className="font-mono-tab text-slate-400">{p.team}</td>
        {COLUMNS.slice(3).map((c) => {
          const v = getValue(p, c);
          const formatted = v == null ? "—" :
            c.key === "season" ? String(v) :
            typeof v === "number" ? v.toLocaleString() : v;
          return (
            <td key={c.key} className={`font-mono-tab ${c.emphasize ? "font-bold text-emerald-300" : "text-slate-300"}`}>
              {formatted}
            </td>
          );
        })}
      </tr>
      {expanded && (
        <tr className="expand-row" data-testid={`expand-row-${p.id}`}>
          <td colSpan={COLUMNS.length + 1} className="bg-slate-900/40 border-t border-emerald-500/20 p-0">
            <ExpandedContent player={p} scoring={scoring} />
          </td>
        </tr>
      )}
    </>
  );
}

function ExpandedContent({ player, scoring }) {
  const [full, setFull] = useState(null);
  const [outlook, setOutlook] = useState(null);
  const [loadingOutlook, setLoadingOutlook] = useState(false);

  useEffect(() => {
    api.get(`/players/${player.id}`, { params: { scoring } }).then((r) => setFull(r.data));
  }, [player.id, scoring]);

  const loadOutlook = (regen = false) => {
    setLoadingOutlook(true);
    if (regen) {
      api.post(`/players/${player.id}/outlook/regenerate`, null, { params: { scoring } })
        .then((r) => setOutlook(r.data))
        .finally(() => setLoadingOutlook(false));
    } else {
      api.get(`/players/${player.id}/outlook`, { params: { scoring } })
        .then((r) => setOutlook(r.data))
        .finally(() => setLoadingOutlook(false));
    }
  };

  if (!full) return <div className="p-6 text-slate-500 text-sm">Loading…</div>;
  const seasons = full.seasons || [];

  return (
    <div className="p-6 space-y-6">
      {/* header strip */}
      <div className="flex flex-wrap items-center gap-4">
        <div>
          <div className="text-[10px] font-bold tracking-[0.2em] uppercase text-slate-500">Player</div>
          <div className="font-display text-2xl font-bold text-white">{full.name}</div>
        </div>
        <div className="flex flex-wrap gap-3 ml-auto">
          <Stat label="Age" value={full.age ?? "—"} />
          <Stat label="Yrs" value={full.experience ?? "—"} />
          {full.next_opponent && <Stat label="Next Opp" value={full.next_opponent} />}
          {full.matchup_def_rank && (
            <Stat
              label={`vs ${full.position} D`}
              value={`#${full.matchup_def_rank}`}
              accent={full.matchup_def_rank >= 24 ? "text-emerald-400" : full.matchup_def_rank <= 8 ? "text-red-400" : "text-slate-300"}
            />
          )}
        </div>
      </div>

      {/* Career stats mini table */}
      <div>
        <div className="text-[10px] font-bold tracking-[0.2em] uppercase text-slate-500 mb-2">Career Production</div>
        <div className="overflow-auto border border-slate-800 rounded-md bg-slate-950/40">
          <table className="pfr-table w-full" data-testid={`career-table-${player.id}`}>
            <thead><tr>
              <th>Season</th><th>G</th><th>Pass Yd</th><th>Pass TD</th><th>INT</th>
              <th>Rush Yd</th><th>Rush TD</th><th>Rec</th><th>Tgt</th><th>Rec Yd</th><th>Rec TD</th>
              <th className="text-emerald-300">FPts</th><th className="text-emerald-300">FPts/G</th>
            </tr></thead>
            <tbody>
              {seasons.map((s) => (
                <tr key={s.season}>
                  <td className="font-bold text-white">{s.season}</td>
                  <td className="font-mono-tab">{s.games}</td>
                  <td className="font-mono-tab">{s.pass_yds?.toLocaleString() || "—"}</td>
                  <td className="font-mono-tab">{s.pass_td || "—"}</td>
                  <td className="font-mono-tab">{s.pass_int || "—"}</td>
                  <td className="font-mono-tab">{s.rush_yds?.toLocaleString() || "—"}</td>
                  <td className="font-mono-tab">{s.rush_td || "—"}</td>
                  <td className="font-mono-tab">{s.receptions || "—"}</td>
                  <td className="font-mono-tab">{s.targets || "—"}</td>
                  <td className="font-mono-tab">{s.rec_yds?.toLocaleString() || "—"}</td>
                  <td className="font-mono-tab">{s.rec_td || "—"}</td>
                  <td className="font-mono-tab font-bold text-emerald-300">{s[`fpts_${scoring}`]}</td>
                  <td className="font-mono-tab font-bold text-emerald-300">{s[`fpts_per_game_${scoring}`]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* AI Outlook + News side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-slate-950/40 border border-slate-800 rounded-md" data-testid={`outlook-${player.id}`}>
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              <h3 className="font-display font-bold text-white">AI Outlook</h3>
            </div>
            <div className="flex gap-1">
              <Button variant="ghost" size="sm" onClick={() => loadOutlook(false)} disabled={loadingOutlook}
                className="h-7 text-xs border border-slate-700 bg-transparent hover:bg-slate-800 text-slate-300">
                {outlook ? "Reload" : "Generate"}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => loadOutlook(true)} disabled={loadingOutlook}
                className="h-7 text-xs border border-slate-700 bg-transparent hover:bg-slate-800 text-slate-300">
                <RefreshCcw className="w-3 h-3" />
              </Button>
            </div>
          </div>
          <div className="p-4">
            {!outlook && !loadingOutlook && <p className="text-sm text-slate-500">Click Generate to produce an AI fantasy outlook.</p>}
            {loadingOutlook && <p className="text-sm text-slate-500">Generating outlook…</p>}
            {outlook && (
              <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-200" data-testid={`outlook-text-${player.id}`}>
                {outlook.outlook}
              </pre>
            )}
          </div>
        </div>

        <div className="bg-slate-950/40 border border-slate-800 rounded-md" data-testid={`news-${player.id}`}>
          <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800">
            <Newspaper className="w-4 h-4 text-slate-400" />
            <h3 className="font-display font-bold text-white">Team News & Insights</h3>
          </div>
          <div className="p-4">
            {(full.news || []).length === 0 && (
              <p className="text-sm text-slate-500">No indexed news. AI outlook synthesizes recent context from stats trajectory.</p>
            )}
            <ul className="space-y-3">
              {(full.news || []).map((n, i) => (
                <li key={i} className="text-sm">
                  <div className="text-[10px] font-mono-tab text-slate-500 mb-0.5">{n.date} · <span className="font-bold uppercase">{n.source}</span></div>
                  <div className="font-bold text-white">{n.headline}</div>
                  <div className="text-slate-400">{n.snippet}</div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, accent = "text-slate-200" }) {
  return (
    <div className="border border-slate-800 rounded-md px-3 py-2 bg-slate-950/40">
      <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-slate-500">{label}</div>
      <div className={`font-mono-tab font-bold text-base ${accent}`}>{value}</div>
    </div>
  );
}
