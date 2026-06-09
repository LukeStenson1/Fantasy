import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useSport } from "../contexts/SportContext";
import { SPORT_CONFIG } from "../contexts/SportContext";
import { Button } from "./ui/button";
import { LogOut, User as UserIcon } from "lucide-react";

const SPORTS = [
  { id: "nfl", label: "NFL" },
  { id: "nba", label: "NBA" },
  { id: "mlb", label: "MLB" },
];

export default function Navbar() {
  const { user, logout } = useAuth();
  const { sport, setSport, config } = useSport();
  const navigate = useNavigate();

  const linkBase = "text-xs font-bold tracking-[0.15em] uppercase px-3 py-2 transition-colors";
  const linkClass = ({ isActive }) =>
    isActive
      ? `${linkBase} border-b-2`
      : `${linkBase} text-slate-400 hover:text-white`;

  const activeLinkStyle = { color: config.hex, borderColor: config.hex };

  return (
    <header className="sticky top-0 z-30 bg-[#0a0e16]/95 backdrop-blur-md border-b border-slate-800" data-testid="navbar">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">

        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 group" data-testid="navbar-logo">
          <div className="relative w-9 h-9 flex items-center justify-center">
            <div
              className="absolute inset-0 rotate-[3deg] group-hover:rotate-[6deg] transition-transform"
              style={{ backgroundColor: config.hex }}
            />
            <div
              className="absolute inset-0 bg-slate-950 border"
              style={{ borderColor: `${config.hex}99` }}
            />
            <span
              className="relative font-display font-black text-base tracking-tight"
              style={{ color: config.hex }}
            >
              FL
            </span>
          </div>
          <div className="font-display font-black text-lg leading-none tracking-tight text-white">
            Fantasy<span style={{ color: config.hex }}>Lab</span>
          </div>
        </Link>

        {/* Sport switcher */}
        <div className="flex items-center gap-1 bg-slate-900 border border-slate-700 rounded-lg p-1">
          {SPORTS.map((s) => (
            <button
              key={s.id}
              onClick={() => setSport(s.id)}
              className="px-3 py-1 text-xs font-bold tracking-widest uppercase rounded-md transition-all"
              style={sport === s.id
                ? { backgroundColor: SPORT_CONFIG[s.id].hex, color: "#0a0e16" }
                : { color: "#94a3b8" }}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-1">
          {[
            { to: "/lineup", label: "Lineup", testid: "nav-lineup" },
            { to: "/trades", label: "Trades", testid: "nav-trades" },
            { to: "/draft-board", label: "Draft Board" },
            { to: "/stats", label: "Stats", testid: "nav-stats" },
            ...(user && user !== false ? [{ to: "/my-rankings", label: "My Lab", testid: "nav-rankings" }] : []),
          ].map(({ to, label, testid }) => (
            <NavLink
              key={to}
              to={to}
              data-testid={testid}
              className={({ isActive }) =>
                isActive
                  ? `${linkBase} border-b-2`
                  : `${linkBase} text-slate-400 hover:text-white`
              }
              style={({ isActive }) => isActive ? activeLinkStyle : {}}
            >
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Auth */}
        <div className="flex items-center gap-2">
          {user && user !== false ? (
            <>
              <span className="hidden sm:flex items-center gap-1.5 text-xs text-slate-400 font-mono-tab"
                data-testid="navbar-user-email">
                <UserIcon className="w-3.5 h-3.5" /> {user.email}
              </span>
              <Button variant="outline" size="sm"
                onClick={async () => { await logout(); navigate("/"); }}
                className="border-slate-700 bg-transparent hover:bg-slate-800 text-slate-300 hover:text-white"
                data-testid="navbar-logout-btn">
                <LogOut className="w-3.5 h-3.5 mr-1" /> Logout
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm"
                onClick={() => navigate("/login")}
                className="text-slate-300 hover:text-white hover:bg-slate-800"
                data-testid="navbar-login-btn">
                Login
              </Button>
              <Button size="sm"
                onClick={() => navigate("/register")}
                className="font-semibold text-slate-950"
                style={{ backgroundColor: config.hex }}
                data-testid="navbar-register-btn">
                Sign Up
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
