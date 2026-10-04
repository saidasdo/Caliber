import type { PriorityRow } from "./types";
import { formatMoneyKusd } from "./format";

// Phase 10 section 3: three templates over the same enriched alert row (app/engine/priority.py
// computes weeks_in_status, estimated_impact, diagnosis_rule_name/confidence alongside the
// existing fields), so every number here is real, not illustrative. estimated_impact is simply
// absent from the row when the viewing role can't see money (server-side redaction), so the
// executive template is only ever called where that's already guaranteed present. The impact is
// an estimate (median of earlier similar incidents), never presented as a known amount.

export function alertWordingExecutive(row: PriorityRow): string {
  // equipment_name already ends with the tag (e.g. "Cracked Gas Compressor KO-3201"), so it
  // alone is the subject; appending equipment_tag again would repeat it.
  const consequence =
    row.health_status === "TRIP"
      ? `${row.plant_code} production stop`
      : `risk of ${row.health_status === "ALARM" ? "trip" : "an upset"}`;
  const estimate = row.estimated_impact;
  const impact =
    estimate?.value_kusd != null
      ? ` Estimated impact: about ${formatMoneyKusd(estimate.value_kusd)} (median of ${estimate.n_incidents} similar past incidents).`
      : "";
  return `${row.equipment_name} at risk of trip. Possible impact: ${consequence}.${impact}`;
}

export function alertWordingPlantManager(
  row: PriorityRow,
  openActionsCount: number,
  nearestDueInDays: number | null,
): string {
  const status = row.health_status ?? "normal";
  const duration =
    row.weeks_in_status != null ? ` for ${row.weeks_in_status} week${row.weeks_in_status === 1 ? "" : "s"}` : "";
  const cause = row.diagnosis_rule_name ? ` Suspected ${row.diagnosis_rule_name.toLowerCase()}.` : "";
  const actions =
    openActionsCount === 0
      ? " No open actions."
      : ` ${openActionsCount} action${openActionsCount === 1 ? "" : "s"} open` +
        (nearestDueInDays != null
          ? nearestDueInDays < 0
            ? `, ${-nearestDueInDays} day${-nearestDueInDays === 1 ? "" : "s"} overdue.`
            : `, due in ${nearestDueInDays} day${nearestDueInDays === 1 ? "" : "s"}.`
          : ".");
  return `${row.equipment_tag} in ${status}${duration}.${cause}${actions}`;
}

export function alertWordingEngineer(row: PriorityRow): string {
  const wp = row.worst_parameter;
  const paramPart = wp
    ? `${wp.parameter} ${wp.value ?? "-"}${wp.unit ?? ""} (alarm ${wp.alarm ?? "-"})`
    : row.reason;
  const diagnosisPart = row.diagnosis_rule_name
    ? ` Diagnosis: ${row.diagnosis_rule_name}, ${row.diagnosis_confidence ?? "no"} confidence.`
    : " No confident diagnosis.";
  return `${paramPart}.${diagnosisPart}`;
}
