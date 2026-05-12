{/* Self-learning stats */}
<div className="bg-slate-950/60 border border-emerald-500/20 rounded-md p-5" data-testid="predstats-panel">
  <div className="flex items-center gap-2 mb-3">
    <Brain className="w-5 h-5 text-emerald-400" />
    <h2 className="font-display font-bold text-lg text-white">Self-Learning Accuracy</h2>
    <span className="ml-auto text-xs text-slate-500 font-mono-tab">
      {predStats ? `${predStats.settled}/${predStats.total} predictions settled` : "loading…"}
    </span>
  </div>

  {(!predStats || Object.keys(predStats?.by_position || {}).length === 0) && (
    <p className="text-sm text-slate-400">
      The Lab logs every Lineup AI suggestion as a prediction. Once new seasonal data publishes (or an admin runs{" "}
      <code className="text-emerald-300 text-xs">POST /api/predictions/settle</code>), accuracy by position will appear here and feed back into future suggestions.
    </p>
  )}

  {predStats && Object.keys(predStats?.by_position || {}).length > 0 && (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
      {Object.entries(predStats?.by_position || {}).map(([pos, s]) => {
        const mae = typeof s?.mae === "number" ? s.mae.toFixed(1) : "—";
        const bias =
          typeof s?.bias === "number"
            ? `${s.bias > 0 ? "+" : ""}${s.bias.toFixed(1)}`
            : "—";
        const n = s?.n ?? 0;

        return (
          <div key={pos} className="border border-slate-800 rounded-md p-3 bg-slate-950/40">
            <div className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">
              {pos}
            </div>

            <div className="font-mono-tab text-white">
              <span className="font-bold">{mae}</span> MAE
            </div>

            <div className="text-xs text-slate-500 font-mono-tab">
              bias {bias} · n={n}
            </div>
          </div>
        );
      })}
    </div>
  )}
</div>
