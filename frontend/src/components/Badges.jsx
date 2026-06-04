import { POSITION_STYLES, TAG_STYLES, TAG_LABELS } from "../lib/api";

export function PositionBadge({ position }) {
  const cls = POSITION_STYLES[position] || POSITION_STYLES.DEF;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md border text-[11px] font-bold tracking-wide ${cls}`}
      data-testid={`position-badge-${position}`}
    >
      {position}
    </span>
  );
}

export function TagBadge({ tag, config }) {
  if (!tag || !TAG_STYLES[tag]) return null;

  // Elite tag uses sport accent color if config provided
  if (tag === "elite" && config) {
    return (
      <span
        className="inline-flex items-center px-2 py-0.5 rounded-md border text-[10px] font-bold tracking-wider"
        style={{
          background: config.hexAlpha,
          color: config.hexLight,
          borderColor: config.hexBorder,
        }}
        data-testid="tag-badge-elite"
      >
        ELITE
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md border text-[10px] font-bold tracking-wider ${TAG_STYLES[tag]}`}
      data-testid={`tag-badge-${tag}`}
    >
      {TAG_LABELS[tag]}
    </span>
  );
}

const INJURY_STYLES = {
  out: "bg-red-500/25 text-red-300 border-red-500/60",
  doubtful: "bg-red-500/15 text-red-300 border-red-500/40",
  questionable: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  probable: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  ir: "bg-red-500/30 text-red-200 border-red-500/70",
  pup: "bg-red-500/30 text-red-200 border-red-500/70",
  suspension: "bg-purple-500/20 text-purple-300 border-purple-500/50",
};

export function InjuryBadge({ status, short }) {
  if (!status) return null;
  const key = status.toLowerCase().replace(/[^a-z]/g, "");
  const cls = INJURY_STYLES[key] || INJURY_STYLES.questionable;
  const code = key === "out" ? "OUT"
    : key === "doubtful" ? "D"
    : key === "questionable" ? "Q"
    : key === "probable" ? "P"
    : key.startsWith("ir") || key === "pup" ? "IR"
    : status.slice(0, 3).toUpperCase();
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded-md border text-[10px] font-bold tracking-wider ${cls}`}
      title={short || status}
      data-testid={`injury-badge-${key}`}
    >
      {code}
    </span>
  );
}

const MATCHUP_STYLES = {
  easy: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  good: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  neutral: "bg-slate-700/30 text-slate-300 border-slate-600/50",
  hard: "bg-red-500/10 text-red-300 border-red-500/30",
  brutal: "bg-red-500/20 text-red-300 border-red-500/50",
};

const MATCHUP_DOT = {
  easy: "bg-emerald-400",
  good: "bg-emerald-500",
  neutral: "bg-slate-500",
  hard: "bg-red-500",
  brutal: "bg-red-400",
};

export function bucketForRank(rank) {
  if (!rank) return null;
  if (rank >= 27) return "easy";
  if (rank >= 20) return "good";
  if (rank >= 13) return "neutral";
  if (rank >= 6) return "hard";
  return "brutal";
}

const MATCHUP_LABEL = {
  easy: "EASY",
  good: "GOOD",
  neutral: "NEUTRAL",
  hard: "HARD",
  brutal: "TOUGH",
};

export function MatchupBadge({ rank, opp, position, fptsAllowed, source, compact }) {
  if (!rank) return null;
  const b = bucketForRank(rank);
  const cls = MATCHUP_STYLES[b];
  const dot = MATCHUP_DOT[b];
  const label = MATCHUP_LABEL[b];
  const tipParts = [];
  if (opp) tipParts.push(`vs ${opp}`);
  if (position) tipParts.push(`#${rank} D vs ${position}`);
  if (fptsAllowed) tipParts.push(`${fptsAllowed.toFixed(1)} FPts allowed/G`);
  if (source === "static") tipParts.push("(2024 baseline — refresh data for live)");
  const title = tipParts.join(" · ");

  if (compact) {
    return (
      <span
        className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md border text-[10px] font-bold ${cls}`}
        title={title}
        data-testid={`matchup-badge-${b}`}
      >
        <span className={`inline-block w-1.5 h-1.5 rounded-full ${dot}`} />
        #{rank}
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[10px] font-bold tracking-wider ${cls}`}
      title={title}
      data-testid={`matchup-badge-${b}`}
    >
      <span className={`inline-block w-1.5 h-1.5 rounded-full ${dot}`} />
      {label} #{rank}
    </span>
  );
}
