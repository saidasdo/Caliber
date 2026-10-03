import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { getOverview, getReplayConfig, logRoleSwitch } from "../lib/api";
import { canSeeMoney } from "../lib/money";
import { setRequestScope } from "../lib/requestScope";
import type { OverviewResponse, ReplayConfig, Role } from "../lib/types";
import type { FetchState } from "../lib/useFetch";

// "PlantPulse" is a placeholder product name (SPEC intro), kept in one place so it can be
// renamed; the authoritative value still comes from the backend config constant.
const FALLBACK_PRODUCT_NAME = "PlantPulse";
const FALLBACK_REPLAY_DATE = "2026-04-08";

interface AppState {
  productName: string;
  replayDate: string;
  setReplayDate: (date: string) => void;
  presets: ReplayConfig["presets"];
  role: Role;
  setRole: (role: Role) => void;
  // SPEC 5.11: "Plant manager: pick a plant; money visible only for that plant."
  selectedPlant: string | null;
  setSelectedPlant: (plantCode: string | null) => void;
  canSeeMoney: (plantCode?: string | null) => boolean;
  // Shared across the shell (asset tree status) and the Overview page, refetched whenever
  // the replay date changes, so every consumer stays in sync with one network call.
  overview: FetchState<OverviewResponse>;
  // Phase 10: the Engineer's landing page is "the top alert, opened" (SPEC phase 10 section
  // 2). Derived here, not stored, so it's always consistent with the live priority queue;
  // scoped to selectedPlant when one is set (Engineer's optional plant filter).
  topAlertTag: string | null;
  // Set by the machine page: true while the machine is in alarm or trip and a suggested action
  // is still untracked, so the Action tab in the page tabs beeps until someone acts on it.
  actionDue: boolean;
  setActionDue: (due: boolean) => void;
}

const AppStateContext = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [replayDate, setReplayDate] = useState(FALLBACK_REPLAY_DATE);
  const [role, setRoleState] = useState<Role>("Engineer");
  const [selectedPlant, setSelectedPlant] = useState<string | null>(null);
  const [config, setConfig] = useState<ReplayConfig | null>(null);
  const [overview, setOverview] = useState<FetchState<OverviewResponse>>({ status: "loading" });
  const previousRole = useRef<Role>("Engineer");
  const [actionDue, setActionDue] = useState(false);

  useEffect(() => {
    getReplayConfig()
      .then((cfg) => {
        setConfig(cfg);
        setReplayDate(cfg.default_replay_date);
      })
      .catch(() => {
        // Backend not reachable yet; keep the fallback default so the shell still renders.
      });
  }, []);

  // Phase 10 section 5: every API request carries X-Role / X-Plant. api.ts's fetch helpers
  // aren't hooks, so the scope is pushed into a module-level holder (lib/requestScope.ts)
  // here, on every change. Declared before the overview-fetch effect below (React runs a
  // render's effects in declaration order) so that fetch always sees the up-to-date scope,
  // never a stale one from before the latest role/plant switch.
  useEffect(() => {
    setRequestScope(role, selectedPlant);
  }, [role, selectedPlant]);

  useEffect(() => {
    let cancelled = false;
    setOverview({ status: "loading" });
    getOverview(replayDate)
      .then((data) => {
        if (!cancelled) setOverview({ status: "ready", data });
      })
      .catch((err: Error) => {
        if (!cancelled) setOverview({ status: "error", error: err.message });
      });
    return () => {
      cancelled = true;
    };
    // Response shape depends on role/plant (server-side money redaction), so this must
    // refetch on every switch, not just when the replay date moves.
  }, [replayDate, role, selectedPlant]);

  function setRole(next: Role) {
    const from = previousRole.current;
    previousRole.current = next;
    setRoleState(next);
    // SPEC phase 10 section 6: "Choosing Plant manager asks for the plant (default ZCU)."
    if (next === "Plant manager" && selectedPlant == null) setSelectedPlant("ZCU");
    if (next !== "Plant manager" && next !== "Engineer") setSelectedPlant(null);
    // SPEC 5.11: "Log role switches ... to audit_log." Fire-and-forget: a logging failure
    // must never block the UI from switching roles.
    logRoleSwitch({ from_role: from, to_role: next, selected_plant: selectedPlant }).catch(() => {});
  }

  const topAlertTag =
    overview.status === "ready"
      ? (overview.data.priority_queue.find((r) => !selectedPlant || r.plant_code === selectedPlant)
          ?.equipment_tag ?? null)
      : null;

  const value = useMemo<AppState>(
    () => ({
      productName: config?.product_name ?? FALLBACK_PRODUCT_NAME,
      replayDate,
      setReplayDate,
      presets: config?.presets ?? [],
      role,
      setRole,
      selectedPlant,
      setSelectedPlant,
      canSeeMoney: (plantCode?: string | null) => canSeeMoney(role, selectedPlant, plantCode),
      overview,
      topAlertTag,
      actionDue,
      setActionDue,
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [config, replayDate, role, selectedPlant, overview, topAlertTag, actionDue],
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState(): AppState {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useAppState must be used within AppStateProvider");
  return ctx;
}
