import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { WeeklySeriesParameter } from "../../lib/types";
import { colors } from "../../styles/tokens";

// SPEC section 5.3: "Weekly parameters: four small charts with alarm and trip lines, replay
// date marker."
export function WeeklyParameterChart({
  series,
  replayDate,
  compact,
}: {
  series: WeeklySeriesParameter;
  replayDate: string;
  // No border/header/axis labels, a shorter chart: the real trend line for a summary tile.
  compact?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);

    const weeks = series.points.map((p) => p.week_date);
    const values = series.points.map((p) => p.value);
    const replayIndex = weeks.reduce(
      (best, d, i) => (d <= replayDate ? i : best),
      -1,
    );

    const markLines: Record<string, unknown>[] = [];
    if (series.alarm !== null) {
      markLines.push({
        yAxis: series.alarm,
        lineStyle: { color: colors.amber, type: "dashed", width: 1 },
        label: { formatter: "alarm", fontSize: 10, color: colors.amber },
      });
    }
    if (series.trip !== null) {
      markLines.push({
        yAxis: series.trip,
        lineStyle: { color: colors.red, type: "dashed", width: 1 },
        label: { formatter: "trip", fontSize: 10, color: colors.red },
      });
    }

    chart.setOption({
      grid: { left: 36, right: 12, top: 10, bottom: 18 },
      textStyle: { fontFamily: "IBM Plex Sans" },
      xAxis: {
        type: "category",
        data: weeks,
        axisLabel: { show: false },
        axisLine: { lineStyle: { color: colors.line } },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        axisLabel: { fontSize: 10, color: colors.mute },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: colors.line, type: "dashed" } },
      },
      series: [
        {
          type: "line",
          data: values,
          showSymbol: false,
          lineStyle: { color: colors.blue, width: 1.5 },
          markLine: {
            symbol: "none",
            data: [
              ...markLines,
              ...(replayIndex >= 0
                ? [
                    {
                      xAxis: replayIndex,
                      lineStyle: { color: colors.ink, width: 1 },
                      label: { show: false },
                    },
                  ]
                : []),
            ],
          },
        },
      ],
      tooltip: {
        trigger: "axis",
        extraCssText: "box-shadow: 0 4px 16px rgba(14,17,22,0.16);",
        formatter: (params: { name: string; value: number }[]) =>
          `${params[0].name}<br/>${series.parameter}: ${params[0].value} ${series.unit ?? ""}`,
      },
    });

    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
    };
  }, [series, replayDate]);

  if (compact) {
    return <div ref={ref} style={{ height: "100%", minHeight: 70 }} />;
  }

  return (
    <div className="border border-line bg-paper">
      <div className="px-2 pt-1.5 text-12 font-medium text-ink">
        {series.parameter}
        <span className="ml-1 text-mute">{series.unit}</span>
      </div>
      <div ref={ref} style={{ height: 120 }} />
    </div>
  );
}
