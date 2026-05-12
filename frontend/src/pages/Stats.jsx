import { useEffect, useMemo, useState } from "react";
import Navbar from "../components/Navbar";
import StatsTable from "../components/StatsTable";
import { api, extractPlayers } from "../lib/api";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
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
  const [loading, setLoading] = useState(false);

  // load teams
  useEffect(() => {
    api
      .get("/teams")
      .then((r) => setTeams(r.data || []))
      .catch(() => setTeams([]));
  }, []);

  const params = useMemo(
    () => ({
      position,
      team,
      season: Number(season),
      scoring,
      search: search || undefined,
      limit: 500,
    }),
    [position, team, season, scoring, search]
  );

  // load players
  useEffect(() => {
    setLoading(true);

    const t = setTimeout(() => {
      api
        .get("/players", { params })
        .then((r) => {
          const players = extractPlayers(r.data);
          setRows(players);
        })
        .catch((err) => {
          console.error("players error:", err);
          setRows([]);
        })
        .finally(() => setLoading(false));
    }, 150);

    return () => clearTimeout(t);
  }, [params]);

  const reset = () => {
    setPosition("ALL");
    setTeam("ALL");
    setSeason("2024");
    setScoring("half_ppr");
    setSearch("");
  };

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />

      {/* HEADER */}
      <div className="border-b border-slate-800 bg-slate-950/60">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <h1 className="text-white text-4xl font-bold">Player Stats</h1>
          <p className="text-slate-400 mt-2">
            NFL player database (live API)
          </p>
        </div>
      </div>

      {/* FILTERS */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex flex-wrap gap-3 items-end">

          {/* search */}
          <div className="flex-1 min-w-[220px]">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search player..."
              className="bg-slate-900 text-white border-slate-700"
            />
          </div>

          <Filter label="Position" value={position} set={setPosition} opts={POSITIONS} />
          <Filter label="Team" value={team} set={setTeam} opts={["ALL", ...teams]} />
          <Filter label="Season" value={season} set={setSeason} opts={SEASONS} />

          <Button onClick={reset} variant="outline">
            <X className="w-4 h-4 mr-1" /> Reset
          </Button>
        </div>

        <div className="mt-4 text-slate-400">
          {loading ? "Loading..." : `${rows.length} players`}
        </div>

        <StatsTable rows={rows} scoring={scoring} />
      </div>
    </div>
  );
}

function Filter({ label, value, set, opts }) {
  return (
    <div>
      <div className="text-xs text-slate-400 mb-1">{label}</div>
      <Select value={value} onValueChange={set}>
        <SelectTrigger className="w-[120px] bg-slate-900 text-white">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {opts.map((o) => (
            <SelectItem key={o} value={o}>
              {o}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
