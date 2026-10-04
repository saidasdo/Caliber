import { useState } from "react";
import type { PlantDetail } from "../../lib/types";
import { formatDate } from "../../lib/format";
import { Money } from "../ui/Money";
import { Modal } from "../ui/Modal";
import { StatusAsOfNote } from "../ui/StatusAsOfNote";

// SPEC section 5.2: "incident history". A dashboard panel is supposed to be readable at a
// glance; a 50-row table dumped inline is the opposite of that, and on the no-scroll plant
// page an inline expand would just push other panels off screen, so this is a summary tile
// that opens the full table in a pop-up instead.
export function IncidentHistoryTable({
  rows,
  plantCode,
}: {
  rows: PlantDetail["incident_history"];
  plantCode: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex h-full w-full flex-col items-start border border-line bg-paper px-2 py-1.5 text-left hover:bg-canvas"
      >
        <span className="text-12 uppercase tracking-wide text-mute">Incident history</span>
        <span className="tabular font-display stretch-semi-expanded text-28 text-ink">{rows.length}</span>
        <span className="text-12 text-mute">
          {rows.length === 0 ? "none" : `most recent ${formatDate(rows[0].date_of_occur)}`}
        </span>
      </button>

      {open && (
        <Modal title="Incident history" onClose={() => setOpen(false)} wide>
          <StatusAsOfNote />
          <table className="w-full text-13">
            <thead>
              <tr className="border-b border-line text-left text-12 text-mute">
                <th className="px-2 py-1 font-medium">Date</th>
                <th className="px-2 py-1 font-medium">Tag</th>
                <th className="px-2 py-1 font-medium">Title</th>
                <th className="px-2 py-1 font-medium">Status</th>
                <th className="px-2 py-1 font-medium text-right">Downtime</th>
                <th className="px-2 py-1 font-medium text-right">Loss</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.slice(0, 50).map((row) => (
                <tr key={row.serial_no} className="hover:bg-canvas">
                  <td className="tabular px-2 py-1 text-mute">{formatDate(row.date_of_occur)}</td>
                  <td className="tabular px-2 py-1 text-ink">{row.tag_number ?? "-"}</td>
                  <td className="px-2 py-1 text-ink">{row.risk_case_title_display}</td>
                  <td className="px-2 py-1 text-mute">{row.overall_status}</td>
                  <td className="tabular px-2 py-1 text-right text-ink">{row.downtime_hrs} h</td>
                  <td className="tabular px-2 py-1 text-right text-ink">
                    <Money kusd={row.total_loss_kusd} plantCode={plantCode} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length > 50 && (
            <div className="border-t border-line px-2 py-1 text-12 text-mute">
              Showing 50 of {rows.length}
            </div>
          )}
          {rows.length === 0 && <p className="p-2 text-13 text-mute">No incidents on or before the replay date.</p>}
        </Modal>
      )}
    </>
  );
}
