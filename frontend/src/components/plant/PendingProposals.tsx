import { useState } from "react";
import { Link } from "react-router-dom";
import { getActions, rejectProposal } from "../../lib/api";
import { useFetch } from "../../lib/useFetch";
import type { TrackedAction } from "../../lib/types";
import { ApproveProposalDialog } from "../actions/ApproveProposalDialog";

// Phase 10 action flow step 2: plant manager approves (assigns PIC + due date) or rejects each action
// an engineer proposed for this plant's equipment. Approve opens a pop-up to enter PIC and due date.
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
  const [approveOpen, setApproveOpen] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

      {!rejecting && (
        <div className="mt-1 flex gap-1">
          <button
            type="button"
            onClick={() => setApproveOpen(true)}
            className="border border-green px-1.5 py-0.5 text-12 font-medium text-green"
          >
            Approve
          </button>
          <button
            type="button"
            onClick={() => setRejecting(true)}
            className="border border-line px-1.5 py-0.5 text-12 font-medium text-mute"
          >
            Reject
          </button>
        </div>
      )}

      {rejecting && (
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
              onClick={() => setRejecting(false)}
              className="border border-line px-1.5 py-0.5 text-12 text-mute"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {approveOpen && (
        <ApproveProposalDialog
          action={action}
          onClose={() => setApproveOpen(false)}
          onApproved={() => {
            setApproveOpen(false);
            onDone();
          }}
        />
      )}
    </li>
  );
}
