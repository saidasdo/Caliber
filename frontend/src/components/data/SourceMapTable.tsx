import type { JoinKey, SourceMapEntry } from "../../lib/types";

// SPEC section 5.9: "Source map: which file, sheet and column feeds which table and which
// KPI, and which key links them."
export function SourceMapTable({ entries, joinKeys }: { entries: SourceMapEntry[]; joinKeys: JoinKey[] }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="border border-line bg-paper">
        <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
          Source map
        </div>
        <table className="w-full table-fixed text-13">
          <colgroup>
            <col style={{ width: "17%" }} />
            <col style={{ width: "12%" }} />
            <col style={{ width: "23%" }} />
            <col style={{ width: "23%" }} />
            <col style={{ width: "25%" }} />
          </colgroup>
          <thead>
            <tr className="border-b border-line text-left text-12 text-mute">
              <th className="px-2 py-1 font-medium">File</th>
              <th className="px-2 py-1 font-medium">Sheet</th>
              <th className="px-2 py-1 font-medium">Column</th>
              <th className="px-2 py-1 font-medium">Table.column</th>
              <th className="px-2 py-1 font-medium">Feeds</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {entries.map((e, i) => (
              <tr key={i} className="align-top hover:bg-canvas">
                <td className="break-words px-2 py-1.5 text-ink">{e.source_file}</td>
                <td className="break-words px-2 py-1.5 text-mute">{e.sheet}</td>
                <td className="break-words px-2 py-1.5 text-mute">{e.column ?? "-"}</td>
                <td className="break-words px-2 py-1.5 text-ink">
                  {e.target_table ? (
                    <span className="tabular">
                      {e.target_table}
                      {e.target_column ? <span className="text-mute">.{e.target_column}</span> : null}
                    </span>
                  ) : (
                    <span className="text-mute">-</span>
                  )}
                </td>
                <td className="px-2 py-1.5">
                  <div className="flex flex-wrap gap-1">
                    {e.feeds.map((f) => (
                      <span key={f} className="border border-line px-1 py-0.5 text-12 text-mute">
                        {f}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="border border-line bg-paper">
        <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
          Join keys
        </div>
        <ul className="divide-y divide-line">
          {joinKeys.map((k) => (
            <li key={k.key} className="px-2 py-1.5">
              <div className="text-13 font-medium text-ink">{k.key}</div>
              <div className="tabular text-12 text-mute">{k.links.join("  |  ")}</div>
              <div className="mt-0.5 text-12 text-mute">{k.notes}</div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
