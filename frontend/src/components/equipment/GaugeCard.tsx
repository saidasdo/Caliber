import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { Gauge } from "../../lib/types";
import { colors } from "../../styles/tokens";
import { NoHourlyData } from "./NoHourlyData";

interface Props {
  title: string;
  gauge: Gauge;
  min: number;
  max: number;
  unit: string;
  // [fraction 0-1, color] pairs, ascending, per SPEC 7 status colors (not a default palette).
  colorStops: [number, string][];
  formatValue?: (v: number) => string;
  // No border/header/footer, a smaller dial: the actual gauge visual for a summary tile
  // (click still opens the full GaugeCard, rendered the normal way, in a pop-up), not just a
  // bare number standing in for it.
  compact?: boolean;
}

// SPEC section 5.3: "Gauges like reference 1 (value, previous period, small sparkline)."
export function GaugeCard({ title, gauge, min, max, unit, colorStops, formatValue, compact }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const format = formatValue ?? ((v: number) => v.toFixed(1));

  useEffect(() => {
    if (!ref.current || !gauge.data_available || gauge.value === null) return;
    const chart = echarts.init(ref.current);
    chart.setOption({
      series: [
        {
          type: "gauge",
          min,
          max,
          startAngle: 210,
          endAngle: -30,
          radius: "100%",
          center: ["50%", "62%"],
          progress: { show: false },
          pointer: {
            show: true,
            length: "55%",
            width: 4,
            itemStyle: { color: colors.ink },
          },
          axisLine: {
            lineStyle: {
              width: 10,
              color: colorStops,
            },
          },
          splitLine: { show: false },
          axisTick: { show: false },
          axisLabel: { show: false },
          anchor: { show: true, size: 8, itemStyle: { color: colors.ink } },
          detail: {
            valueAnimation: true,
            formatter: () => format(gauge.value as number) + unit,
            fontFamily: "Archivo Variable",
            fontSize: compact ? 20 : 22,
            fontWeight: 700,
            color: colors.ink,
            offsetCenter: [0, "10%"],
          },
          data: [{ value: gauge.value }],
        },
      ],
    });
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
    };
  }, [gauge.value, gauge.data_available, min, max, unit, colorStops, format, compact]);

  const gaugeHeight = compact ? 90 : 130;

  if (compact) {
    return gauge.data_available && gauge.value !== null ? (
      <div ref={ref} style={{ height: "100%", minHeight: 110 }} />
    ) : (
      <NoHourlyData height={110} />
    );
  }

  return (
    <div className="border border-line bg-paper">
      <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        {title}
      </div>
      {gauge.data_available && gauge.value !== null ? (
        <>
          <div ref={ref} style={{ height: gaugeHeight }} />
          <div className="flex items-center justify-between px-2 pb-1">
            <span className="text-12 text-mute">
              Previous: <span className="tabular text-ink">{format(gauge.previous ?? 0)}{unit}</span>
            </span>
            <Sparkline data={gauge.sparkline} />
          </div>
        </>
      ) : (
        <NoHourlyData height={160} />
      )}
    </div>
  );
}

function Sparkline({ data }: { data: number[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || data.length < 2) return;
    const chart = echarts.init(ref.current);
    chart.setOption({
      grid: { left: 0, right: 0, top: 4, bottom: 0 },
      xAxis: { type: "category", show: false, data: data.map((_, i) => i) },
      yAxis: { type: "value", show: false, min: "dataMin", max: "dataMax" },
      series: [
        {
          type: "line",
          data,
          showSymbol: false,
          lineStyle: { color: colors.blue, width: 1.5 },
          areaStyle: { color: colors.blue, opacity: 0.08 },
        },
      ],
    });
    return () => chart.dispose();
  }, [data]);

  if (data.length < 2) return null;
  return <div ref={ref} style={{ width: 72, height: 24 }} />;
}
