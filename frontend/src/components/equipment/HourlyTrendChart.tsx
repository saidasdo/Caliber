import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts";
import { getEquipmentAnomalies, getEquipmentSeries } from "../../lib/api";
import { useFetch } from "../../lib/useFetch";
import type { AnomalyMarker, HourlyPoint, Signal } from "../../lib/types";
import { colors } from "../../styles/tokens";
import {
  HOUR_MS,
  TICK_EVERY_HOURS,
  dayLabel,
  hourIndex,
  hourTimestamp,
  replayEndIndex,
  tsToMs,
} from "../../lib/replayAxis";
import { NoHourlyData } from "./NoHourlyData";

const SIGNALS: { value: Signal; label: string }[] = [
  { value: "vibration", label: "Vibration" },
  { value: "temperature", label: "Temperature" },
  { value: "motor_current", label: "Motor current" },
  { value: "discharge_pressure", label: "Discharge pressure" },
  { value: "feed", label: "Feed" },
  { value: "plant_rate", label: "Plant rate" },
];

// SPEC section 5.3: "Hourly trend with anomaly markers (section 5.5)." Replay rule (SPEC 4): the line
// ends at the replay date; the x-axis keeps the full record width, and the rest is an empty band.
export function HourlyTrendChart({
  tag,
  replayDate,
  hasHourlyCoverage,
  compact,
  signal: fixedSignal,
}: {
  tag: string;
  replayDate: string;
  hasHourlyCoverage: boolean;
  // No border/header/signal picker, a shorter chart showing `signal` for a rotating tile.
  // Click opens the full version with every signal available.
  compact?: boolean;
  signal?: Signal;
}) {
  const [pickedSignal, setSignal] = useState<Signal>("vibration");
  const signal = compact ? (fixedSignal ?? "vibration") : pickedSignal;
  const ref = useRef<HTMLDivElement>(null);
  const state = useFetch(() => getEquipmentSeries(tag, signal, replayDate), [tag, signal, replayDate]);
  const anomalyState = useFetch(
    () => getEquipmentAnomalies(tag, signal, replayDate),
    [tag, signal, replayDate],
  );

  useEffect(() => {
    if (!ref.current || state.status !== "ready") return;
    const { points, display_unit: unit, window_start: start, axis_hours: axis } = state.data;
    if (!start || axis === 0) return;

    const anomalies: AnomalyMarker[] = anomalyState.status === "ready" ? anomalyState.data.anomalies : [];
    const startMs = tsToMs(start);
    const values: (number | null)[] = new Array(axis).fill(null);
    const pointAt = new Map<number, HourlyPoint>();
    for (const p of points) {
      const i = hourIndex(start, p.ts);
      if (i >= 0 && i < axis) {
        values[i] = p.value;
        pointAt.set(i, p);
      }
    }
    const lastIndex = Math.min(axis - 1, replayEndIndex(start, replayDate));
    const labels = Array.from({ length: axis }, (_, i) =>
      i % TICK_EVERY_HOURS === 0 ? dayLabel(startMs + i * HOUR_MS) : "",
    );
    const offIndexRanges = offRanges(points).map(([a, b]) => [hourIndex(start, a), hourIndex(start, b)] as const);
    const anomalyRanges = anomalies.map((a) => [hourIndex(start, a.start_ts), hourIndex(start, a.end_ts)] as const);
    const inAnomaly = (i: number) => anomalyRanges.some(([a, b]) => i >= a && i <= b);

    const chart = echarts.init(ref.current);
    chart.setOption({
      grid: compact ? { left: 40, right: 8, top: 16, bottom: 20 } : { left: 44, right: 12, top: 24, bottom: 40 },
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
        name: unit ?? "",
        nameTextStyle: { fontSize: 10, color: colors.mute, align: "left" },
        axisLabel: { fontSize: 10, color: colors.mute },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: colors.line, type: "dashed" } },
      },
      series: [
        {
          type: "line",
          data: values,
          showSymbol: false,
          connectNulls: false,
          lineStyle: { color: colors.blue, width: 1.2 },
          markArea: {
            silent: true,
            data: [
              ...offIndexRanges.map(([a, b]) => [{ xAxis: a, itemStyle: { color: colors.canvas } }, { xAxis: b }]),
              ...anomalyRanges.map(([a, b]) => [
                { xAxis: a, itemStyle: { color: colors.red, opacity: 0.12 } },
                { xAxis: b },
              ]),
              ...(lastIndex < axis - 1
                ? [
                    [
                      {
                        xAxis: lastIndex + 0.5,
                        itemStyle: { color: colors.canvas },
                        label: { show: false },
                      },
                      { xAxis: axis - 1 },
                    ],
                  ]
                : []),
            ],
          },
          markPoint: {
            symbol: "pin",
            symbolSize: 28,
            itemStyle: { color: colors.red },
            label: { color: colors.paper, fontSize: 10 },
            data: anomalies.map((a) => ({
              coord: [hourIndex(start, a.start_ts), a.peak_value],
              value: "!",
            })),
          },
        },
      ],
      tooltip: {
        trigger: "axis",
        extraCssText: "box-shadow: 0 4px 16px rgba(14,17,22,0.16);",
        formatter: (params: { dataIndex: number; value: number | null }[]) => {
          const i = params[0].dataIndex;
          const point = pointAt.get(i);
          const suffix = unit ? ` ${unit}` : "";
          const anomaly = inAnomaly(i) ? '<br/><span style="color:' + colors.red + '">Anomaly</span>' : "";
          return `${hourTimestamp(startMs + i * HOUR_MS)}<br/>${params[0].value ?? "-"}${suffix} (${point?.run_status ?? ""})${anomaly}`;
        },
      },
    });

    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
    };
  }, [state, anomalyState, replayDate, compact]);

  const hasData = state.status === "ready" && !!state.data.window_start;

  if (compact) {
    const hasAnomaly = anomalyState.status === "ready" && anomalyState.data.anomalies.length > 0;
    return !hasHourlyCoverage ? (
      <NoHourlyData height={70} />
    ) : hasData ? (
      <div ref={ref} style={{ height: "100%", minHeight: 70 }} className={hasAnomaly ? "ring-1 ring-red" : ""} />
    ) : (
      <div className="flex h-[70px] items-center justify-center text-12 text-mute">
        {state.status === "error" ? "No data" : "Loading..."}
      </div>
    );
  }

  return (
    <div className="border border-line bg-paper">
      <div className="flex items-center justify-between border-b border-line px-2 py-1.5">
        <span className="flex items-center gap-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
          Hourly trend
          {anomalyState.status === "ready" && anomalyState.data.anomalies.length > 0 && (
            <span className="flex items-center gap-0.5 font-normal normal-case text-red">
              <span className="h-1 w-1 rounded-full bg-red" />
              {anomalyState.data.anomalies.length} anomal
              {anomalyState.data.anomalies.length === 1 ? "y" : "ies"}
            </span>
          )}
        </span>
        <select
          value={signal}
          onChange={(e) => setSignal(e.target.value as Signal)}
          className="border border-line bg-paper px-1 py-0.5 text-12 text-ink"
        >
          {SIGNALS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>
      {!hasHourlyCoverage ? (
        <NoHourlyData height={260} />
      ) : hasData ? (
        <div ref={ref} style={{ height: 260 }} />
      ) : state.status === "error" ? (
        <NoHourlyData height={260} />
      ) : (
        <div className="flex h-[260px] items-center justify-center text-13 text-mute">Loading...</div>
      )}
    </div>
  );
}

function offRanges(points: { ts: string; run_status: string }[]): [string, string][] {
  const ranges: [string, string][] = [];
  let start: string | null = null;
  for (let i = 0; i < points.length; i++) {
    if (points[i].run_status === "OFF" && start === null) start = points[i].ts;
    if (points[i].run_status !== "OFF" && start !== null) {
      ranges.push([start, points[i - 1].ts]);
      start = null;
    }
  }
  if (start !== null) ranges.push([start, points[points.length - 1].ts]);
  return ranges;
}
