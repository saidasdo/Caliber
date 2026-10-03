import type { KpiBand as KpiBandData, KpiValue } from "../../lib/types";
import { formatHours } from "../../lib/format";
import { Money } from "../ui/Money";

interface Cell {
  label: string;
  kpi: KpiValue;
  format?: (v: number) => string;
  money?: boolean;
  alarm?: boolean;
}

// SPEC section 7: "Group related KPIs in one continuous band divided by vertical rules
// instead of separate cards." All five are lower-is-better, so a decrease is shown in green.
// SPEC 5.11: Loss is an all-plant aggregate, so only Executive sees it (Plant manager's
// visibility is scoped to one plant, which this number is not). "Equipment in ALARM" is the
// one cell that's actionable right now rather than historical, so its own number (not just
// the trend arrow) turns red when nonzero, the one visual signal in the band that says
// "look here first."
//
// Whether the Loss cell renders is decided by whether `data.loss_kusd` is present at all, not
// by re-deriving visibility from the current role: the server already decided and omitted the
// key for a role that can't see it (phase 10 money redaction), and that's the only source of
// truth that's guaranteed in sync with the data actually in hand (role can change a render
// before a refetch for the new role has resolved; the fetched object's own shape can't).
export function KpiBand({ data }: { data: KpiBandData }) {
  const cells: Cell[] = [
    { label: "Incidents", kpi: data.incidents, format: (v) => String(Math.round(v)) },
    { label: "Downtime", kpi: data.downtime_hours, format: formatHours },
    ...(data.loss_kusd ? [{ label: "Loss", kpi: data.loss_kusd, money: true }] : []),
    { label: "Open follow-ups", kpi: data.open_follow_ups, format: (v) => String(Math.round(v)) },
    {
      label: "Equipment in ALARM",
      kpi: data.equipment_in_alarm,
      format: (v) => String(Math.round(v)),
      alarm: true,
    },
  ];

  return (
    <div className="flex divide-x divide-line border border-line bg-paper">
      {cells.map((cell) => (
        <KpiCell key={cell.label} {...cell} />
      ))}
    </div>
  );
}

function KpiCell({ label, kpi, format, money, alarm }: Cell) {
  const delta = kpi.value - kpi.previous;
  const improved = delta < 0;
  const flat = delta === 0;
  const deltaColor = flat ? "text-mute" : improved ? "text-green" : "text-red";
  const arrow = flat ? "–" : improved ? "↓" : "↑";
  const isAlarming = alarm && kpi.value > 0;

  return (
    <div className="flex-1 px-2 py-1.5">
      <div className="text-12 uppercase tracking-wide text-mute">{label}</div>
      <div
        className={`tabular font-display stretch-semi-expanded text-28 ${isAlarming ? "text-red" : "text-ink"}`}
      >
        {money ? <Money kusd={kpi.value} /> : format!(kpi.value)}
      </div>
      <div className={`tabular text-12 font-medium ${deltaColor}`}>
        {arrow} {money ? <Money kusd={Math.abs(delta)} /> : format!(Math.abs(delta))} vs previous period
      </div>
    </div>
  );
}
