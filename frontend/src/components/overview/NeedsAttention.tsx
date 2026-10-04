import { useState } from "react";
import { Link } from "react-router-dom";
import type { ActionStatusLabel, PriorityLabel, PriorityRow } from "../../lib/types";
import { colors } from "../../styles/tokens";
import { Money } from "../ui/Money";
import { Modal } from "../ui/Modal";

// The left border carries the priority, as a 3 px solid rule. Colour is not used for whole cards.
const PRIORITY_RULE: Record<PriorityLabel, string> = {
  Critical: colors.red,
  High: colors.orange,
  Medium: colors.amber,
  Normal: colors.line,
};

// Solid chips for the action state. "No owner yet" is the one that needs someone to act first.
const ACTION_CHIP: Record<ActionStatusLabel, string> = {
  "No owner yet": "bg-red text-white",
  Proposed: "bg-blue text-white",
  Open: "bg-amber text-ink",
  "In progress": "bg-green text-white",
};

const TOP_N = 5;
const NEEDS_ATTENTION: PriorityLabel[] = ["Critical", "High", "Medium"];

// Every row uses the same columns and height, so urgency, margin, impact and status line up down the list.
const ROW_GRID = "grid grid-cols-[18px_minmax(0,1fr)_64px_128px_88px_104px] items-center gap-x-2 h-[54px] pr-2";

// Plain words for a row: what the machine is doing and how much health margin is left.
export function plainReason(row: PriorityRow): string {
  const margin = row.breakdown.health_margin_pct;
  const state =
    row.health_status === "TRIP" ? "Tripped" : row.health_status === "ALARM" ? "In alarm" : "Drifting toward alarm";
  const marginText = margin == null ? "" : `, ${Math.max(0, Math.round(margin))}% health margin left`;
  const suspected = row.diagnosis_rule_name ? `. Suspected ${row.diagnosis_rule_name.toLowerCase()}` : "";
  return `${state}${marginText}${suspected}`;
}

export function NeedsAttention({ rows }: { rows: PriorityRow[] }) {
  const [showAll, setShowAll] = useState(false);
  // Only machines labelled Medium or above need attention; Normal ones stay in "Show all".
  const attention = rows.filter((r) => NEEDS_ATTENTION.includes(r.priority_label));
  const shown = attention.slice(0, TOP_N);

  return (
    <div className="flex h-full min-h-0 flex-col border border-line bg-paper">
      <div className="flex shrink-0 items-center justify-between border-b border-line px-2 py-1.5">
        <span className="text-12 font-semibold uppercase tracking-wide text-mute">Needs attention now</span>
        <button type="button" onClick={() => setShowAll(true)} className="text-12 text-blue">
          Show all ({rows.length})
        </button>
      </div>

      {shown.length === 0 ? (
        <p className="px-2 py-3 text-13 text-mute">Nothing needs attention on this replay date.</p>
      ) : (
        <ul className="min-h-0 flex-1 divide-y divide-line overflow-hidden">
          {shown.map((row, i) => (
            <AttentionRow key={row.equipment_tag} row={row} rank={i + 1} />
          ))}
        </ul>
      )}

      {showAll && (
        <Modal title="Priority queue, all machines" onClose={() => setShowAll(false)} wide>
          <ul className="divide-y divide-line">
            {rows.map((row, i) => (
              <AttentionRow key={row.equipment_tag} row={row} rank={i + 1} />
            ))}
          </ul>
        </Modal>
      )}
    </div>
  );
}

// The bar shows the health margin (0 = at trip, 100 = at baseline), labelled, not the urgency.
function MarginBar({ margin }: { margin: number | null }) {
  if (margin == null) return <div />;
  const fill = Math.min(100, Math.max(0, margin));
  return (
    <div className="min-w-0">
      <div className="tabular truncate text-12 text-mute">Margin to trip {Math.round(margin)}%</div>
      <div className="mt-0.5 h-1.5 w-full bg-line">
        <div className="h-full bg-ink" style={{ width: `${fill}%` }} />
      </div>
    </div>
  );
}

// Urgency is the rank and the number shown. Criticality and the estimated impact only break exact ties.
function urgencyTitle(row: PriorityRow): string {
  const b = row.breakdown;
  const impact = row.estimated_impact?.value_kusd;
  return (
    `Urgency ${row.priority_score.toFixed(2)} = 0.6 x proximity ${b.proximity.toFixed(2)} ` +
    `+ 0.4 x alarm share ${b.alarm_share.toFixed(2)} ` +
    `(${b.parameters_past_alarm} of ${b.parameters_total} parameters past alarm). ` +
    `Criticality ${b.criticality ?? "not recorded"} and estimated impact ${impact != null ? Math.round(impact) + " k USD" : "-"} break ties only.`
  );
}

function AttentionRow({ row, rank }: { row: PriorityRow; rank: number }) {
  const status = row.action_status ?? "No owner yet";
  return (
    <li>
      <Link
        to={`/equipment/${row.equipment_tag}`}
        className={`${ROW_GRID} hover:bg-canvas`}
        style={{ borderLeft: `3px solid ${PRIORITY_RULE[row.priority_label]}`, paddingLeft: 8 }}
        title={urgencyTitle(row)}
      >
        <span className="tabular text-12 text-mute">#{rank}</span>
        <div className="min-w-0">
          <div className="flex min-w-0 items-baseline gap-2 whitespace-nowrap">
            <span className="tabular font-display text-15 font-bold text-ink">{row.equipment_tag}</span>
            <span className="text-12 text-mute">{row.plant_code}</span>
            {row.equipment_type && <span className="min-w-0 truncate text-12 text-mute">{row.equipment_type}</span>}
          </div>
          <div className="truncate text-13 text-ink">{plainReason(row)}</div>
        </div>
        <div className="text-right">
          <div className="text-12 text-mute">Urgency</div>
          <div className="tabular font-display text-28 font-bold leading-none text-ink">{row.priority_score.toFixed(2)}</div>
        </div>
        <MarginBar margin={row.breakdown.health_margin_pct} />
        <div className="tabular text-right text-13 text-ink">
          {row.estimated_impact?.value_kusd != null ? (
            <Money kusd={row.estimated_impact.value_kusd} fallback="-" />
          ) : (
            <span className="text-mute">-</span>
          )}
        </div>
        <span className={`px-1.5 py-0.5 text-center text-12 font-medium ${ACTION_CHIP[status]}`}>{status}</span>
      </Link>
    </li>
  );
}
