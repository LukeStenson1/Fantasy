import AdUnit from "./AdUnit";

export default function Layout({ children }) {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Page content */}
      <div className="flex-1 min-w-0">
        {children}
      </div>

      {/* Bottom leaderboard ad — only shows when AdSense serves an ad */}
      <div className="w-full flex justify-center py-3 border-t border-slate-800/50 bg-slate-900/50">
        <AdUnit slot="6881020577" format="horizontal" className="w-full max-w-4xl min-h-0" />
      </div>
    </div>
  );
}
