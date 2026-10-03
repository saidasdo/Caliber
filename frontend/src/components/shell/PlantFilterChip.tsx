import { Link } from "react-router-dom";

// Shown on the global Diagnosis/Actions/Backtest pages when they were reached from inside a
// plant or equipment page (PageTabs attaches ?plant=), so it's obvious the list isn't the
// full all-plants view and there's a one-click way back to it.
export function PlantFilterChip({ plantCode, clearTo }: { plantCode: string; clearTo: string }) {
  return (
    <div className="flex items-center gap-1 self-start border border-line bg-canvas px-1.5 py-0.5 text-12 text-mute">
      Filtered to <span className="font-semibold text-ink">{plantCode}</span>
      <Link to={clearTo} aria-label="Clear plant filter" className="text-mute hover:text-ink">
        &times;
      </Link>
    </div>
  );
}
