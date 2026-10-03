import type { KpiDictionaryEntry } from "../../lib/types";

// SPEC section 5.9: "KPI dictionary: name, definition, formula, source, refresh frequency, owner."
export function KpiDictionaryTable({ entries }: { entries: KpiDictionaryEntry[] }) {
  return (
    <div className="border border-line bg-paper">
      <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        KPI dictionary
      </div>
      <table className="w-full text-13">
        <thead>
          <tr className="border-b border-line text-left text-12 text-mute">
            <th className="px-2 py-1 font-medium">KPI</th>
            <th className="px-2 py-1 font-medium">Definition</th>
            <th className="px-2 py-1 font-medium">Formula</th>
            <th className="px-2 py-1 font-medium">Source</th>
            <th className="px-2 py-1 font-medium">Refresh</th>
            <th className="px-2 py-1 font-medium">Owner</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {entries.map((e) => (
            <tr key={e.kpi_name} className="align-top hover:bg-canvas">
              <td className="whitespace-nowrap px-2 py-1.5 font-medium text-ink">{e.kpi_name}</td>
              <td className="px-2 py-1.5 text-ink">{e.definition}</td>
              <td className="px-2 py-1.5 text-mute">{e.formula ?? "-"}</td>
              <td className="px-2 py-1.5 text-mute">{e.source ?? "-"}</td>
              <td className="whitespace-nowrap px-2 py-1.5 text-mute">{e.refresh_frequency ?? "-"}</td>
              <td className="whitespace-nowrap px-2 py-1.5 text-mute">{e.owner ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
