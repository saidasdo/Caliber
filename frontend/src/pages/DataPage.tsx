import { useState } from "react";
import { useAppState } from "../state/AppStateContext";
import { getAssumptions, getDataQuality, getKpiDictionary, getProcessFlags, getSourceMap } from "../lib/api";
import { useFetch } from "../lib/useFetch";
import { SourceMapTable } from "../components/data/SourceMapTable";
import { KpiDictionaryTable } from "../components/data/KpiDictionaryTable";
import { DataQualityPanel } from "../components/data/DataQualityPanel";
import { ProcessFlagsPanel } from "../components/data/ProcessFlagsPanel";
import { AssumptionsTable } from "../components/data/AssumptionsTable";

type SubTab = "source-map" | "kpi-dictionary" | "assumptions" | "data-quality";

const SUB_TABS: { id: SubTab; label: string }[] = [
  { id: "source-map", label: "Source map" },
  { id: "kpi-dictionary", label: "KPI dictionary" },
  { id: "assumptions", label: "Assumptions" },
  { id: "data-quality", label: "Data quality" },
];

// SPEC section 5.9: "Data foundation" - source map, KPI dictionary, data quality (all
// DQ1-DQ12 findings plus the section 6 process flags, shown separately as "not data errors").
export function DataPage() {
  const { replayDate } = useAppState();
  const [tab, setTab] = useState<SubTab>("data-quality");

  const sourceMap = useFetch(() => getSourceMap(), []);
  const kpiDictionary = useFetch(() => getKpiDictionary(), []);
  const dataQuality = useFetch(() => getDataQuality(), []);
  const assumptions = useFetch(() => getAssumptions(), []);
  const processFlags = useFetch(() => getProcessFlags(replayDate), [replayDate]);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="border border-line bg-paper px-2 py-1.5">
        <h1 className="font-display stretch-semi-expanded text-20 font-bold text-ink">Data</h1>
        <p className="text-12 text-mute">
          Where every number on this dashboard comes from, what it means, and how trustworthy it is.
        </p>
        <p className="text-12 text-mute">Data quality checks run on the full dataset.</p>
      </div>

      <nav className="flex gap-4 border-b border-line bg-paper px-2">
        {SUB_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`border-b-2 py-1.5 text-13 font-medium ${
              tab === t.id ? "border-blue text-ink" : "border-transparent text-mute hover:text-ink"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "source-map" &&
        (sourceMap.status === "ready" ? (
          <SourceMapTable entries={sourceMap.data.entries} joinKeys={sourceMap.data.join_keys} />
        ) : (
          <Loading status={sourceMap.status} />
        ))}

      {tab === "kpi-dictionary" &&
        (kpiDictionary.status === "ready" ? (
          <KpiDictionaryTable entries={kpiDictionary.data.results} />
        ) : (
          <Loading status={kpiDictionary.status} />
        ))}

      {tab === "assumptions" &&
        (assumptions.status === "ready" ? (
          <AssumptionsTable entries={assumptions.data.results} />
        ) : (
          <Loading status={assumptions.status} />
        ))}

      {tab === "data-quality" && (
        <>
          {processFlags.status === "ready" ? (
            <ProcessFlagsPanel data={processFlags.data} />
          ) : (
            <Loading status={processFlags.status} />
          )}
          {dataQuality.status === "ready" ? (
            <DataQualityPanel data={dataQuality.data} />
          ) : (
            <Loading status={dataQuality.status} />
          )}
        </>
      )}
    </div>
  );
}

function Loading({ status }: { status: string }) {
  return (
    <div className="border border-line bg-paper p-3 text-13 text-mute">
      {status === "error" ? "Could not load this section." : "Loading..."}
    </div>
  );
}
