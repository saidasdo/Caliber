import { useState } from "react";
import { resetDemoData } from "../../lib/api";

// SPEC section 10 phase 9: "'Reset demo data' button." Discards any approve/reject/status
// changes made during the session by re-running the full ingestion pipeline, so it asks for
// confirmation first (a destructive, hard-to-reverse action from the user's point of view).
export function ResetDemoDataButton() {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      const result = await resetDemoData();
      if (result.status !== "ok") {
        throw new Error("Reset completed but some acceptance checks failed.");
      }
      window.location.reload();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        title="Reset demo data"
        aria-label="Reset demo data"
        onClick={() => setOpen((o) => !o)}
        className={`flex h-4 w-4 items-center justify-center rounded ${
          open ? "bg-white/10 text-white" : "text-mute hover:text-white"
        }`}
      >
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
          <circle cx="12" cy="12" r="3" />
          <path d="M19 12a7 7 0 00-.2-1.6l2-1.6-2-3.4-2.4 1a7 7 0 00-2.8-1.6L13 2h-4l-.6 2.8a7 7 0 00-2.8 1.6l-2.4-1-2 3.4 2 1.6A7 7 0 003 12a7 7 0 00.2 1.6l-2 1.6 2 3.4 2.4-1a7 7 0 002.8 1.6L9 22h4l.6-2.8a7 7 0 002.8-1.6l2.4 1 2-3.4-2-1.6A7 7 0 0019 12z" />
        </svg>
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute bottom-0 left-[56px] z-20 w-[260px] border border-line bg-paper p-2 shadow-popover">
            <div className="text-13 font-semibold text-ink">Reset demo data</div>
            <p className="mt-1 text-12 text-mute">
              Re-runs ingestion from data/raw. Discards any approved or rejected actions and
              status changes made this session. Cannot be undone.
            </p>
            {error && <p className="mt-1 text-12 text-red">{error}</p>}
            <div className="mt-2 flex gap-1">
              <button
                type="button"
                disabled={busy}
                onClick={confirm}
                className="bg-red px-1.5 py-0.5 text-12 font-medium text-white disabled:opacity-50"
              >
                {busy ? "Resetting..." : "Reset"}
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => setOpen(false)}
                className="border border-line px-1.5 py-0.5 text-12 text-ink"
              >
                Cancel
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
