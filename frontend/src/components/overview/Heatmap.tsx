import type { ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import type { HeatmapCell } from "../../lib/types";
import { colors } from "../../styles/tokens";
import { useAppState } from "../../state/AppStateContext";

type Metric = "incident_count" | "loss_kusd";

const MONTH_ORDER = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function monthKey(monthYear: string): string {
  const [mon, year] = monthYear.split("-");
  const idx = MONTH_ORDER.indexOf(mon);
  return `${year}-${String(idx).padStart(2, "0")}`;
}

// SPEC section 5.1: "Heatmap: plant x month (incident count, toggle to loss), inspired by the
// 'Workload' heatmap in reference 2." Charts are Apache ECharts per section 1.
export function Heatmap({
  cells,
  height = 260,
  headerAction,
}: {
  cells: HeatmapCell[];
  height?: number;
  headerAction?: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [metric, setMetric] = useState<Metric>("incident_count");
  // The heatmap spans all 12 plants at once, so it cannot be scoped to one plant: only
  // Executive (SPEC 5.11) may see the loss toggle at all.
  const { canSeeMoney } = useAppState();
  const lossAllowed = canSeeMoney(undefined);
  const effectiveMetric: Metric = metric === "loss_kusd" && !lossAllowed ? "incident_count" : metric;

  const { plants, months, matrix, max } = useMemo(() => {
    const plantSet = Array.from(new Set(cells.map((c) => c.plant_code))).sort();
    const monthSet = Array.from(new Set(cells.map((c) => c.month_year))).sort(
      (a, b) => monthKey(a).localeCompare(monthKey(b)),
    );
    const plantIndex = new Map(plantSet.map((p, i) => [p, i]));
    const monthIndex = new Map(monthSet.map((m, i) => [m, i]));
    const data = cells.map((c) => [
      monthIndex.get(c.month_year)!,
      plantIndex.get(c.plant_code)!,
      Math.round((c[effectiveMetric] ?? 0) * 100) / 100,
    ]);
    const maxValue = Math.max(...data.map((d) => d[2] as number), 1);
    return { plants: plantSet, months: monthSet, matrix: data, max: maxValue };
  }, [cells, effectiveMetric]);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption({
      textStyle: { fontFamily: "IBM Plex Sans", color: colors.ink },
      grid: { left: 60, right: 16, top: 10, bottom: 50 },
      xAxis: {
        type: "category",
        data: months,
        axisLine: { lineStyle: { color: colors.line } },
        axisLabel: { color: colors.mute, fontSize: 11, rotate: 45 },
        splitArea: { show: false },
      },
      yAxis: {
        type: "category",
        data: plants,
        axisLine: { lineStyle: { color: colors.line } },
        axisLabel: { color: colors.mute, fontSize: 11 },
        splitArea: { show: false },
      },
      visualMap: {
        min: 0,
        max,
        show: false,
        inRange: { color: [colors.canvas, colors.amber, colors.red] },
      },
      tooltip: {
        borderWidth: 0,
        extraCssText: "box-shadow: 0 4px 16px rgba(14,17,22,0.16);",
        formatter: (p: { data: [number, number, number] }) => {
          const [mIdx, pIdx, v] = p.data;
          const label = effectiveMetric === "incident_count" ? "incidents" : "k USD loss";
          return `${plants[pIdx]} / ${months[mIdx]}<br/>${v} ${label}`;
        },
      },
      series: [
        {
          type: "heatmap",
          data: matrix,
          itemStyle: { borderColor: colors.paper, borderWidth: 1 },
          emphasis: { itemStyle: { borderColor: colors.ink, borderWidth: 1 } },
        },
      ],
    });

    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
    };
  }, [plants, months, matrix, max, effectiveMetric]);

  return (
    <div className="border border-line bg-paper">
      <div className="flex items-center justify-between border-b border-line px-2 py-1.5">
        <span className="text-12 font-semibold uppercase tracking-wide text-mute">
          Plant x month
        </span>
        <div className="flex border border-line text-12">
          <button
            type="button"
            onClick={() => setMetric("incident_count")}
            className={`px-1 py-0.5 ${effectiveMetric === "incident_count" ? "bg-ink text-white" : "text-mute"}`}
          >
            Incidents
          </button>
          {lossAllowed && (
            <button
              type="button"
              onClick={() => setMetric("loss_kusd")}
              className={`border-l border-line px-1 py-0.5 ${
                effectiveMetric === "loss_kusd" ? "bg-ink text-white" : "text-mute"
              }`}
            >
              Loss
            </button>
          )}
        </div>
        {headerAction}
      </div>
      <div ref={ref} style={{ height }} />
    </div>
  );
}
