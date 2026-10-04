import { useState, type ReactNode } from "react";
import type { KpiBand, OverviewResponse } from "../../lib/types";
import { formatHours } from "../../lib/format";
import { Money } from "../ui/Money";
import { Modal } from "../ui/Modal";

type Breakdown = "production" | "energy" | null;

// Tier 2: four tiles, one status line each. The line says whether the number went up or down, and is
// green when that is good for the business and red when it is bad (higherIsBetter decides which).
export function ExecKpiTiles({
  kpi,
  production,
  energy,
  emission,
}: {
  kpi: KpiBand;
  production: OverviewResponse["kpi_band"]["production_vs_normal"];
  energy: OverviewResponse["kpi_band"]["energy_proxy"];
  emission: OverviewResponse["kpi_band"]["emission_kg"];
}) {
  const [open, setOpen] = useState<Breakdown>(null);
  const rowsFromEmission = emission?.breakdown ?? [];

  const prodDelta = production?.value != null && production.previous != null ? production.value - production.previous : null;
  const downtimeDelta = kpi.downtime_hours.value - kpi.downtime_hours.previous;
  const lossDelta = kpi.loss_kusd ? kpi.loss_kusd.value - kpi.loss_kusd.previous : null;
  const emissionDelta = emission?.value != null && emission.previous != null ? emission.value - emission.previous : null;

  return (
    <>
      <div className="grid h-full grid-cols-4 gap-1.5">
        <Tile
          label="Production vs normal"
          onClick={production ? () => setOpen("production") : undefined}
          value={
            production?.value != null ? (
              <>{production.value.toFixed(1)}%</>
            ) : (
              <span className="text-20 text-mute">No hourly data</span>
            )
          }
          line={
            prodDelta != null
              ? changeLine(prodDelta, `${Math.abs(prodDelta).toFixed(1)} pts vs previous week`, true)
              : { text: "Average of machines with hourly data", tone: "text-mute" }
          }
        />

        <Tile
          label="Downtime"
          value={<>{formatHours(kpi.downtime_hours.value)}</>}
          line={changeLine(downtimeDelta, `${formatHours(Math.abs(downtimeDelta))} vs previous period`, false)}
        />

        <Tile
          label="Loss"
          value={kpi.loss_kusd ? <Money kusd={kpi.loss_kusd.value} /> : <span className="text-mute">-</span>}
          line={
            lossDelta != null
              ? changeLine(lossDelta, <><Money kusd={Math.abs(lossDelta)} /> vs previous period</>, false)
              : { text: "Not visible for this role", tone: "text-mute" }
          }
        />

        <Tile
          label="Energy and emission (estimate)"
          onClick={emission || energy ? () => setOpen("energy") : undefined}
          value={
            emission?.value != null ? (
              <>{Math.round(emission.value).toLocaleString("en-US")} kg CO2e</>
            ) : (
              <span className="text-20 text-mute">No data</span>
            )
          }
          line={
            emissionDelta != null
              ? changeLine(emissionDelta, `${Math.round(Math.abs(emissionDelta)).toLocaleString("en-US")} kg vs previous week`, false)
              : { text: "Estimate from motor current", tone: "text-mute" }
          }
        />
      </div>

      {open === "production" && production && (
        <Modal title="Production vs normal, per machine" onClose={() => setOpen(null)}>
          <BreakdownTable
            columns={["Machine", "Plant", "Now", "A week earlier"]}
            empty="No machine has hourly data on this replay date."
            rows={production.breakdown.map((b) => [
              b.equipment_tag,
              b.plant_code,
              `${b.value.toFixed(1)}%`,
              b.previous == null ? "-" : `${b.previous.toFixed(1)}%`,
            ])}
          />
          <p className="px-2 py-2 text-12 text-mute">
            Average over {production.count} machines with hourly data. 100% = the machine's normal rate.
          </p>
        </Modal>
      )}

      {open === "energy" && (
        <Modal title="Energy and emission, per machine" onClose={() => setOpen(null)}>
          <p className="px-2 pb-1 pt-2 text-12 font-semibold uppercase tracking-wide text-mute">Emission estimate</p>
          <BreakdownTable
            columns={["Machine", "Plant", "Replay week, kg CO2e"]}
            empty="No motor-driven machine has motor current data."
            rows={rowsFromEmission.map((b) => [
              b.equipment_tag,
              b.plant_code,
              Math.round(b.week_kg).toLocaleString("en-US"),
            ])}
          />
          <p className="px-2 py-2 text-12 text-mute">
            Estimate from motor current, not metered. The conversion factors are placeholders until the team sets
            them from official sources (Data page, Assumptions).
          </p>
          {energy && (
            <>
              <p className="px-2 pb-1 pt-2 text-12 font-semibold uppercase tracking-wide text-mute">Energy proxy</p>
              <BreakdownTable
                columns={["Machine", "Plant", "Replay week", "Week before", "7-day forecast"]}
                empty="No motor current data."
                rows={energy.breakdown.map((b) => [
                  b.equipment_tag,
                  b.plant_code,
                  b.week == null ? "-" : Math.round(b.week).toLocaleString("en-US"),
                  b.previous_week == null ? "-" : Math.round(b.previous_week).toLocaleString("en-US"),
                  b.forecast_direction ?? "-",
                ])}
              />
            </>
          )}
        </Modal>
      )}
    </>
  );
}

type Line = { text: ReactNode; tone: string };

// An arrow and the change, coloured by whether that change is good for the business.
// higherIsBetter=true: up is green. higherIsBetter=false: down is green.
function changeLine(delta: number, text: ReactNode, higherIsBetter: boolean): Line {
  if (delta === 0) return { text: <>– no change</>, tone: "text-mute" };
  const up = delta > 0;
  const good = up === higherIsBetter;
  return {
    text: (
      <>
        {up ? "↑" : "↓"} {text}
      </>
    ),
    tone: good ? "text-green" : "text-red",
  };
}

function Tile({
  label,
  value,
  line,
  onClick,
}: {
  label: string;
  value: ReactNode;
  line: Line;
  onClick?: () => void;
}) {
  const body = (
    <>
      <div className="text-12 uppercase tracking-wide text-mute">{label}</div>
      <div className="tabular font-display stretch-semi-expanded mt-0.5 text-28 font-bold leading-none text-ink">
        {value}
      </div>
      <div className={`tabular mt-1 truncate text-13 font-medium ${line.tone}`}>{line.text}</div>
    </>
  );
  const shell = "flex min-w-0 flex-col justify-center border border-line bg-paper px-2 py-1.5 text-left";
  return onClick ? (
    <button type="button" onClick={onClick} className={`${shell} hover:bg-canvas`}>
      {body}
    </button>
  ) : (
    <div className={shell}>{body}</div>
  );
}

function BreakdownTable({
  columns,
  rows,
  empty,
}: {
  columns: string[];
  rows: (string | number)[][];
  empty: string;
}) {
  return (
    <table className="w-full text-13">
      <thead>
        <tr className="border-b border-line text-left text-12 text-mute">
          {columns.map((c, i) => (
            <th key={c} className={`px-2 py-1 font-medium ${i >= 2 ? "text-right" : ""}`}>
              {c}
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="divide-y divide-line">
        {rows.map((r, i) => (
          <tr key={i}>
            {r.map((cell, j) => (
              <td
                key={j}
                className={`px-2 py-1.5 ${j === 0 ? "tabular font-medium text-ink" : j >= 2 ? "tabular text-right text-ink" : "text-mute"}`}
              >
                {cell}
              </td>
            ))}
          </tr>
        ))}
        {rows.length === 0 && (
          <tr>
            <td colSpan={columns.length} className="px-2 py-2 text-mute">
              {empty}
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
