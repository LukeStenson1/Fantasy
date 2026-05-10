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
