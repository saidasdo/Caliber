import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { WeeklySeriesParameter } from "../../lib/types";
import { colors } from "../../styles/tokens";

// SPEC section 5.3: "Weekly parameters: four small charts with alarm and trip lines." Replay rule
// (SPEC 4): the line ends at the replay week. The x-axis keeps the full record width (axisWeeks), and
// the weeks after the replay date are an empty grey band.
export function WeeklyParameterChart({
  series,
  axisWeeks,
  compact,
}: {
  series: WeeklySeriesParameter;
  axisWeeks: number;
  // No border/header/axis labels, a shorter chart: the real trend line for a summary tile.
  compact?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);

    const points = series.points;
    const n = Math.max(axisWeeks, points.length);
    const labels = Array.from({ length: n }, (_, i) => (points[i] ? points[i].week_date.slice(5, 10) : ""));
    const values = Array.from({ length: n }, (_, i) => points[i]?.value ?? null);

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
    const futureArea =
      points.length < n
        ? [
            [
              {
                xAxis: points.length - 0.5,
                itemStyle: { color: colors.canvas },
                label: { show: false },
              },
              { xAxis: n - 1 },
            ],
          ]
        : [];

    chart.setOption({
      grid: { left: 40, right: 34, top: 16, bottom: 14 },
      textStyle: { fontFamily: "IBM Plex Sans" },
      xAxis: {
        type: "category",
        data: labels,
        axisLabel: { show: false },
        axisLine: { lineStyle: { color: colors.line } },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        show: true,
        name: series.unit ?? "",
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
          lineStyle: { color: colors.blue, width: 1.5 },
          markLine: { symbol: "none", data: markLines },
          markArea: { silent: true, data: futureArea },
        },
      ],
      tooltip: {
        trigger: "axis",
        extraCssText: "box-shadow: 0 4px 16px rgba(14,17,22,0.16);",
        formatter: (params: { dataIndex: number; value: number }[]) => {
          const p = points[params[0].dataIndex];
          return `${p?.week_date ?? ""}<br/>${series.parameter}: ${params[0].value} ${series.unit ?? ""}`;
        },
      },
    });

    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
    };
  }, [series, axisWeeks]);

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
