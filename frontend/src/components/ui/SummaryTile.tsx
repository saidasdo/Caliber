import type { ReactNode } from "react";

// A compact, clickable "headline number + what it means" card: the glanceable unit this
// no-scroll redesign is built from. Click opens a Modal with the full detail elsewhere on the
// page; the tile itself never has to be more than a label, a number and a one-word status.
export function SummaryTile({
  label,
  value,
  sublabel,
  accent,
  onClick,
}: {
  label: string;
  value: ReactNode;
  sublabel?: ReactNode;
  accent?: "red" | "amber" | "ink";
  onClick: () => void;
}) {
  const valueColor = accent === "red" ? "text-red" : accent === "amber" ? "text-amber" : "text-ink";
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex h-full w-full flex-col items-start border border-line bg-paper px-2 py-1.5 text-left hover:bg-canvas"
    >
      <span className="text-12 uppercase tracking-wide text-mute">{label}</span>
      <span className={`tabular font-display stretch-semi-expanded text-28 ${valueColor}`}>{value}</span>
      {sublabel && <span className="text-12 text-mute">{sublabel}</span>}
    </button>
  );
}
