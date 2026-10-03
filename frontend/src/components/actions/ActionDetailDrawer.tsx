import { useState } from "react";
import { Link } from "react-router-dom";
import {
  updateActionStatus,
  closeAction,
  escalateAction,
  commentOnAction,
  getActionComments,
} from "../../lib/api";
import { useFetch } from "../../lib/useFetch";
import { useAppState } from "../../state/AppStateContext";
import type { ActionStatus, TrackedAction } from "../../lib/types";

const ENGINEER_STATUSES: ActionStatus[] = ["In progress", "Done"];

// SPEC section 7: "detail drawer on the right." Phase 10 section 4: "buttons a role cannot
// use are not shown": progress buttons are Engineer's, Close is Plant manager's (only once
// Done), Escalate and Comment are Executive's (Escalate only once overdue).
export function ActionDetailDrawer({
  action,
  onClose,
  onChanged,
}: {
  action: TrackedAction;
  onClose: () => void;
  onChanged: () => void;
}) {
  const { role, replayDate } = useAppState();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [commentText, setCommentText] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const comments = useFetch(() => getActionComments(action.id), [action.id, refreshKey]);

  async function run(key: string, fn: () => Promise<unknown>) {
    setBusy(key);
    setError(null);
    try {
      await fn();
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-10 bg-ink/20" onClick={onClose} />
      <aside className="fixed inset-y-0 right-0 z-20 w-[360px] overflow-y-auto border-l border-line bg-paper shadow-popover">
        <div className="flex items-center justify-between border-b border-line px-2 py-1.5">
          <span className="text-12 font-semibold uppercase tracking-wide text-mute">
            Action detail
          </span>
          <button type="button" onClick={onClose} className="text-13 text-mute hover:text-ink">
            Close
          </button>
        </div>

        <div className="p-2">
          {action.equipment_tag && (
            <Link to={`/equipment/${action.equipment_tag}`} className="tabular text-15 font-bold text-blue">
              {action.equipment_tag}
            </Link>
          )}
          <p className="mt-1 text-13 text-ink">{action.action_text}</p>

          <dl className="mt-2 divide-y divide-line border-y border-line text-13">
            <Row label="Status" value={action.status} />
            <Row label="Source" value={action.source} />
            <Row label="PIC" value={action.pic ?? "-"} />
            <Row label="Due date" value={action.due_date ?? "-"} />
            <Row label="Created" value={action.created_at?.slice(0, 19) ?? "-"} />
            <Row label="Approved" value={action.approved_at?.slice(0, 19) ?? "-"} />
            {action.progress_note && <Row label="Progress note" value={action.progress_note} />}
            {action.reject_reason && <Row label="Reject reason" value={action.reject_reason} />}
            {action.overdue_days != null && <Row label="Overdue" value={`${action.overdue_days} days`} />}
            {action.escalated === 1 && <Row label="Escalated" value="Yes" />}
          </dl>

          {role === "Engineer" && (action.status === "Open" || action.status === "In progress") && (
            <div className="mt-2">
              <div className="text-12 font-semibold uppercase tracking-wide text-mute">
                Update progress
              </div>
              <div className="mt-1 flex flex-wrap gap-1">
                {ENGINEER_STATUSES.map((s) => (
                  <button
                    key={s}
                    type="button"
                    disabled={busy !== null || action.status === s}
                    onClick={() => run(s, () => updateActionStatus(action.id, s, role))}
                    className={`border px-1.5 py-0.5 text-12 font-medium disabled:opacity-40 ${
                      action.status === s ? "border-ink bg-ink text-white" : "border-line text-ink hover:bg-canvas"
                    }`}
                  >
                    {busy === s ? "Saving..." : s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {role === "Plant manager" && action.status === "Done" && (
            <div className="mt-2">
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => run("close", () => closeAction(action.id))}
                className="border border-ink bg-ink px-1.5 py-0.5 text-12 font-medium text-white disabled:opacity-40"
              >
                {busy === "close" ? "Closing..." : "Close"}
              </button>
            </div>
          )}

          {role === "Executive" && (
            <div className="mt-2">
              {action.overdue_days != null && action.escalated !== 1 && (
                <button
                  type="button"
                  disabled={busy !== null}
                  onClick={() => run("escalate", () => escalateAction(action.id, replayDate))}
                  className="border border-red px-1.5 py-0.5 text-12 font-medium text-red disabled:opacity-40"
                >
                  {busy === "escalate" ? "Escalating..." : "Escalate"}
                </button>
              )}
              <div className="mt-2">
                <div className="text-12 font-semibold uppercase tracking-wide text-mute">Comments</div>
                <ul className="mt-1 space-y-1">
                  {comments.status === "ready" &&
                    comments.data.results.map((c) => (
                      <li key={c.id} className="text-13 text-ink">
                        {c.comment}
                        <span className="ml-1 text-12 text-mute">{c.ts.slice(0, 10)}</span>
                      </li>
                    ))}
                </ul>
                <div className="mt-1 flex gap-1">
                  <input
                    type="text"
                    value={commentText}
                    onChange={(e) => setCommentText(e.target.value)}
                    placeholder="Add a comment"
                    className="flex-1 border border-line bg-paper px-1 py-0.5 text-13"
                  />
                  <button
                    type="button"
                    disabled={busy !== null || !commentText.trim()}
                    onClick={async () => {
                      await run("comment", () => commentOnAction(action.id, commentText));
                      setCommentText("");
                      setRefreshKey((k) => k + 1);
                    }}
                    className="border border-line px-1.5 py-0.5 text-12 text-ink disabled:opacity-40"
                  >
                    Add
                  </button>
                </div>
              </div>
            </div>
          )}

          {error && <p className="mt-1 text-12 text-red">{error}</p>}
        </div>
      </aside>
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-2 py-1">
      <dt className="text-mute">{label}</dt>
      <dd className="text-right text-ink">{value}</dd>
    </div>
  );
}
