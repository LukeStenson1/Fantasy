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
  const { sport, setSport } = useSport();
  const navigate = useNavigate();

  const linkBase = "text-xs font-bold tracking-[0.15em] uppercase px-3 py-2 transition-colors";
  const linkClass = ({ isActive }) =>
    `${linkBase} ${isActive ? "text-emerald-400 border-b-2 border-emerald-400" : "text-slate-400 hover:text-white"}`;

  return (
    <header className="sticky top-0 z-30 bg-[#0a0e16]/95 backdrop-blur-md border-b border-slate-800" data-testid="navbar">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 group" data-testid="navbar-logo">
          <div className="relative w-9 h-9 flex items-center justify-center">
            <div className="absolute inset-0 bg-emerald-500 rotate-[3deg] group-hover:rotate-[6deg] transition-transform"></div>
            <div className="absolute inset-0 bg-slate-950 border border-emerald-500/60"></div>
            <span className="relative font-display font-black text-base text-emerald-400 tracking-tight">FL</span>
          </div>
          <div className="font-display font-black text-lg leading-none tracking-tight text-white">
            Fantasy<span className="text-emerald-400">Lab</span>
          </div>
        </Link>

        {/* Sport switcher */}
        <div className="flex items-center gap-1 bg-slate-900 border border-slate-700 rounded-lg p-1">
          {SPORTS.map((s) => (
            <button
              key={s.id}
              onClick={() => setSport(s.id)}
              className={`px-3 py-1 text-xs font-bold tracking-widest uppercase rounded-md transition-all ${
                sport === s.id
                  ? "bg-emerald-500 text-slate-950"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-1">
          <NavLink to="/lineup" className={linkClass} data-testid="nav-lineup">Lineup</NavLink>
          <NavLink to="/trades" className={linkClass} data-testid="nav-trades">Trades</NavLink>
          <NavLink to="/draft-board" className={linkClass}>Draft Board</NavLink>
          <NavLink to="/stats" className={linkClass} data-testid="nav-stats">Stats</NavLink>
          {user && user !== false && (
            <NavLink to="/my-rankings" className={linkClass} data-testid="nav-rankings">My Lab</NavLink>
          )}
        </nav>

        {/* Auth */}
        <div className="flex items-center gap-2">
          {user && user !== false ? (
            <>
              <span className="hidden sm:flex items-center gap-1.5 text-xs text-slate-400 font-mono-tab" data-testid="navbar-user-email">
                <UserIcon className="w-3.5 h-3.5" /> {user.email}
              </span>
              <Button variant="outline" size="sm" onClick={async () => { await logout(); navigate("/"); }}
                className="border-slate-700 bg-transparent hover:bg-slate-800 text-slate-300 hover:text-white" data-testid="navbar-logout-btn">
                <LogOut className="w-3.5 h-3.5 mr-1" /> Logout
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" onClick={() => navigate("/login")} className="text-slate-300 hover:text-white hover:bg-slate-800" data-testid="navbar-login-btn">
                Login
              </Button>
              <Button size="sm" onClick={() => navigate("/register")}
                className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold" data-testid="navbar-register-btn">
                Sign Up
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
