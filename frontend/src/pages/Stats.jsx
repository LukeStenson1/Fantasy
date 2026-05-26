import { useEffect, useMemo, useState } from "react";
import Navbar from "../components/Navbar";
import StatsTable from "../components/StatsTable";
import { api, extractPlayers } from "../lib/api";
import { useSport } from "../contexts/SportContext";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { X } from "lucide-react";

const NFL_POSITIONS = ["ALL", "QB", "RB", "WR", "TE", "K", "DEF"];
const NBA_POSITIONS = ["ALL", "PG", "SG", "SF", "PF", "C"];
const MLB_POSITIONS = ["ALL", "C", "1B", "2B", "3B", "SS", "OF", "DH", "SP", "RP"];

const SCORINGS = [
  { v: "half_ppr", l: "Half PPR" },
  { v: "ppr", l: "PPR" },
  { v: "standard", l: "Standard" },
];

const currentYear = new Date().getFullYear();
const NFL_SEASONS = Array.from({ length: 4 }, (_, i) => String(currentYear - i));
const NBA_SEASONS = ["2025-26", "2024-25", "2023-24"];
const MLB_SEASONS = Array.from({ length: 3 }, (_, i) => String(currentYear - i));

const SPORT_LABELS = {
  nfl: "NFL Player Database",
  nba: "NBA Player Database",
  mlb: "MLB Player Database",
};

export default function Stats() {
  const { sport } = useSport();
  const [position, setPosition] = useState("ALL");
  const [team, setTeam] = useState("ALL");
  const [season, setSeason] = useState("");
  const [scoring, setScoring] = useState("half_ppr");
  const [search, setSearch] = useState("");
  const [teams, setTeams] = useState([]);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setPosition("ALL");
    setTeam("ALL");
    setSearch("");
    if (sport === "nba") setSeason("2025-26");
    else if (sport === "mlb") setSeason(String(currentYear));
    else setSeason(String(currentYear - 1));
  }, [sport]); // eslint-disable-line react-hooks/exhaustive-deps

  const positions = sport === "nba" ? NBA_POSITIONS : sport === "mlb" ? MLB_POSITIONS : NFL_POSITIONS;
  const seasons = sport === "nba" ? NBA_SEASONS : sport === "mlb" ? MLB_SEASONS : NFL_SEASONS;

  useEffect(() => {
    api.get("/teams", { params: { sport } })
      .then((r) => setTeams(r.data || []))
      .catch(() => setTeams([]));
  }, [sport]); // eslint-disable-line react-hooks/exhaustive-deps

  const params = useMemo(() => ({
    position,
    team,
    season: sport === "nba" ? season : Number(season),
    scoring,
    search: search || undefined,
    sport,
    limit: 500,
  }), [position, team, season, scoring, search, sport]);

  useEffect(() => {
    if (!season) return;
    setLoading(true);
    const t = setTimeout(() => {
      api.get("/players", { params })
        .then((r) => setRows(extractPlayers(r.data)))
        .catch(() => setRows([]))
        .finally(() => setLoading(false));
    }, 150);
    return () => clearTimeout(t);
  }, [params]); // eslint-disable-line react-hooks/exhaustive-deps

  const reset = () => {
    setPosition("ALL");
    setTeam("ALL");
    setSearch("");
    if (sport === "nba") setSeason("2025-26");
    else if (sport === "mlb") setSeason(String(currentYear));
    else setSeason(String(currentYear - 1));
  };

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />
      <div className="border-b border-slate-800 bg-slate-950/60">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="text-[10px] font-bold tracking-[0.25em] uppercase text-emerald-400 mb-2">◆ The Lab · Player Database</div>
          <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight text-white">Player Stats</h1>
          <p className="text-slate-400 mt-2">{SPORT_LABELS[sport]} (live API)</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[220px]">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search player..."
              className="bg-slate-900 text-white border-slate-700"
            />
          </div>
          <Filter label="Position" value={position} set={setPosition} opts={positions} />
          <Filter label="Team" value={team} set={setTeam} opts={["ALL", ...teams]} />
          <Filter label="Season" value={season} set={setSeason} opts={seasons} />
          {sport === "nfl" && (
            <Filter label="Scoring" value={scoring} set={setScoring}
              opts={SCORINGS.map(s => s.v)} labels={SCORINGS.map(s => s.l)} />
          )}
          <Button onClick={reset} variant="outline">
            <X className="w-4 h-4 mr-1" /> Reset
          </Button>
        </div>

        <div className="mt-4 text-slate-400">
          {loading ? "Loading..." : `${rows.length} players`}
        </div>

        <StatsTable rows={rows} scoring={scoring} sport={sport} />
      </div>
    </div>
  );
}

function Filter({ label, value, set, opts, labels }) {
  return (
    <div>
      <div className="text-xs text-slate-400 mb-1">{label}</div>
      <Select value={value} onValueChange={set}>
        <SelectTrigger className="w-[120px] bg-slate-900 text-white">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {opts.map((o, i) => (
            <SelectItem key={o} value={o}>
              {labels ? labels[i] : o}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
