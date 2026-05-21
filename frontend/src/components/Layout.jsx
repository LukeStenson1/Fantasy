import AdUnit from "./AdUnit";

export default function Layout({ children }) {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Top leaderboard ad */}
      <div className="w-full flex justify-center py-1 bg-slate-900/50 border-b border-slate-800/50">
        <AdUnit slot="7472733276" format="horizontal" className="w-full max-w-4xl" />
      </div>

      {/* Main content with sidebar ads */}
      <div className="flex flex-1 w-full gap-0">
        {/* Left sidebar ad — hidden on mobile/tablet */}
        <aside className="hidden xl:flex flex-col w-36 shrink-0 pt-16 px-1 bg-transparent">
          <AdUnit slot="8063760212" format="vertical" className="w-36 sticky top-16" />
        </aside>

        {/* Page content — unchanged */}
        <div className="flex-1 min-w-0">
          {children}
        </div>

        {/* Right sidebar ad — hidden on mobile/tablet */}
        <aside className="hidden xl:flex flex-col w-36 shrink-0 pt-16 px-1 bg-transparent">
          <AdUnit slot="4226559777" format="vertical" className="w-36 sticky top-16" />
        </aside>
      </div>

      {/* Bottom leaderboard ad */}
      <div className="w-full flex justify-center py-3 bg-slate-900/50 border-t border-slate-800/50">
        <AdUnit slot="6881020577" format="horizontal" className="w-full max-w-4xl" />
      </div>
    </div>
  );
}
