import type { ReactNode } from "react";

// Like SummaryTile, but for a metric that actually has a visual (a gauge, a trend line, a
// status bar): shows the real mini chart inline, not just the number it would otherwise
// reduce to. Click still opens the full version in a pop-up.
export function ChartTile({
  label,
  sublabel,
  onClick,
  children,
}: {
  label: string;
  sublabel?: ReactNode;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex h-full w-full flex-col items-stretch border border-line bg-paper px-2 py-1.5 text-left hover:bg-canvas"
    >
      <span className="shrink-0 text-12 uppercase tracking-wide text-mute">{label}</span>
      <div className="min-h-0 flex-1">{children}</div>
      {sublabel && <span className="shrink-0 text-12 text-mute">{sublabel}</span>}
    </button>
  );
}
