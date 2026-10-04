import type { FollowUpPipeline, KpiValue } from "../../lib/types";

// Tier 1, right third: what needs a person to follow up, with the change since the previous period.
export function FollowUpHealth({
  rcaOverdue,
  awaitingApproval,
  openFollowUps,
  onReviewEscalations,
}: {
  rcaOverdue: FollowUpPipeline["rca_process_overdue"];
  awaitingApproval: number;
  openFollowUps: KpiValue;
  onReviewEscalations: () => void;
}) {
  const delta = openFollowUps.value - openFollowUps.previous;
  const deltaText =
    delta === 0 ? "no change" : `${delta > 0 ? "up" : "down"} ${Math.abs(delta)} vs previous period`;
  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden border border-line bg-paper">
      <div className="shrink-0 border-b border-line px-2 py-1 text-12 font-semibold uppercase tracking-wide text-mute">
        Follow-up health
      </div>
      <dl className="min-h-0 flex-1 divide-y divide-line">
        <Row label="RCA overdue" value={rcaOverdue} line="RCA process past its due date" />
        <Row
          label="Awaiting approval"
          value={awaitingApproval}
          line={awaitingApproval === 0 ? "Nothing waiting on a plant manager" : "Proposed actions waiting for approval"}
        />
        <Row label="Open follow-ups" value={Math.round(openFollowUps.value)} line={deltaText} />
      </dl>
      <div className="shrink-0 px-2 pb-1.5 pt-1">
        <button
          type="button"
          onClick={onReviewEscalations}
          className="block w-full border border-ink bg-ink px-2 py-1 text-center text-13 font-medium text-white"
        >
          Review escalations
        </button>
      </div>
    </div>
  );
}

function Row({ label, value, line }: { label: string; value: number; line: string }) {
  return (
    <div className="flex items-center justify-between gap-2 px-2 py-0">
      <div className="min-w-0">
        <dt className="text-13 text-ink">{label}</dt>
        <dd className="truncate text-12 text-mute">{line}</dd>
      </div>
      <span className="tabular font-display text-20 font-bold leading-none text-ink">{value}</span>
    </div>
  );
}
