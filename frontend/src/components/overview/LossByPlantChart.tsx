import { useEffect, useMemo, useRef } from "react";
import * as echarts from "echarts";
import type { PlantLoss } from "../../lib/types";
import { colors } from "../../styles/tokens";
import { useAppState } from "../../state/AppStateContext";
import { formatMoneyKusd, formatHours } from "../../lib/format";

// SPEC section 5.1: "Loss by plant for all 12 plants, sorted." A chart instead of a 12-row
// list reads in the glance an Overview page is supposed to take; click opens the full
// numbers (lib/priorityCardStyle-style click-through, see OverviewPage's modal).
// SPEC 5.11: a row the viewing role can't see money for falls back to downtime hours, same
// rule as the old list view, so the bar never leaks the hidden number through its length.
export function LossByPlantChart({ plants }: { plants: PlantLoss[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const { canSeeMoney } = useAppState();

  const rows = useMemo(
    () =>
      plants
        .map((p) => {
          const moneyVisible = canSeeMoney(p.plant_code) && p.loss_kusd != null;
          return {
            plant_code: p.plant_code,
            moneyVisible,
            value: moneyVisible ? p.loss_kusd! : p.downtime_hrs,
            label: moneyVisible ? formatMoneyKusd(p.loss_kusd!) : formatHours(p.downtime_hrs),
          };
        })
        // Chart reads top-to-bottom as highest-first, so reverse here (ECharts category axis
        // draws bottom to top).
        .reverse(),
    [plants, canSeeMoney],
  );

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption({
      textStyle: { fontFamily: "IBM Plex Sans", color: colors.ink },
      grid: { left: 48, right: 56, top: 4, bottom: 4 },
      xAxis: { type: "value", show: false },
      yAxis: {
        type: "category",
        data: rows.map((r) => r.plant_code),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: colors.ink, fontSize: 12, fontWeight: 500 },
      },
      tooltip: {
        trigger: "item",
        borderWidth: 0,
        extraCssText: "box-shadow: 0 4px 16px rgba(14,17,22,0.16);",
        formatter: (p: { dataIndex: number }) => {
          const r = rows[p.dataIndex];
          return `${r.plant_code}: ${r.label}${r.moneyVisible ? "" : " (downtime)"}`;
        },
      },
      series: [
        {
          type: "bar",
          data: rows.map((r) => r.value),
          barCategoryGap: "30%",
          itemStyle: { color: colors.blue },
          label: {
            show: true,
            position: "right",
            formatter: (p: { dataIndex: number }) => rows[p.dataIndex].label,
            color: colors.mute,
            fontSize: 11,
          },
        },
      ],
    });

    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
    };
  }, [rows]);

  return <div ref={ref} className="h-full w-full" />;
}
