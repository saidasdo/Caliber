import { useParams, useSearchParams } from "react-router-dom";
import { useAppState } from "../state/AppStateContext";

// Resolves the plant a Plant or Equipment page is currently scoped to, so the breadcrumb
// and the page tabs can agree on what "the current plant" means without either one owning
// the other's data fetch. Equipment pages don't carry plantCode in the URL, so it is looked
// up from the already-loaded overview priority queue (every equipment reachable from the
// asset tree appears there). Diagnosis/Actions/Backtest carry it as ?plant= instead, when
// reached from inside a plant.
export function useCurrentPlantCode(): string | null {
  const params = useParams<{ plantCode?: string; tag?: string }>();
  const [searchParams] = useSearchParams();
  const { overview } = useAppState();

  if (params.plantCode) return params.plantCode;
  if (params.tag && overview.status === "ready") {
    const row = overview.data.priority_queue.find((r) => r.equipment_tag === params.tag);
    return row?.plant_code ?? null;
  }
  return searchParams.get("plant");
}
