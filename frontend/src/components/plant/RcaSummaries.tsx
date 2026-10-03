import { useState } from "react";
import { Link } from "react-router-dom";
import type { PlantDetail } from "../../lib/types";
import { Modal } from "../ui/Modal";

// Phase 10 section 2 (plant manager page): "RCA summaries" for this plant's equipment. Root
// cause text is a genuine paragraph, not something a glance-and-go overview should carry
// inline, so this is a count tile that opens the full summaries in a pop-up.
export function RcaSummaries({ rows }: { rows: PlantDetail["rca_summaries"] }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex h-full w-full flex-col items-start border border-line bg-paper px-2 py-1.5 text-left hover:bg-canvas"
      >
        <span className="text-12 uppercase tracking-wide text-mute">RCA summaries</span>
        <span className="tabular font-display stretch-semi-expanded text-28 text-ink">{rows.length}</span>
        <span className="text-12 text-mute">{rows.length === 0 ? "none" : "cases on record"}</span>
      </button>

      {open && (
        <Modal title="RCA summaries" onClose={() => setOpen(false)} wide>
          <ul className="divide-y divide-line">
            {rows.map((row) => (
              <li key={row.equipment_tag} className="px-2 py-1.5">
                <Link to={`/equipment/${row.equipment_tag}`} className="tabular text-13 font-medium text-blue">
                  {row.equipment_tag}
                </Link>
                <span className="text-12 text-mute"> {row.equipment_name}</span>
                <p className="mt-0.5 text-13 text-ink">{row.root_cause ?? "No root cause recorded."}</p>
              </li>
            ))}
            {rows.length === 0 && <li className="px-2 py-2 text-13 text-mute">No RCA cases for this plant.</li>}
          </ul>
        </Modal>
      )}
    </>
  );
}
