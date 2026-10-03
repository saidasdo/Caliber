import { useState } from "react";
import { Link } from "react-router-dom";
import { getActions, approveProposal, rejectProposal } from "../../lib/api";
import { useFetch } from "../../lib/useFetch";
import type { TrackedAction } from "../../lib/types";

// Phase 10 action flow step 2: plant manager approves (assigns PIC + due date) or rejects
// each action an engineer proposed for this plant's equipment.
export function PendingProposals({ plantCode, replayDate }: { plantCode: string; replayDate: string }) {
  const [refreshKey, setRefreshKey] = useState(0);
  const actions = useFetch(
    () => getActions({ replayDate, plantCode, status: "Proposed" }),
    [replayDate, plantCode, refreshKey],
  );
  const refetch = () => setRefreshKey((k) => k + 1);

  const rows = actions.status === "ready" ? actions.data.results : [];
  if (actions.status === "ready" && rows.length === 0) return null;

  return (
    <div className="border border-amber bg-paper">
      <div className="border-b border-line bg-amber px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-ink">
        Pending your approval
      </div>
      <ul className="divide-y divide-line">
        {rows.map((a) => (
          <ProposalRow key={a.id} action={a} onDone={refetch} />
        ))}
      </ul>
    </div>
  );
}

function ProposalRow({ action, onDone }: { action: TrackedAction; onDone: () => void }) {
  const [mode, setMode] = useState<"idle" | "approve" | "reject">("idle");
  const [pic, setPic] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submitApprove() {
    if (!pic.trim() || !dueDate) {
      setError("PIC and due date are required");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await approveProposal(action.id, { pic, due_date: dueDate });
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
      await rejectProposal(action.id, reason);
      onDone();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="px-2 py-1.5">
      <div className="flex items-baseline gap-1">
        {action.equipment_tag && (
          <Link to={`/equipment/${action.equipment_tag}`} className="tabular text-13 font-medium text-blue">
            {action.equipment_tag}
          </Link>
        )}
      </div>
      <p className="text-13 text-ink">{action.action_text}</p>

      {mode === "idle" && (
        <div className="mt-1 flex gap-1">
          <button
            type="button"
            onClick={() => setMode("approve")}
            className="border border-green px-1.5 py-0.5 text-12 font-medium text-green"
          >
            Approve
          </button>
          <button
            type="button"
            onClick={() => setMode("reject")}
            className="border border-line px-1.5 py-0.5 text-12 font-medium text-mute"
          >
            Reject
          </button>
        </div>
      )}

      {mode === "approve" && (
        <div className="mt-1 flex flex-col gap-1 border border-line bg-canvas p-1.5">
          <label className="text-12 text-mute">
            PIC
            <input
              type="text"
              value={pic}
              onChange={(e) => setPic(e.target.value)}
              className="mt-0.5 block w-full border border-line bg-paper px-1 py-0.5 text-13"
            />
          </label>
          <label className="text-12 text-mute">
            Due date
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="tabular mt-0.5 block w-full border border-line bg-paper px-1 py-0.5 text-13"
            />
          </label>
          {error && <p className="text-12 text-red">{error}</p>}
          <div className="flex gap-1">
            <button
              type="button"
              disabled={busy}
              onClick={submitApprove}
              className="bg-green px-1.5 py-0.5 text-12 font-medium text-white disabled:opacity-50"
            >
              Confirm approve
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

      {mode === "reject" && (
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
