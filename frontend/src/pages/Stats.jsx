import { useEffect, useMemo, useState } from "react";
import Navbar from "../components/Navbar";
import StatsTable from "../components/StatsTable";
import { api } from "../lib/api";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Search, X } from "lucide-react";

const POSITIONS = ["ALL", "QB", "RB", "WR", "TE"];
const SCORINGS = [
  { v: "half_ppr", l: "Half PPR" },
  { v: "ppr", l: "PPR" },
  { v: "standard", l: "Standard" },
];
const SEASONS = ["2024", "2023", "2022"];

export default function Stats() {
  const [position, setPosition] = useState("ALL");
  const [team, setTeam] = useState("ALL");
  const [season, setSeason] = useState("2024");
  const [scoring, setScoring] = useState("half_ppr");
  const [search, setSearch] = useState("");
  const [teams, setTeams] = useState([]);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/teams").then((r) => setTeams(r.data)).catch(() => {});
  }, []);

  const params = useMemo(() => ({
    position, team, season: Number(season), scoring, search: search || undefined, limit: 500,
  }), [position, team, season, scoring, search]);

  useEffect(() => {
    setLoading(true);
    const t = setTimeout(() => {
      api.get("/players", { params })
        .then((r) => setRows(r.data.items || []))
        .finally(() => setLoading(false));
    }, 200);
    return () => clearTimeout(t);
  }, [params]);

  const reset = () => {
    setPosition("ALL"); setTeam("ALL"); setSeason("2024"); setScoring("half_ppr"); setSearch("");
  };

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />

      <div className="border-b border-slate-800 bg-slate-950/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-[10px] font-bold tracking-[0.25em] uppercase text-emerald-400 mb-2">◆ The Lab · Stats Browser</div>
          <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight text-white" data-testid="stats-title">Player Stats</h1>
          <p className="text-slate-400 mt-2 max-w-2xl">Real NFL seasonal data from nflverse · click any row for the full player profile, AI outlook, and team news.</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="bg-slate-950/60 border border-slate-800 rounded-md p-4 mb-4 flex flex-wrap items-end gap-3" data-testid="filter-bar">
          <div className="flex-1 min-w-[220px]">
            <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">Search</label>
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search player name…"
                className="pl-9 bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
                data-testid="filter-search-input"
              />
            </div>
          </div>

          <FilterSelect label="Position" value={position} onChange={setPosition} options={POSITIONS} testid="filter-position" />
          <FilterSelect label="Team" value={team} onChange={setTeam} options={["ALL", ...teams]} testid="filter-team" />
          <FilterSelect label="Season" value={season} onChange={setSeason} options={SEASONS} testid="filter-season" />

          <div>
            <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">Scoring</label>
            <Select value={scoring} onValueChange={setScoring}>
              <SelectTrigger className="w-[140px] bg-slate-900 border-slate-700 text-white" data-testid="filter-scoring">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-700 text-white">
                {SCORINGS.map((s) => <SelectItem key={s.v} value={s.v} data-testid={`scoring-opt-${s.v}`}>{s.l}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <Button variant="outline" onClick={reset} className="border-slate-700 bg-transparent text-slate-300 hover:bg-slate-800 hover:text-white" data-testid="filter-reset-btn">
            <X className="w-4 h-4 mr-1" /> Reset
          </Button>
        </div>

        <div className="flex items-center justify-between mb-3">
          <div className="text-sm text-slate-400 font-mono-tab" data-testid="results-count">
            {loading ? "Loading…" : `${rows.length} players`}
          </div>
          <div className="text-[10px] text-slate-500 uppercase tracking-[0.2em]">Click any row to expand · click headers to sort</div>
        </div>

        <StatsTable rows={rows} scoring={scoring} />
      </div>
    </div>
  );
}

function FilterSelect({ label, value, onChange, options, testid }) {
  return (
    <div>
      <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">{label}</label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-[120px] bg-slate-900 border-slate-700 text-white" data-testid={testid}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent className="bg-slate-900 border-slate-700 text-white">
          {options.map((o) => (
            <SelectItem key={o} value={o} data-testid={`${testid}-opt-${o}`}>{o}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
