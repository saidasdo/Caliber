// Phase 10 (SPEC 5.11 extended): "Every API request carries the current role and plant
// scope (header X-Role, X-Plant)." api.ts's fetch helpers are plain functions, not hooks, so
// they can't read AppStateContext directly; AppStateProvider pushes the current role/plant in
// here on every change, and the fetch helpers read it back when building headers.
import type { Role } from "./types";

let currentRole: Role = "Executive";
let currentPlant: string | null = null;
let currentReplayDate: string | null = null;

export function setRequestScope(role: Role, plant: string | null, replayDate: string | null = null): void {
  currentRole = role;
  currentPlant = plant;
  currentReplayDate = replayDate;
}

// X-Replay-Date tells the backend which day "today" is, so writes record the date they were
// made on (actions.as_of_date) and reads can hide everything after it.
export function getRequestHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "X-Role": currentRole };
  if (currentPlant) headers["X-Plant"] = currentPlant;
  if (currentReplayDate) headers["X-Replay-Date"] = currentReplayDate;
  return headers;
}
