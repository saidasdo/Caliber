import { useEffect, useRef } from "react";
import { useAppState } from "../state/AppStateContext";
import { logViewMoney } from "./api";

// SPEC section 5.11: "Log ... views of money values to audit_log." Logs once per
// (page, role, plant) combination, not on every render, so this stays a meaningful audit
// trail instead of noise.
export function useLogViewMoney(page: string, plantCode?: string | null) {
  const { role, selectedPlant, canSeeMoney } = useAppState();
  const lastLogged = useRef<string | null>(null);

  useEffect(() => {
    if (!canSeeMoney(plantCode)) return;
    const key = `${page}:${role}:${plantCode ?? ""}:${selectedPlant ?? ""}`;
    if (lastLogged.current === key) return;
    lastLogged.current = key;
    logViewMoney({ actor_role: role, page, plant_code: plantCode ?? null }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, plantCode, role, selectedPlant]);
}
