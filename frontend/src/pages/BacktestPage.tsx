import { useSearchParams } from "react-router-dom";
import { getBacktest } from "../lib/api";
import { useFetch } from "../lib/useFetch";
import { useLogViewMoney } from "../lib/useLogViewMoney";
import { useAppState } from "../state/AppStateContext";
import { BacktestSwimlane } from "../components/backtest/BacktestSwimlane";
import { BacktestTable } from "../components/backtest/BacktestTable";
import { PlantFilterChip } from "../components/shell/PlantFilterChip";

// SPEC section 5.8: "For each of the five equipment: first ALARM week, TRIP week, lead time
// in weeks; first hourly anomaly before the first OFF hour, lead time in hours; downtime and
// loss from the RCA. Swimlane timeline chart plus a table. Show the message 'Warning was
// available X weeks before the trip' with the assumption stated. Compute everything, do not
// hardcode." (All figures here come from app/engine/backtest.py, computed from health_weekly
// and sensor_hourly at ingest-read time, not stored constants.)
export function BacktestPage() {
  const { role, selectedPlant } = useAppState();
  const state = useFetch(() => getBacktest(), [role, selectedPlant]);
  useLogViewMoney("backtest");
  const [searchParams] = useSearchParams();
  const plantFilter = searchParams.get("plant");

  if (state.status === "loading") {
    return <div className="p-3 text-13 text-mute">Loading backtest...</div>;
  }
  if (state.status === "error") {
    return (
      <div className="border border-line bg-paper p-3 text-13 text-red">
        Could not load the backtest: {state.error}
      </div>
    );
  }

  const allResults = state.data.results;
  const results = plantFilter ? allResults.filter((r) => r.plant_code === plantFilter) : allResults;
  const assumption = allResults[0]?.assumption;

  return (
    <div className="flex flex-col gap-1.5">
      <p className="border border-line bg-paper px-2 py-1.5 text-13 text-mute">
        Retrospective view: compares warnings with what happened later.
      </p>
      <div className="border border-line bg-paper px-2 py-1.5">
        <h1 className="font-display stretch-semi-expanded text-20 font-bold text-ink">
          Backtest
        </h1>
        <p className="text-12 text-mute">
          For each equipment: how far in advance the weekly condition data and the hourly
          trend warned of the eventual trip.
        </p>
      </div>

      {plantFilter && <PlantFilterChip plantCode={plantFilter} clearTo="/backtest" />}

      <div className="border border-line bg-paper px-2 py-1.5">
        <ul className="divide-y divide-line">
          {results.map((r) => (
            <li key={r.equipment_tag} className="flex items-center gap-2 py-1 text-13">
              <span className="tabular w-[80px] shrink-0 font-medium text-ink">{r.equipment_tag}</span>
              <span className="text-ink">{r.message ?? "Not enough data to compute a lead time."}</span>
            </li>
          ))}
        </ul>
        {assumption && (
          <p className="mt-1.5 border-t border-line pt-1.5 text-12 italic text-mute">
            Assumption: {assumption}
          </p>
        )}
      </div>

      <BacktestSwimlane rows={results} />
      <BacktestTable rows={results} />
    </div>
  );
}
