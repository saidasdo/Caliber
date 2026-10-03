import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import { getEnergyProxy } from "../../lib/api";
import { useFetch } from "../../lib/useFetch";
import { colors } from "../../styles/tokens";

// SPEC section 5.10 (low priority, built last): "Daily sum of motor current per equipment as
// a 'Motor load index', 7-day moving average forecast for the next 7 days. Always labeled
// 'Proxy derived from motor current, not metered energy'."
export function EnergyProxyPanel({ tag, compact }: { tag: string; compact?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const state = useFetch(() => getEnergyProxy(tag), [tag]);

  useEffect(() => {
    if (!ref.current || state.status !== "ready") return;
    const { history, moving_average, forecast } = state.data;
    if (history.length === 0) return;

    const days = [...history.map((h) => h.day), ...forecast.map((f) => f.day)];
    const historySeries = history.map((h) => h.motor_load_index);
    const forecastSeries = [
      ...new Array(history.length - 1).fill(null),
      moving_average[moving_average.length - 1]?.value ?? null,
      ...forecast.map((f) => f.value),
    ];
    const movingAverageSeries = [...moving_average.map((m) => m.value), ...forecast.map(() => null)];

    const chart = echarts.init(ref.current);
    chart.setOption({
      grid: compact ? { left: 4, right: 4, top: 4, bottom: 4 } : { left: 50, right: 16, top: 16, bottom: 40 },
      textStyle: { fontFamily: "IBM Plex Sans" },
      xAxis: {
        type: "category",
        data: days,
        show: !compact,
        axisLabel: { fontSize: 10, color: colors.mute, rotate: 30, formatter: (v: string) => v.slice(5) },
        axisLine: { lineStyle: { color: colors.line } },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        show: !compact,
        axisLabel: { fontSize: 10, color: colors.mute },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: colors.line, type: "dashed" } },
      },
      legend: compact
        ? undefined
        : {
            data: ["Motor load index", "7-day moving average", "Forecast"],
            top: 0,
            textStyle: { fontSize: 11, color: colors.mute },
            itemWidth: 12,
            itemHeight: 8,
          },
      series: [
        {
          name: "Motor load index",
          type: "bar",
          data: historySeries,
          itemStyle: { color: colors.line },
          barMaxWidth: 10,
        },
        {
          name: "7-day moving average",
          type: "line",
          data: movingAverageSeries,
          showSymbol: false,
          lineStyle: { color: colors.blue, width: 1.5 },
        },
        {
          name: "Forecast",
          type: "line",
          data: forecastSeries,
          showSymbol: false,
          lineStyle: { color: colors.orange, width: 1.5, type: "dashed" },
        },
      ],
      tooltip: { trigger: "axis", extraCssText: "box-shadow: 0 4px 16px rgba(14,17,22,0.16);" },
    });

    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
    };
  }, [state, compact]);

  if (compact) {
    return state.status === "ready" && state.data.history.length > 0 ? (
      <div ref={ref} style={{ height: "100%", minHeight: 70 }} />
    ) : (
      <div className="flex h-full items-center justify-center text-12 text-mute">
        {state.status === "loading" ? "Loading..." : "No data"}
      </div>
    );
  }

  return (
    <div className="border border-line bg-paper">
      <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        Energy proxy
      </div>
      {state.status === "ready" && state.data.history.length > 0 ? (
        <div ref={ref} style={{ height: 180 }} />
      ) : (
        <p className="p-3 text-13 text-mute">
          {state.status === "loading" ? "Loading..." : "No motor current data for this equipment."}
        </p>
      )}
      <p className="border-t border-line px-2 py-1.5 text-12 italic text-mute">
        {state.status === "ready" ? state.data.label : "Proxy derived from motor current, not metered energy"}
      </p>
    </div>
  );
}
