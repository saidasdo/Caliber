import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts";
import { getEquipmentAnomalies, getEquipmentSeries } from "../../lib/api";
import { useFetch } from "../../lib/useFetch";
import type { AnomalyMarker, Signal } from "../../lib/types";
import { colors } from "../../styles/tokens";
import { NoHourlyData } from "./NoHourlyData";

const SIGNALS: { value: Signal; label: string }[] = [
  { value: "vibration", label: "Vibration" },
  { value: "temperature", label: "Temperature" },
  { value: "motor_current", label: "Motor current" },
  { value: "discharge_pressure", label: "Discharge pressure" },
  { value: "feed", label: "Feed" },
  { value: "plant_rate", label: "Plant rate" },
];

// SPEC section 5.3: "Hourly trend with anomaly markers (section 5.5)."
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
  const state = useFetch(() => getEquipmentSeries(tag, signal), [tag, signal]);
  const anomalyState = useFetch(() => getEquipmentAnomalies(tag, signal), [tag, signal]);

  useEffect(() => {
    if (!ref.current || state.status !== "ready") return;
    const { points } = state.data;
    const anomalies: AnomalyMarker[] = anomalyState.status === "ready" ? anomalyState.data.anomalies : [];
    const replayTs = `${replayDate} 23:59:59`;
    const replayIndex = points.reduce(
      (best, p, i) => (p.ts <= replayTs ? i : best),
      -1,
    );

    const chart = echarts.init(ref.current);
    chart.setOption({
      grid: compact ? { left: 4, right: 4, top: 4, bottom: 4 } : { left: 44, right: 12, top: 10, bottom: 40 },
      textStyle: { fontFamily: "IBM Plex Sans" },
      xAxis: {
        type: "category",
        data: points.map((p) => p.ts),
        show: !compact,
        axisLabel: { fontSize: 10, color: colors.mute, rotate: 30, formatter: (v: string) => v.slice(5, 10) },
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
      series: [
        {
          type: "line",
          data: points.map((p) => p.value),
          showSymbol: false,
          lineStyle: { color: colors.blue, width: 1.2 },
          markArea: {
            silent: true,
            data: [
              ...offRanges(points).map(([start, end]) => [
                { xAxis: start, itemStyle: { color: colors.canvas } },
                { xAxis: end },
              ]),
              ...anomalies.map((a) => [
                {
                  xAxis: a.start_ts,
                  itemStyle: { color: colors.red, opacity: 0.12 },
                },
                { xAxis: a.end_ts },
              ]),
            ],
          },
          markPoint: {
            symbol: "pin",
            symbolSize: 28,
            itemStyle: { color: colors.red },
            label: { color: colors.paper, fontSize: 10 },
            data: anomalies.map((a) => ({
              coord: [a.start_ts, a.peak_value],
              value: "!",
            })),
          },
          markLine: {
            symbol: "none",
            data:
              replayIndex >= 0
                ? [{ xAxis: replayIndex, lineStyle: { color: colors.ink, width: 1 }, label: { show: false } }]
                : [],
          },
        },
      ],
      tooltip: {
        trigger: "axis",
        extraCssText: "box-shadow: 0 4px 16px rgba(14,17,22,0.16);",
        formatter: (params: { name: string; value: number }[]) => {
          const idx = points.findIndex((p) => p.ts === params[0].name);
          const runStatus = idx >= 0 ? points[idx].run_status : "";
          const inAnomaly = anomalies.some((a) => params[0].name >= a.start_ts && params[0].name <= a.end_ts);
          return (
            `${params[0].name}<br/>${params[0].value} (${runStatus})` +
            (inAnomaly ? "<br/><span style=\"color:" + colors.red + "\">Anomaly</span>" : "")
          );
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

  if (compact) {
    const hasAnomaly = anomalyState.status === "ready" && anomalyState.data.anomalies.length > 0;
    return !hasHourlyCoverage ? (
      <NoHourlyData height={70} />
    ) : state.status === "ready" ? (
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
      ) : state.status === "ready" ? (
        <div ref={ref} style={{ height: 260 }} />
      ) : state.status === "error" ? (
        <NoHourlyData height={260} />
      ) : (
        <div className="flex h-[260px] items-center justify-center text-13 text-mute">
          Loading...
        </div>
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
