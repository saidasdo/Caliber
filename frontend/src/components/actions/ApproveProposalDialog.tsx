import { useState } from "react";
import { approveProposal } from "../../lib/api";
import type { TrackedAction } from "../../lib/types";
import { Modal } from "../ui/Modal";

// Plant manager's approval of an engineer's proposal (SPEC 5.7, phase 10): PIC and due date are required.
// Shared by the plant page (Pending your approval) and the Actions page (click a Proposed action).
export function ApproveProposalDialog({
  action,
  onClose,
  onApproved,
}: {
  action: TrackedAction;
  onClose: () => void;
  onApproved: () => void;
}) {
  const [pic, setPic] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!pic.trim() || !dueDate) {
      setError("PIC and due date are required");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await approveProposal(action.id, { pic: pic.trim(), due_date: dueDate });
      onApproved();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <Modal title="Approve proposed action" onClose={onClose}>
      <div className="flex flex-col gap-3 p-3">
        <div>
          <p className="text-12 uppercase tracking-wide text-mute">Equipment</p>
          <p className="tabular text-15 font-bold text-ink">{action.equipment_tag}</p>
        </div>
        <div>
          <p className="text-12 uppercase tracking-wide text-mute">Action</p>
          <p className="text-13 text-ink">{action.action_text}</p>
        </div>
        <label className="text-12 text-mute">
          Person in charge (PIC)
          <input
            type="text"
            autoFocus
            value={pic}
            onChange={(e) => setPic(e.target.value)}
            className="mt-1 block w-full border border-line bg-paper px-2 py-1.5 text-13 text-ink"
          />
        </label>
        <label className="text-12 text-mute">
          Due date
          <input
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            className="tabular mt-1 block w-full border border-line bg-paper px-2 py-1.5 text-13 text-ink"
          />
        </label>
        {error && <p className="text-12 text-red">{error}</p>}
        <div className="flex justify-end gap-2 border-t border-line pt-3">
          <button type="button" onClick={onClose} className="border border-line px-3 py-1.5 text-13 text-mute">
            Cancel
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={submit}
            className="bg-green px-3 py-1.5 text-13 font-medium text-white disabled:opacity-50"
          >
            Confirm approve
          </button>
        </div>
      </div>
    </Modal>
  );
}
