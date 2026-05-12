import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { api } from "../lib/api";
import AdSlot from "../components/AdSlot";
import { PositionBadge } from "../components/Badges";

/* ---------------- SAFE NORMALIZER ---------------- */
const safeArray = (v) =>
  Array.isArray(v) ? v : v?.items || v?.data || [];

const safeObject = (v, fallback = {}) =>
  v && typeof v === "object" ? v : fallback;

export default function Home() {
  const [summary, setSummary] = useState({
    total_players: 0,
    data_seasons: [],
    last_refresh: null,
  });

  const [movers, setMovers] = useState({
    sleepers: [],
    busts: [],
    breakouts: [],
    elites: [],
  });

  const [matchups, setMatchups] = useState(null);

  useEffect(() => {
    // SUMMARY
    api.get("/stats/summary")
      .then((r) => setSummary(safeObject(r.data)))
      .catch((err) => console.error("summary error", err));

    // MOVERS
    api.get("/sleepers-busts", { params: { scoring: "half_ppr" } })
      .then((r) => setMovers(safeObject(r.data)))
      .catch((err) => console.error("movers error", err));

    // MATCHUPS
    api.get("/matchups/this-week")
      .then((r) => setMatchups(safeObject(r.data)))
      .catch((err) => console.error("matchups error", err));
  }, []);

  const byPos =
    matchups?.by_position ||
    matchups?.byPosition ||
    matchups?.data?.by_position ||
    {};

  return (
    <div className="min-h-screen bg-[#0a0e16]">
      <Navbar />

      {/* HERO (unchanged) */}
      <section className="relative overflow-hidden border-b border-slate-800">
        <div className="absolute inset-0 bg-grid opacity-30" />
        <div className="relative max-w-7xl mx-auto px-4 py-20">
          <h1 className="text-white text-4xl font-bold">
            FantasyLab Dashboard
          </h1>
        </div>
      </section>

      {/* MATCHUPS */}
      {Object.keys(byPos).length > 0 && (
        <section className="max-w-7xl mx-auto px-4 py-10">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {["RB", "WR", "QB", "TE"].map((pos) => (
              <MatchupColumn
                key={pos}
                pos={pos}
                data={byPos[pos] || { soft: [], tough: [] }}
              />
            ))}
          </div>
        </section>
      )}

      {/* MOVERS */}
      <section className="max-w-7xl mx-auto px-4 py-10 grid grid-cols-1 lg:grid-cols-2 gap-4">
        <MoverList
          title="Breakout Candidates"
          players={movers?.breakouts}
        />
        <MoverList
          title="Bust Risks"
          players={movers?.busts}
        />
      </section>

      <section className="max-w-7xl mx-auto px-4 pb-20">
        <AdSlot slot="home-bottom" />
      </section>
    </div>
  );
}

/* ---------------- SAFE COMPONENTS ---------------- */

function MatchupColumn({ pos, data }) {
  const soft = data?.soft || [];
  const tough = data?.tough || [];

  return (
    <div className="bg-slate-950/60 border border-slate-800 rounded-md p-3">
      <div className="flex items-center gap-2 mb-2">
        <PositionBadge position={pos} />
        <span className="text-white font-bold">{pos}</span>
      </div>

      <div className="text-xs text-emerald-400 mb-1">Smash</div>
      {soft.slice(0, 3).map((r, i) => (
        <div key={i} className="text-xs text-white">
          {r.offense_team || "—"}
        </div>
      ))}

      <div className="text-xs text-red-400 mt-2 mb-1">Avoid</div>
      {tough.slice(0, 3).map((r, i) => (
        <div key={i} className="text-xs text-white">
          {r.offense_team || "—"}
        </div>
      ))}
    </div>
  );
}

function MoverList({ title, players = [] }) {
  const safePlayers = Array.isArray(players) ? players : [];

  return (
    <div className="bg-slate-950/60 border border-slate-800 rounded-md">
      <div className="p-3 border-b border-slate-800 text-white font-bold">
        {title}
      </div>

      <div>
        {safePlayers.slice(0, 8).map((p) => (
          <div key={p.id} className="p-3 text-white text-sm">
            {p.name}
          </div>
        ))}

        {safePlayers.length === 0 && (
          <div className="p-4 text-slate-500 text-sm">
            No players yet.
          </div>
        )}
      </div>
    </div>
  );
}
