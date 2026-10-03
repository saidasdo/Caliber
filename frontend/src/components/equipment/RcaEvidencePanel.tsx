import type { LinkedRca } from "../../lib/types";

interface FourColRow {
  item: string;
  parameter?: string;
  factor?: string;
  result: "G" | "NG" | string;
  evidence: string;
}

// Phase 10 section 2 (engineer equipment page): "RCA evidence (4P and 4M+1E summary,
// chronology)." Same rca_reports row the Equipment page already links, just the structured
// 4P (problem validation) / 4M+1E (root-cause factor) tables and the chronology, which were
// ingested in phase 1 but never shown anywhere until now.
export function RcaEvidencePanel({ rca }: { rca: LinkedRca | null }) {
  if (!rca) {
    return (
      <div className="border border-line bg-paper p-2 text-13 text-mute">
        No linked RCA for this equipment.
      </div>
    );
  }

  const fourP = (rca.four_p as FourColRow[] | null) ?? [];
  const fourM1E = (rca.four_m_1e as FourColRow[] | null) ?? [];

  return (
    <div className="border border-line bg-paper">
      <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        RCA evidence
      </div>
      <div className="p-2">
        <p className="text-12 text-mute">Root cause</p>
        <p className="text-13 text-ink">{rca.root_cause ?? "Not recorded."}</p>
      </div>

      {fourP.length > 0 && <FourColTable title="4P (problem validation)" rows={fourP} />}
      {fourM1E.length > 0 && <FourColTable title="4M+1E (contributing factors)" rows={fourM1E} />}

      {rca.chronology.length > 0 && (
        <div className="border-t border-line p-2">
          <p className="mb-1 text-12 text-mute">Chronology</p>
          <ul className="space-y-0.5">
            {rca.chronology.map((e, i) => (
              <li key={i} className="flex gap-2 text-13">
                <span className="tabular shrink-0 text-mute">{e.datetime}</span>
                <span className="text-ink">{e.event}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function FourColTable({ title, rows }: { title: string; rows: FourColRow[] }) {
  return (
    <div className="border-t border-line p-2">
      <p className="mb-1 text-12 text-mute">{title}</p>
      <table className="w-full text-13">
        <tbody className="divide-y divide-line">
          {rows.map((row) => (
            <tr key={row.item}>
              <td className="w-[70px] py-1 align-top text-mute">{row.item}</td>
              <td className="w-[80px] py-1 align-top">
                <span
                  className={`rounded px-1 py-0.5 text-12 font-semibold ${
                    row.result === "NG" ? "bg-red text-white" : "bg-green text-white"
                  }`}
                >
                  {row.result}
                </span>
              </td>
              <td className="py-1 align-top text-ink">
                <span className="font-medium">{row.parameter ?? row.factor}</span>
                <p className="text-12 text-mute">{row.evidence}</p>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
