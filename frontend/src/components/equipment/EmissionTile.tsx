import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { Emission } from "../../lib/types";
import { colors } from "../../styles/tokens";

// Compact tile: the day's CO2e estimate as the number, the last 7 days as bars. Only for
// motor-driven equipment; a heat exchanger has no motor drive (see DQ3), so it gets a plain note.
export function EmissionTile({ emission }: { emission: Emission }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || !emission.applicable || emission.series.length === 0) return;
    const chart = echarts.init(ref.current);
    chart.setOption({
      grid: { left: 44, right: 8, top: 8, bottom: 20 },
      xAxis: {
        type: "category",
        data: emission.series.map((p) => p.day),
        axisLabel: { fontSize: 10, color: colors.mute, formatter: (v: string) => v.slice(5) },
        axisLine: { lineStyle: { color: colors.line } },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        name: "kg CO2e",
        nameTextStyle: { fontSize: 10, color: colors.mute, align: "left" },
        axisLabel: { fontSize: 10, color: colors.mute },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: colors.line, type: "dashed" } },
      },
      tooltip: {
        trigger: "axis",
        formatter: (params: { name: string; value: number }[]) =>
          `${params[0].name}<br/>${Math.round(params[0].value).toLocaleString("en-US")} kg CO2e`,
      },
      series: [
        {
          type: "bar",
          data: emission.series.map((p) => p.kg_co2e),
          itemStyle: { color: colors.blue },
          barMaxWidth: 16,
        },
      ],
    });
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
    };
  }, [emission]);

  if (!emission.applicable) {
    return <p className="text-13 text-mute">Not applicable: no motor drive on this equipment.</p>;
  }
  if (emission.today_kg == null) {
    return <p className="text-13 text-mute">No motor current data for this date.</p>;
  }
  return (
    <div className="flex h-full flex-col">
      <div className="tabular font-display stretch-semi-expanded text-28 text-ink">
        {Math.round(emission.today_kg).toLocaleString("en-US")}
        <span className="ml-1 text-13 font-normal text-mute">kg CO2e today</span>
      </div>
      <div className="tabular text-12 text-mute">
        7 days: {emission.week_kg != null ? Math.round(emission.week_kg).toLocaleString("en-US") : "-"} kg
      </div>
      <div ref={ref} className="min-h-[40px] flex-1" />
    </div>
  );
}

// Pop-up: the daily figures and the factors behind them. The factors are placeholders until
// the team sets them from official sources (config.py, shown on the Data page).
export function EmissionDetail({ emission }: { emission: Emission }) {
  if (!emission.applicable) {
    return <p className="p-2 text-13 text-mute">Not applicable: no motor drive on this equipment.</p>;
  }
  const f = emission.factors;
  return (
    <div className="space-y-2 p-2">
      <p className="text-13 text-ink">{emission.label}</p>
      <p className="text-12 text-mute">
        kWh = sqrt(3) x {f.motor_voltage_kv} kV x current (A) x {f.power_factor} power factor, per ON hour.
        kg CO2e = kWh x {f.grid_emission_factor_kg_per_kwh} kg/kWh. Factors are placeholders until set from official
        sources.
      </p>
      <table className="w-full text-13">
        <thead>
          <tr className="text-left text-12 uppercase tracking-wide text-mute">
            <th className="py-1 font-semibold">Day</th>
            <th className="py-1 text-right font-semibold">kWh</th>
            <th className="py-1 text-right font-semibold">kg CO2e</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {emission.series.map((p) => (
            <tr key={p.day}>
              <td className="tabular py-1">{p.day}</td>
              <td className="tabular py-1 text-right">{Math.round(p.kwh).toLocaleString("en-US")}</td>
              <td className="tabular py-1 text-right">{Math.round(p.kg_co2e).toLocaleString("en-US")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
