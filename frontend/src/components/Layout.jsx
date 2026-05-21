import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import AdUnit from "./AdUnit";

const NAV_LINKS = [
  { path: "/lineup", label: "LINEUP" },
  { path: "/trades", label: "TRADES" },
  { path: "/draft-board", label: "DRAFT BOARD" },
  { path: "/stats", label: "STATS" },
  { path: "/my-rankings", label: "MY LAB" },
];

export default function Layout({ children }) {
  const location = useLocation();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col">
      {/* Nav */}
      <nav className="border-b border-slate-800 bg-slate-950/90 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 flex items-center h-14 gap-8">
          <Link to="/" className="flex items-center gap-2 font-display font-bold text-white text-lg shrink-0">
            <div className="w-8 h-8 bg-emerald-500 rounded-sm flex items-center justify-center text-black font-bold text-sm">FL</div>
            <span><span className="text-white">Fantasy</span><span className="text-emerald-400">Lab</span></span>
          </Link>
          <div className="hidden md:flex items-center gap-6 flex-1">
            {NAV_LINKS.map((l) => (
              <Link
                key={l.path}
                to={l.path}
                className={`text-xs font-bold tracking-widest transition-colors ${
                  location.pathname === l.path
                    ? "text-emerald-400 border-b-2 border-emerald-400 pb-0.5"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {l.label}
              </Link>
            ))}
          </div>
          <div className="ml-auto flex items-center gap-3">
            {user ? (
              <>
                <span className="text-xs text-slate-400 hidden sm:block">{user.email}</span>
                <button
                  onClick={logout}
                  className="text-xs border border-slate-700 rounded px-3 py-1.5 text-slate-300 hover:bg-slate-800 flex items-center gap-1"
                >
                  Logout
                </button>
              </>
            ) : (
              <Link to="/login" className="text-xs border border-slate-700 rounded px-3 py-1.5 text-slate-300 hover:bg-slate-800">
                Login
              </Link>
            )}
          </div>
        </div>
      </nav>

      {/* Top leaderboard ad */}
      <div className="w-full flex justify-center py-2 bg-slate-900/50 border-b border-slate-800/50">
        <AdUnit slot="YOUR_TOP_AD_SLOT" format="horizontal" className="w-full max-w-4xl" />
      </div>

      {/* Main content with sidebar ads */}
      <div className="flex flex-1 max-w-7xl mx-auto w-full px-4 py-6 gap-6">
        {/* Left sidebar ad — hidden on mobile */}
        <aside className="hidden xl:flex flex-col gap-4 w-40 shrink-0 pt-2">
          <AdUnit slot="YOUR_LEFT_AD_SLOT" format="vertical" className="w-40" />
        </aside>

        {/* Page content */}
        <main className="flex-1 min-w-0">
          {children}
        </main>

        {/* Right sidebar ad — hidden on mobile */}
        <aside className="hidden xl:flex flex-col gap-4 w-40 shrink-0 pt-2">
          <AdUnit slot="YOUR_RIGHT_AD_SLOT" format="vertical" className="w-40" />
        </aside>
      </div>

      {/* Bottom leaderboard ad */}
      <div className="w-full flex justify-center py-4 bg-slate-900/50 border-t border-slate-800/50">
        <AdUnit slot="YOUR_BOTTOM_AD_SLOT" format="horizontal" className="w-full max-w-4xl" />
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-4 text-center text-xs text-slate-600">
        FantasyLab © {new Date().getFullYear()} — AI-powered fantasy football analytics
      </footer>
    </div>
  );
}
