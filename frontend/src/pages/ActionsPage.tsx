import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAppState } from "../state/AppStateContext";
import { getActions, getProblems } from "../lib/api";
import { useFetch } from "../lib/useFetch";
import type { ActionStatus, TrackedAction } from "../lib/types";
import { ProblemTankSummary } from "../components/actions/ProblemTankSummary";
import { FilterRail } from "../components/actions/FilterRail";
import { ActionsTable } from "../components/actions/ActionsTable";
import { ActionDetailDrawer } from "../components/actions/ActionDetailDrawer";
import { PlantFilterChip } from "../components/shell/PlantFilterChip";

// SPEC section 7: "Actions: narrow 3-column filter and count rail plus 9-column dense table,
// detail drawer on the right." SPEC 5.7: Problem Tank sits alongside action tracking.
export function ActionsPage() {
  const { replayDate } = useAppState();
  const [status, setStatus] = useState<ActionStatus | null>(null);
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [selected, setSelected] = useState<TrackedAction | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [searchParams] = useSearchParams();
  const plantFilter = searchParams.get("plant");

  const problems = useFetch(() => getProblems(replayDate), [replayDate, refreshKey]);
  const actions = useFetch(
    () => getActions({ replayDate, status: status ?? undefined, plantCode: plantFilter ?? undefined }),
    [replayDate, status, plantFilter, refreshKey],
  );

  const refetch = () => setRefreshKey((k) => k + 1);

  if (actions.status === "error" || problems.status === "error") {
    return (
      <div className="border border-line bg-paper p-3 text-13 text-red">
        Could not load actions.
      </div>
    );
  }

  const rows =
    actions.status === "ready"
      ? overdueOnly
        ? actions.data.results.filter((a) => a.overdue_days)
        : actions.data.results
      : [];

  return (
    <div className="flex flex-col gap-1.5">
      {problems.status === "ready" && (
        <ProblemTankSummary counts={problems.data.counts_by_source_type} problems={problems.data.results} />
      )}

      {plantFilter && (
        <PlantFilterChip plantCode={plantFilter} clearTo="/actions" />
      )}

      <div className="grid grid-cols-12 gap-1.5">
        <div className="col-span-3">
          {actions.status === "ready" && (
            <FilterRail
              counts={actions.data.counts_by_status}
              status={status}
              onStatusChange={setStatus}
              overdueOnly={overdueOnly}
              onOverdueOnlyChange={setOverdueOnly}
            />
          )}
        </div>
        <div className="col-span-9">
          {actions.status === "ready" ? (
            <ActionsTable actions={rows} selectedId={selected?.id ?? null} onSelect={setSelected} />
          ) : (
            <div className="border border-line bg-paper p-3 text-13 text-mute">Loading actions...</div>
          )}
        </div>
      </div>

      {selected && (
        <ActionDetailDrawer
          action={selected}
          onClose={() => setSelected(null)}
          onChanged={() => {
            refetch();
            setSelected(null);
          }}
        />
      )}
    </div>
  );
}
