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

export function TagBadge({ tag }) {
  if (!tag || !TAG_STYLES[tag]) return null;
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
  const code = key === "out" ? "OUT" : key === "doubtful" ? "D" : key === "questionable" ? "Q" : key === "probable" ? "P" : key.startsWith("ir") || key === "pup" ? "IR" : status.slice(0, 3).toUpperCase();
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
