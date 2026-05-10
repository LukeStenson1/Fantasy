import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Button } from "./ui/button";
import { LogOut, User as UserIcon } from "lucide-react";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const linkBase = "text-sm font-semibold tracking-wide uppercase px-3 py-2 transition-colors";
  const linkClass = ({ isActive }) =>
    `${linkBase} ${isActive ? "text-black border-b-2 border-black" : "text-slate-600 hover:text-black"}`;

  return (
    <header className="sticky top-0 z-30 bg-white border-b border-slate-200" data-testid="navbar">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
        <Link to="/" className="flex items-center gap-2" data-testid="navbar-logo">
          <div className="w-8 h-8 bg-black flex items-center justify-center text-white font-display font-black text-sm">
            FF
          </div>
          <div className="font-display font-black text-lg leading-none">
            FantasyRef<span className="text-emerald-600">.</span>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-1">
          <NavLink to="/stats" className={linkClass} data-testid="nav-stats">Stats</NavLink>
          <NavLink to="/sleepers-busts" className={linkClass} data-testid="nav-sleepers">Sleepers / Busts</NavLink>
          {user && user !== false && (
            <NavLink to="/my-rankings" className={linkClass} data-testid="nav-rankings">My Rankings</NavLink>
          )}
        </nav>

        <div className="flex items-center gap-2">
          {user && user !== false ? (
            <>
              <span className="hidden sm:flex items-center gap-1.5 text-sm text-slate-600" data-testid="navbar-user-email">
                <UserIcon className="w-4 h-4" /> {user.email}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={async () => { await logout(); navigate("/"); }}
                data-testid="navbar-logout-btn"
              >
                <LogOut className="w-4 h-4 mr-1" /> Logout
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" onClick={() => navigate("/login")} data-testid="navbar-login-btn">
                Login
              </Button>
              <Button size="sm" onClick={() => navigate("/register")} className="bg-black hover:bg-slate-800 text-white" data-testid="navbar-register-btn">
                Sign Up
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
