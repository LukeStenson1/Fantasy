import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { PositionBadge, TagBadge } from "./Badges";

const COLUMNS = [
  { key: "name", label: "Player", sortable: true, sticky: true },
  { key: "position", label: "Pos", sortable: true },
  { key: "team", label: "Team", sortable: true },
  { key: "season", label: "Yr", sortable: true, fromCurrent: true, type: "num" },
  { key: "games", label: "G", sortable: true, fromCurrent: true, type: "num" },
  { key: "pass_yds", label: "Pass Yds", sortable: true, fromCurrent: true, type: "num" },
  { key: "pass_td", label: "Pass TD", sortable: true, fromCurrent: true, type: "num" },
  { key: "rush_yds", label: "Rush Yds", sortable: true, fromCurrent: true, type: "num" },
  { key: "rush_td", label: "Rush TD", sortable: true, fromCurrent: true, type: "num" },
  { key: "receptions", label: "Rec", sortable: true, fromCurrent: true, type: "num" },
  { key: "rec_yds", label: "Rec Yds", sortable: true, fromCurrent: true, type: "num" },
  { key: "rec_td", label: "Rec TD", sortable: true, fromCurrent: true, type: "num" },
  { key: "current_fpts", label: "FPts", sortable: true, type: "num", emphasize: true },
  { key: "current_fpts_per_game", label: "FPts/G", sortable: true, type: "num", emphasize: true },
];

function getValue(p, col) {
  if (col.key === "current_fpts" || col.key === "current_fpts_per_game") return p[col.key];
  if (col.fromCurrent) return p.current_season?.[col.key];
  return p[col.key];
}

export default function StatsTable({ rows }) {
  const [sortKey, setSortKey] = useState("current_fpts");
  const [dir, setDir] = useState("desc");

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
    if (sortKey !== k) return <ArrowUpDown className="w-3 h-3 inline opacity-40" />;
    return dir === "asc" ? <ArrowUp className="w-3 h-3 inline" /> : <ArrowDown className="w-3 h-3 inline" />;
  };

  return (
    <div className="overflow-auto border border-slate-200 rounded-md bg-white" data-testid="stats-table-wrapper">
      <table className="pfr-table w-full" data-testid="stats-table">
        <thead>
          <tr>
            {COLUMNS.map((c) => (
              <th
                key={c.key}
                onClick={() => c.sortable && onSort(c.key)}
                className={`text-left whitespace-nowrap ${c.emphasize ? "text-black" : ""}`}
                data-testid={`col-header-${c.key}`}
              >
                {c.label} {c.sortable && <SortIcon k={c.key} />}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 && (
            <tr><td colSpan={COLUMNS.length} className="text-center py-8 text-slate-500">No players match these filters.</td></tr>
          )}
          {sorted.map((p) => (
            <tr key={p.id} data-testid={`row-${p.id}`}>
              <td className="font-semibold sticky left-0 bg-inherit">
                <div className="flex items-center gap-2">
                  <Link to={`/player/${p.id}`} className="hover:underline" data-testid={`player-link-${p.id}`}>
                    {p.name}
                  </Link>
                  <TagBadge tag={p.tag} />
                </div>
              </td>
              <td><PositionBadge position={p.position} /></td>
              <td className="font-mono-tab text-slate-700">{p.team}</td>
              {COLUMNS.slice(3).map((c) => {
                const v = getValue(p, c);
                const formatted = v == null ? "—" :
                  c.key === "season" ? String(v) :
                  typeof v === "number" ? v.toLocaleString() : v;
                return (
                  <td key={c.key} className={`font-mono-tab ${c.emphasize ? "font-bold text-black" : "text-slate-700"}`}>
                    {formatted}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
