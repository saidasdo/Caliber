import type { Diagnosis } from "../../lib/types";

// Phase 10 section 2: "diagnosis in one sentence" (executive) / a compact diagnosis summary
// (plant manager). Same diagnosis object as the full panel, just the headline.
export function DiagnosisOneLiner({ diagnosis }: { diagnosis: Diagnosis }) {
  return (
    <div className="border border-line bg-paper px-2 py-1.5 text-13">
      <span className="text-12 font-semibold uppercase tracking-wide text-mute">Diagnosis </span>
      {diagnosis.rule_name ? (
        <span className="text-ink">
          {diagnosis.rule_name} ({diagnosis.confidence} confidence)
        </span>
      ) : (
        <span className="text-mute">No confident root cause hint.</span>
      )}
    </div>
  );
}
