import { Link } from "react-router-dom";
import type { BacktestRow } from "../../lib/types";
import { formatDate, formatHours } from "../../lib/format";
import { Money } from "../ui/Money";

// SPEC section 5.8: table alongside the swimlane, with the same computed figures.
export function BacktestTable({ rows }: { rows: BacktestRow[] }) {
  return (
    <div className="border border-line bg-paper">
      <table className="w-full text-13">
        <thead>
          <tr className="border-b border-line text-left text-12 text-mute">
            <th className="px-2 py-1 font-medium">Equipment</th>
            <th className="px-2 py-1 font-medium">First ALARM</th>
            <th className="px-2 py-1 font-medium">TRIP</th>
            <th className="px-2 py-1 font-medium text-right">Lead (weeks)</th>
            <th className="px-2 py-1 font-medium">First hourly anomaly</th>
            <th className="px-2 py-1 font-medium">First OFF hour</th>
            <th className="px-2 py-1 font-medium text-right">Lead (hours)</th>
            <th className="px-2 py-1 font-medium text-right">Downtime</th>
            <th className="px-2 py-1 font-medium text-right">Loss</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((r) => (
            <tr key={r.equipment_tag} className="hover:bg-canvas">
              <td className="px-2 py-1.5">
                <Link to={`/equipment/${r.equipment_tag}`} className="tabular font-medium text-blue">
                  {r.equipment_tag}
                </Link>
              </td>
              <td className="px-2 py-1.5 text-ink">
                {r.first_alarm_date ? (
                  <>
                    wk {r.first_alarm_week}
                    <span className="block text-12 text-mute">{formatDate(r.first_alarm_date)}</span>
                  </>
                ) : (
                  "-"
                )}
              </td>
              <td className="px-2 py-1.5 text-ink">
                {r.first_trip_date ? (
                  <>
                    wk {r.first_trip_week}
                    <span className="block text-12 text-mute">{formatDate(r.first_trip_date)}</span>
                  </>
                ) : (
                  "-"
                )}
              </td>
              <td className="tabular px-2 py-1.5 text-right font-medium text-ink">
                {r.lead_time_weeks ?? "-"}
              </td>
              <td className="px-2 py-1.5 text-ink">
                {r.first_hourly_anomaly_ts ? (
                  <>
                    wk {r.first_hourly_anomaly_week}
                    <span className="block text-12 text-mute tabular">{r.first_hourly_anomaly_ts}</span>
                  </>
                ) : (
                  <span className="text-mute">no anomaly on this signal</span>
                )}
              </td>
              <td className="tabular px-2 py-1.5 text-mute">{r.first_off_ts ?? "-"}</td>
              <td className="tabular px-2 py-1.5 text-right font-medium text-ink">
                {r.lead_time_hours ?? "-"}
              </td>
              <td className="tabular px-2 py-1.5 text-right text-ink">
                {r.downtime_hours != null ? formatHours(r.downtime_hours) : "-"}
              </td>
              <td className="tabular px-2 py-1.5 text-right text-ink">
                <Money kusd={r.loss_kusd} plantCode={r.plant_code} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
