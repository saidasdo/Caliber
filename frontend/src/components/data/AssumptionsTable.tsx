import type { Assumption } from "../../lib/types";

// Every applied assumption and replay rule, with the reason for it. The "not_error" rows
// (real data facts that are not data errors) belong to the Data quality tab instead.
// The emission factors here are placeholders until the team sets them from official sources.
export function AssumptionsTable({ entries }: { entries: Assumption[] }) {
  const rows = entries.filter((e) => e.area !== "not_error");
  return (
    <div className="border border-line bg-paper">
      <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        Assumptions and replay rules
      </div>
      <table className="w-full text-13">
        <thead>
          <tr className="border-b border-line text-left text-12 text-mute">
            <th className="w-[18%] px-2 py-1 font-medium">Area</th>
            <th className="w-[42%] px-2 py-1 font-medium">Assumption</th>
            <th className="px-2 py-1 font-medium">Rationale</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row) => (
            <tr key={row.id} className="align-top">
              <td className="px-2 py-1.5 font-medium text-ink">{row.area}</td>
              <td className="px-2 py-1.5 text-ink">{row.assumption_text}</td>
              <td className="px-2 py-1.5 text-mute">{row.rationale ?? "-"}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={3} className="px-2 py-2 text-mute">
                No assumptions recorded. Run npm run ingest.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
