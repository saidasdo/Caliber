import type { HealthStatus, PriorityLabel } from "../../lib/types";

// SPEC section 7: "Status chips are solid fills (red with white text, amber with black text,
// green with white text)."
const HEALTH_STYLES: Record<NonNullable<HealthStatus>, string> = {
  TRIP: "bg-red text-white",
  ALARM: "bg-amber text-ink",
  NORMAL: "bg-green text-white",
};

const PRIORITY_STYLES: Record<PriorityLabel, string> = {
  Critical: "bg-red text-white",
  High: "bg-orange text-white",
  Medium: "bg-amber text-ink",
  Normal: "bg-line text-ink",
};

function ChipBase({ className, label }: { className: string; label: string }) {
  return (
    <span
      className={`inline-flex items-center rounded px-1 py-0.5 text-12 font-sans font-semibold leading-none tracking-wide ${className}`}
    >
      {label}
    </span>
  );
}

export function HealthChip({ status }: { status: HealthStatus }) {
  if (!status) {
    return <ChipBase className="bg-canvas text-mute" label="NO DATA" />;
  }
  return <ChipBase className={HEALTH_STYLES[status]} label={status} />;
}

export function PriorityChip({ label, inverted }: { label: PriorityLabel; inverted?: boolean }) {
  return (
    <ChipBase
      className={inverted ? "bg-white text-ink" : PRIORITY_STYLES[label]}
      label={label}
    />
  );
}
