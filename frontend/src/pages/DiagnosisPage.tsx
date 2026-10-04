import { Link, useSearchParams } from "react-router-dom";
import { useAppState } from "../state/AppStateContext";
import { useFetch } from "../lib/useFetch";
import { getEquipment } from "../lib/api";
import { PlantFilterChip } from "../components/shell/PlantFilterChip";
import { PriorityChip } from "../components/ui/StatusChip";
import { priorityCardStyle } from "../lib/priorityCardStyle";
import type { PriorityRow } from "../lib/types";

const TAGS = ["PU-2101B", "KO-3201", "PM-4405B", "HE-3301", "BL-5702"];

const CONFIDENCE_CLASS: Record<string, string> = {
  High: "bg-green text-white",
  Medium: "bg-amber text-ink",
  Low: "bg-line text-ink",
};

// SPEC section 7 page tab "Diagnosis": a cross-equipment view of the rule-based root-cause
// hint (section 5.5) at the current replay date, so an engineer does not have to open each
// equipment page individually to see what is flagged right now. Cards are tinted and sorted
// by the same priority ranking as the Overview priority queue (section 5.4), so the one
// alert that most needs a look is first and hardest to miss, not just alphabetical.
export function DiagnosisPage() {
  const { replayDate, overview } = useAppState();
  const [searchParams] = useSearchParams();
  const plantFilter = searchParams.get("plant");

  const priorityByTag = new Map<string, PriorityRow>();
  if (overview.status === "ready") {
    for (const row of overview.data.priority_queue) priorityByTag.set(row.equipment_tag, row);
  }
  const tags = TAGS
    .filter((t) => !plantFilter || priorityByTag.get(t)?.plant_code === plantFilter)
    .sort((a, b) => (priorityByTag.get(a)?.rank ?? 99) - (priorityByTag.get(b)?.rank ?? 99));

  return (
    <div className="flex flex-col gap-1.5">
      <div className="border border-line bg-paper px-2 py-1.5">
        <h1 className="font-display stretch-semi-expanded text-20 font-bold text-ink">
          Diagnosis
        </h1>
        <p className="text-12 text-mute">
          Rule-based root cause hints for all 5 sensor-equipped equipment, as of the replay
          date, highest priority first. Suggested, needs engineer review.
        </p>
      </div>
      {plantFilter && <PlantFilterChip plantCode={plantFilter} clearTo="/diagnosis" />}
      {tags.length === 0 ? (
        <div className="border border-line bg-paper p-2 text-13 text-mute">
          No sensor-equipped equipment in {plantFilter} to diagnose.
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-1.5">
          {tags.map((tag) => (
            <EquipmentDiagnosisCard
              key={tag}
              tag={tag}
              replayDate={replayDate}
              priorityLabel={priorityByTag.get(tag)?.priority_label}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function EquipmentDiagnosisCard({
  tag,
  replayDate,
  priorityLabel,
}: {
  tag: string;
  replayDate: string;
  priorityLabel?: PriorityRow["priority_label"];
}) {
  const state = useFetch(() => getEquipment(tag, replayDate), [tag, replayDate]);

  if (state.status !== "ready") {
    return (
      <div className="border border-line bg-paper p-2 text-13 text-mute">
        {tag}: {state.status === "error" ? "failed to load" : "loading..."}
      </div>
    );
  }

  const { diagnosis } = state.data;
  const style = priorityCardStyle(priorityLabel);
  const confidenceClass = style.invertedChip
    ? "bg-white text-ink"
    : diagnosis.confidence
      ? CONFIDENCE_CLASS[diagnosis.confidence]
      : "bg-canvas text-mute";

  return (
    <Link
      to={`/equipment/${tag}`}
      className={`block border border-line p-2 ${
        style.container ? `${style.container} hover:brightness-95` : "bg-paper hover:border-blue"
      }`}
    >
      <div className="flex items-center justify-between gap-1">
        <span className={`tabular font-display text-15 font-bold ${style.heading}`}>{tag}</span>
        <div className="flex items-center gap-1">
          {priorityLabel && <PriorityChip label={priorityLabel} inverted={style.invertedChip} />}
          {diagnosis.confidence ? (
            <span className={`rounded px-1 py-0.5 text-12 font-semibold ${confidenceClass}`}>
              {diagnosis.confidence}
            </span>
          ) : (
            <span className={`rounded px-1 py-0.5 text-12 ${confidenceClass}`}>No hint</span>
          )}
        </div>
      </div>
      <p className={`mt-1 text-13 ${style.invertedChip ? style.heading : "text-ink"}`}>
        {diagnosis.rule_name ?? diagnosis.reason ?? "No confident root cause hint."}
      </p>
      {diagnosis.rule_name && <p className={`text-12 ${style.body}`}>{diagnosis.passes} of {diagnosis.of} conditions met</p>}
    </Link>
  );
}
