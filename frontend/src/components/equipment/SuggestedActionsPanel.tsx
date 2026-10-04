import { useState } from "react";
import {
  getActions,
  getEquipmentSuggestedActions,
  proposeAction,
  rejectAction,
} from "../../lib/api";
import { useFetch } from "../../lib/useFetch";
import { useAppState } from "../../state/AppStateContext";
import { canUseAction } from "../../roles/roleConfig";
import type { SuggestedAction, TrackedAction } from "../../lib/types";

// SPEC section 5.7: "Suggested actions from the diagnosis ... only become tracked actions
// after an engineer clicks Approve." Phase 10 splits that single step: the engineer here
// proposes (no PIC/due date), and a plant manager approves the proposal elsewhere (assigning
// PIC and due date) or rejects it. Declining a suggestion outright (never proposing it) still
// goes straight to Rejected, same as before phase 10.
export function SuggestedActionsPanel({
  tag,
  replayDate,
  onChange,
}: {
  tag: string;
  replayDate: string;
  // Told after a proposal or rejection, so the page can refresh anything that depends on it.
  onChange?: () => void;
}) {
  const [refreshKey, setRefreshKey] = useState(0);
  const suggested = useFetch(
    () => getEquipmentSuggestedActions(tag, replayDate),
    [tag, replayDate, refreshKey],
  );
  const existing = useFetch(
    () => getActions({ replayDate, equipmentTag: tag, source: "diagnosis_suggestion" }),
    [tag, replayDate, refreshKey],
  );

  const refetch = () => {
    setRefreshKey((k) => k + 1);
    onChange?.();
  };

  return (
    <div className="h-full border border-line bg-paper">
      <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        Suggested actions
      </div>
      {suggested.status !== "ready" || existing.status !== "ready" ? (
        <p className="px-2 py-2 text-13 text-mute">
          {suggested.status === "loading" ? "Loading..." : "Unavailable"}
        </p>
      ) : suggested.data.suggestions.length === 0 ? (
        <p className="px-2 py-2 text-13 text-mute">
          {suggested.data.confidence
            ? "No corrective CAPA or library action found for this rule."
            : "No confident diagnosis, nothing to suggest."}
        </p>
      ) : (
        <ul className="divide-y divide-line">
          {suggested.data.suggestions.map((s, i) => (
            <SuggestionRow
              key={i}
              tag={tag}
              suggestion={s}
              existingAction={existing.data.results.find(
                (a) =>
                  a.action_text === s.action_text &&
                  (s.source_capa_action_id === null || a.capa_action_id === s.source_capa_action_id),
              )}
              onDone={refetch}
            />
          ))}
        </ul>
      )}
      <p className="border-t border-line px-2 py-1.5 text-12 italic text-mute">
        Suggested, needs engineer review
      </p>
    </div>
  );
}

const STATUS_LABEL_CLASS: Record<string, string> = {
  Proposed: "border border-line text-mute",
  Open: "bg-line text-ink",
  "In progress": "bg-amber text-ink",
  Done: "bg-green text-white",
  Closed: "bg-ink text-white",
  Rejected: "bg-canvas text-mute",
};

function SuggestionRow({
  tag,
  suggestion,
  existingAction,
  onDone,
}: {
  tag: string;
  suggestion: SuggestedAction;
  existingAction: TrackedAction | undefined;
  onDone: () => void;
}) {
  const { role } = useAppState();
  const [mode, setMode] = useState<"idle" | "reject">("idle");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canPropose = canUseAction(role, "propose");

  if (existingAction) {
    return (
      <li className="px-2 py-1.5">
        <p className="text-13 text-ink">{suggestion.action_text}</p>
        <div className="mt-0.5 flex items-center gap-1.5 text-12">
          <span
            className={`rounded px-1 py-0.5 font-semibold ${STATUS_LABEL_CLASS[existingAction.status]}`}
          >
            {existingAction.status}
          </span>
          {existingAction.pic && <span className="text-mute">{existingAction.pic}</span>}
          {existingAction.due_date && <span className="tabular text-mute">{existingAction.due_date}</span>}
          {existingAction.reject_reason && (
            <span className="text-mute italic">"{existingAction.reject_reason}"</span>
          )}
        </div>
      </li>
    );
  }

  async function submitPropose() {
    setBusy(true);
    setError(null);
    try {
      await proposeAction({
        equipment_tag: tag,
        action_text: suggestion.action_text,
        source_capa_action_id: suggestion.source_capa_action_id,
      });
      onDone();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function submitReject() {
    if (!reason.trim()) {
      setError("A reason is required");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await rejectAction({
        equipment_tag: tag,
        action_text: suggestion.action_text,
        reason,
        source_capa_action_id: suggestion.source_capa_action_id,
      });
      setMode("idle");
      onDone();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="px-2 py-1.5">
      <p className="text-13 text-ink">{suggestion.action_text}</p>
      <p className="text-12 text-mute">
        {suggestion.source === "rca_capa" ? "From the equipment's own RCA" : "Generic action (library)"}
      </p>

      {!canPropose && (
        <p className="mt-1 text-12 text-mute">Not yet proposed by an engineer.</p>
      )}

      {canPropose && mode === "idle" && (
        <div className="mt-1 flex gap-1">
          <button
            type="button"
            disabled={busy}
            onClick={submitPropose}
            className="border border-green px-1.5 py-0.5 text-12 font-medium text-green disabled:opacity-50"
          >
            {busy ? "Proposing..." : "Propose"}
          </button>
          <button
            type="button"
            onClick={() => setMode("reject")}
            className="border border-line px-1.5 py-0.5 text-12 font-medium text-mute"
          >
            Reject
          </button>
          {error && <p className="text-12 text-red">{error}</p>}
        </div>
      )}

      {canPropose && mode === "reject" && (
        <div className="mt-1 flex flex-col gap-1 border border-line bg-canvas p-1.5">
          <label className="text-12 text-mute">
            Reason
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="mt-0.5 block w-full border border-line bg-paper px-1 py-0.5 text-13"
            />
          </label>
          {error && <p className="text-12 text-red">{error}</p>}
          <div className="flex gap-1">
            <button
              type="button"
              disabled={busy}
              onClick={submitReject}
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
    </li>
  );
}
