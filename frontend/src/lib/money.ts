import type { Role } from "./types";

// SPEC section 5.11:
// - Executive: sees all money values.
// - Plant manager: pick a plant; money visible only for that plant.
// - Engineer: no money values; impact shown as tons, hours and priority labels.
export function canSeeMoney(role: Role, selectedPlant: string | null, plantCode?: string | null): boolean {
  if (role === "Executive") return true;
  if (role === "Plant manager") return selectedPlant != null && plantCode != null && plantCode === selectedPlant;
  return false; // Engineer
}
