import { useState } from "react";
import { useAppState } from "../../state/AppStateContext";
import { getDiagnosisReview, postDiagnosisReview } from "../../lib/api";
import { useFetch } from "../../lib/useFetch";
import { BulletBar } from "../ui/BulletBar";
import type { Diagnosis, DiagnosisCondition } from "../../lib/types";

const CONFIDENCE_CLASS: Record<string, string> = {
  High: "bg-green text-white",
  Medium: "bg-amber text-ink",
  Low: "bg-line text-ink",
};

const TREND_ARROW: Record<string, string> = { rising: "↑", falling: "↓", flat: "–" };

// A bullet graph (value position against its limit, ISA-101 style) instead of a text row of
// "value / limit / trend / pass" columns: the point is to see at a glance how close to the
// line a parameter is, not to read four numbers per condition.
function ConditionRow({ condition: c }: { condition: DiagnosisCondition }) {
  return (
    <li className="px-2 py-1.5">
      <div className="flex items-center justify-between text-12">
        <span className="text-ink">{c.parameter}</span>
        <span className="tabular text-mute">
          {c.trend && <span className="mr-1">{TREND_ARROW[c.trend]}</span>}
          {c.value ?? "-"}
          {c.limit != null && <span className="text-mute"> / {c.limit}</span>}
        </span>
      </div>
      <div className="mt-0.5">
        <BulletBar value={c.value} limit={c.limit} danger={c.pass} />
      </div>
    </li>
  );
}

// SPEC section 5.5: "Show every condition as a row: parameter, value, limit, trend, pass/fail.
// Label the panel 'Root cause hint' with the note 'Suggested, needs engineer review'."
// Phase 10 action flow step 1: engineer confirms or rejects this diagnosis before proposing
// an action, so the review control is an engineer-only extra at the bottom of this panel.
export function DiagnosisPanel({
  diagnosis,
  tag,
  replayDate,
}: {
  diagnosis: Diagnosis;
  tag?: string;
  replayDate?: string;
}) {
  return (
    <div className="h-full border border-line bg-paper">
      <div className="flex items-center justify-between border-b border-line px-2 py-1.5">
        <span className="text-12 font-semibold uppercase tracking-wide text-mute">
          Root cause hint
        </span>
        {diagnosis.confidence && (
          <span
            className={`rounded px-1 py-0.5 text-12 font-semibold ${CONFIDENCE_CLASS[diagnosis.confidence]}`}
          >
            {diagnosis.confidence}
          </span>
        )}
      </div>

      {diagnosis.rule_name ? (
        <>
          <div className="flex items-baseline justify-between px-2 pt-1.5">
            <span className="text-15 font-medium text-ink">{diagnosis.rule_name}</span>
            <span className="tabular text-20 font-display font-bold text-ink">
              {diagnosis.passes}
              <span className="text-13 font-normal text-mute">/{diagnosis.of}</span>
            </span>
          </div>
          <div className="px-2 pb-1 text-12 text-mute">conditions met</div>
          <ul className="divide-y divide-line">
            {diagnosis.conditions.map((c, i) => (
              <ConditionRow key={i} condition={c} />
            ))}
          </ul>
        </>
      ) : (
        <p className="px-2 py-2 text-13 text-mute">
          {diagnosis.reason ?? "No confident root cause hint for this replay date."}
        </p>
      )}

      <p className="border-t border-line px-2 py-1.5 text-12 italic text-mute">{diagnosis.note}</p>
      {tag && replayDate && diagnosis.rule_name && (
        <DiagnosisReviewControl tag={tag} replayDate={replayDate} ruleName={diagnosis.rule_name} />
      )}
    </div>
  );
}

function DiagnosisReviewControl({
  tag,
  replayDate,
  ruleName,
}: {
  tag: string;
  replayDate: string;
  ruleName: string;
}) {
  const { role } = useAppState();
  const [refreshKey, setRefreshKey] = useState(0);
  const review = useFetch(() => getDiagnosisReview(tag), [tag, refreshKey]);
  const [mode, setMode] = useState<"idle" | "reject">("idle");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  if (role !== "Engineer") return null;

  const current = review.status === "ready" ? review.data : null;
  const upToDate = current && current.rule_name === ruleName;

  async function confirm() {
    setBusy(true);
    try {
      await postDiagnosisReview(tag, { status: "confirmed", replay_date: replayDate });
      setRefreshKey((k) => k + 1);
    } finally {
      setBusy(false);
    }
  }

  async function reject() {
    if (!reason.trim()) return;
    setBusy(true);
    try {
      await postDiagnosisReview(tag, { status: "rejected", reason, replay_date: replayDate });
      setMode("idle");
      setReason("");
      setRefreshKey((k) => k + 1);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border-t border-line p-2">
      {upToDate ? (
        <p className="text-13 text-ink">
          You {current!.status} this diagnosis.
          {current!.reason && <span className="text-mute italic"> "{current!.reason}"</span>}
        </p>
      ) : mode === "idle" ? (
        <div className="flex gap-1">
          <button
            type="button"
            disabled={busy}
            onClick={confirm}
            className="border border-green px-1.5 py-0.5 text-12 font-medium text-green disabled:opacity-50"
          >
            Confirm diagnosis
          </button>
          <button
            type="button"
            onClick={() => setMode("reject")}
            className="border border-line px-1.5 py-0.5 text-12 font-medium text-mute"
          >
            Reject diagnosis
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-1">
          <label className="text-12 text-mute">
            Reason
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="mt-0.5 block w-full border border-line bg-paper px-1 py-0.5 text-13"
            />
          </label>
          <div className="flex gap-1">
            <button
              type="button"
              disabled={busy}
              onClick={reject}
              className="bg-ink px-1.5 py-0.5 text-12 font-medium text-white disabled:opacity-50"
            >
              Confirm reject
            </button>
            <button
              type="button"
              onClick={() => setMode("idle")}
              className="border border-line px-1.5 py-0.5 text-12 text-mute"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
