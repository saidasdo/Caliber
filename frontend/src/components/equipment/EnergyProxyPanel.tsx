import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import { getEnergyProxy } from "../../lib/api";
import { useFetch } from "../../lib/useFetch";
import { colors } from "../../styles/tokens";
import { DAY_MS, dayIndex, dayLabel, tsToMs } from "../../lib/replayAxis";

// SPEC section 5.10 (low priority, built last): "Daily sum of motor current per equipment as a 'Motor
// load index', 7-day moving average forecast for the next 7 days. Always labeled 'Proxy derived from
// motor current, not metered energy'." Replay rule (SPEC 4): history ends at the replay date. The
// forecast starts the day after it (it is a projection, drawn dashed and labeled as one), and the
// rest of the record width stays an empty band.
export function EnergyProxyPanel({ tag, replayDate, compact }: { tag: string; replayDate: string; compact?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const state = useFetch(() => getEnergyProxy(tag, replayDate), [tag, replayDate]);

  useEffect(() => {
    if (!ref.current || state.status !== "ready") return;
    const { history, moving_average: movingAverage, forecast, axis_days: axisDays } = state.data;
    if (history.length === 0) return;

    const startDay = history[0].day;
    const startMs = tsToMs(startDay);
    const lastHistoryIndex = dayIndex(startDay, history[history.length - 1].day);
    const forecastIndices = forecast.map((f) => dayIndex(startDay, f.day));
    const n = Math.max(axisDays, ...forecastIndices.map((i) => i + 1), lastHistoryIndex + 1);

    const labels = Array.from({ length: n }, (_, i) => (i % 3 === 0 ? dayLabel(startMs + i * DAY_MS) : ""));
    const historySeries: (number | null)[] = new Array(n).fill(null);
    const averageSeries: (number | null)[] = new Array(n).fill(null);
    const forecastSeries: (number | null)[] = new Array(n).fill(null);
    history.forEach((h) => (historySeries[dayIndex(startDay, h.day)] = h.motor_load_index));
    movingAverage.forEach((m) => (averageSeries[dayIndex(startDay, m.day)] = m.value));
    // The dashed forecast starts on the last real day so the two lines join.
    const lastAverage = movingAverage[movingAverage.length - 1]?.value ?? null;
    forecastSeries[lastHistoryIndex] = lastAverage;
    forecast.forEach((f, k) => (forecastSeries[forecastIndices[k]] = f.value));

    const chart = echarts.init(ref.current);
    chart.setOption({
      grid: compact ? { left: 40, right: 8, top: 8, bottom: 20 } : { left: 50, right: 16, top: 16, bottom: 40 },
      textStyle: { fontFamily: "IBM Plex Sans" },
      xAxis: {
        type: "category",
        data: labels,
        show: true,
        axisLabel: { fontSize: 10, color: colors.mute, interval: 0 },
        axisLine: { lineStyle: { color: colors.line } },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        show: true,
        axisLabel: { fontSize: 10, color: colors.mute },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: colors.line, type: "dashed" } },
      },
      legend: compact
        ? undefined
        : {
            data: ["Motor load index", "7-day moving average", "Forecast (after replay date)"],
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
          markArea: {
            silent: true,
            data:
              lastHistoryIndex < n - 1
                ? [
                    [
                      {
                        xAxis: lastHistoryIndex + 0.5,
                        itemStyle: { color: colors.canvas },
                        label: { show: false },
                      },
                      { xAxis: n - 1 },
                    ],
                  ]
                : [],
          },
        },
        {
          name: "7-day moving average",
          type: "line",
          data: averageSeries,
          showSymbol: false,
          connectNulls: false,
          lineStyle: { color: colors.blue, width: 1.5 },
        },
        {
          name: "Forecast (after replay date)",
          type: "line",
          data: forecastSeries,
          showSymbol: false,
          connectNulls: false,
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
