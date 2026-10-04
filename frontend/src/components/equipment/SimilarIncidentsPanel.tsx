import { Link } from "react-router-dom";
import type { SimilarIncident } from "../../lib/types";
import { formatDate } from "../../lib/format";
import { Money } from "../ui/Money";
import { StatusAsOfNote } from "../ui/StatusAsOfNote";

const SENSOR_TAGS = new Set(["PU-2101B", "KO-3201", "PM-4405B", "HE-3301", "BL-5702"]);

// SPEC section 5.6: "Top 5 with AR No., date, downtime, loss, status, link to RCA if present.
// Rows flagged by DQ9 appear with a warning tag, and the score explanation is visible."
export function SimilarIncidentsPanel({ incidents }: { incidents: SimilarIncident[] }) {
  return (
    <div className="h-full border border-line bg-paper">
      <StatusAsOfNote />
      <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        Similar incidents
      </div>
      <ul className="divide-y divide-line">
        {incidents.map((inc) => (
          <li key={inc.serial_no} className="px-2 py-1.5">
            <div className="flex items-center justify-between gap-1">
              <span className="tabular truncate text-13 font-medium text-ink" title={inc.risk_case_title ?? ""}>
                {inc.tag_number}
              </span>
              <div className="flex items-center gap-1">
                {inc.dq9_flag && (
                  <span
                    className="rounded bg-amber px-1 py-0.5 text-12 font-semibold text-ink"
                    title="DQ9: implausible component for this equipment type"
                  >
                    DQ9
                  </span>
                )}
                <span
                  className="tabular rounded border border-line px-1 py-0.5 text-12 text-mute"
                  title={Object.entries(inc.score_breakdown)
                    .map(([k, v]) => `${k} +${v}`)
                    .join(", ")}
                >
                  score {inc.score}
                </span>
              </div>
            </div>
            <p className="truncate text-12 text-mute">{inc.risk_case_title}</p>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-12 text-mute">
              <span>{formatDate(inc.date_of_occur)}</span>
              <span>{inc.downtime_hrs} h</span>
              <Money kusd={inc.total_loss_kusd} plantCode={inc.plant_code} />
              <span>{inc.overall_status}</span>
              {inc.ar_no ? (
                SENSOR_TAGS.has(inc.tag_number) ? (
                  <Link to={`/equipment/${inc.tag_number}`} className="text-blue">
                    {inc.ar_no}
                  </Link>
                ) : (
                  <span>{inc.ar_no}</span>
                )
              ) : (
                <span className="text-mute">no AR No.</span>
              )}
            </div>
          </li>
        ))}
        {incidents.length === 0 && (
          <li className="px-2 py-2 text-13 text-mute">No similar incidents found.</li>
        )}
      </ul>
    </div>
  );
}
