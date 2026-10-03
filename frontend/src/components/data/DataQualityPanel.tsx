import { useState } from "react";
import type { DataQualityResponse, DqIssue } from "../../lib/types";

const DQ_IDS = Array.from({ length: 12 }, (_, i) => `DQ${i + 1}`);

const SEVERITY_CLASS: Record<string, string> = {
  Error: "bg-red text-white",
  Warning: "bg-amber text-ink",
  Info: "bg-line text-ink",
};

// SPEC section 5.9: "Data quality: table of all dq_issues (section 6) with severity, source
// location, observed vs expected, applied assumption, status (Open/Accepted), plus a data
// quality score." Section 9 acceptance check: "All DQ1 to DQ12 findings ... are detected."
export function DataQualityPanel({ data }: { data: DataQualityResponse }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  function toggle(dqId: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(dqId) ? next.delete(dqId) : next.add(dqId);
      return next;
    });
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex border border-line bg-paper">
        <div className="flex-1 px-2 py-1.5">
          <div className="text-12 uppercase tracking-wide text-mute">Data quality score</div>
          <div className="tabular font-display stretch-semi-expanded text-44 text-ink">
            {data.score}
          </div>
          <div className="text-12 text-mute">{data.score_formula}</div>
        </div>
        <div className="flex-1 border-l border-line px-2 py-1.5">
          <div className="text-12 uppercase tracking-wide text-mute">Checks detected</div>
          <div className="tabular font-display stretch-semi-expanded text-44 text-green">
            {DQ_IDS.filter((id) => data.by_dq_id[id]?.length).length} / 12
          </div>
          <div className="text-12 text-mute">{data.issue_count} findings total</div>
        </div>
      </div>

      <div className="border border-line bg-paper">
        <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
          DQ1 - DQ12
        </div>
        <ul className="divide-y divide-line">
          {DQ_IDS.map((id) => {
            const issues = data.by_dq_id[id] ?? [];
            const detected = issues.length > 0;
            const isOpen = expanded.has(id);
            return (
              <li key={id}>
                <button
                  type="button"
                  onClick={() => toggle(id)}
                  className="flex w-full items-center justify-between px-2 py-1.5 text-left hover:bg-canvas"
                >
                  <span className="flex items-center gap-2">
                    <span
                      className={`rounded px-1 py-0.5 text-12 font-semibold ${
                        detected ? "bg-green text-white" : "bg-red text-white"
                      }`}
                    >
                      {detected ? "DETECTED" : "NOT DETECTED"}
                    </span>
                    <span className="tabular text-13 font-medium text-ink">{id}</span>
                    <span className="text-12 text-mute">
                      {issues.length} finding{issues.length === 1 ? "" : "s"}
                    </span>
                  </span>
                  <span className="text-12 text-mute">{isOpen ? "Hide" : "Show"}</span>
                </button>
                {isOpen && (
                  <div className="border-t border-line">
                    {issues.map((issue) => (
                      <IssueRow key={issue.id} issue={issue} />
                    ))}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </div>

      <div className="border border-line bg-paper">
        <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
          Not errors (documented, not flagged)
        </div>
        <ul className="divide-y divide-line">
          {data.not_errors.map((a) => (
            <li key={a.id} className="px-2 py-1.5">
              <p className="text-13 text-ink">{a.assumption_text}</p>
              {a.rationale && <p className="text-12 text-mute">{a.rationale}</p>}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function IssueRow({ issue }: { issue: DqIssue }) {
  return (
    <div className="grid grid-cols-12 gap-2 border-b border-line px-2 py-1.5 text-12 last:border-b-0">
      <div className="col-span-2">
        <span className={`rounded px-1 py-0.5 font-semibold ${SEVERITY_CLASS[issue.severity] ?? "bg-line text-ink"}`}>
          {issue.severity}
        </span>
        <span className="ml-1 text-mute">{issue.status}</span>
      </div>
      <div className="col-span-3 text-mute">{issue.source_location}</div>
      <div className="col-span-3">
        <div className="text-ink">{issue.observed}</div>
        {issue.expected && <div className="text-mute">Expected: {issue.expected}</div>}
      </div>
      <div className="col-span-4 text-mute">{issue.applied_assumption}</div>
    </div>
  );
}
