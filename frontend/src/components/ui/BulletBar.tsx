// ISA-101 style bullet graph: where a value sits against its limit, at a glance, instead of
// reading "value X vs limit Y" as a sentence. Shared by the diagnosis panel and the priority
// queue so a value-vs-limit reads the same way everywhere in the app.
export function BulletBar({
  value,
  limit,
  danger,
  inverted,
}: {
  value: number | null;
  limit: number | null;
  danger: boolean;
  /** On a solid-colored card (e.g. a pulsing Critical card), a red fill on a gray track
   * would disappear or clash; switch to a white-on-translucent treatment instead. */
  inverted?: boolean;
}) {
  const axisMax = Math.max(Math.abs(value ?? 0), Math.abs(limit ?? 0), 1) * 1.3;
  const valuePct = value != null ? Math.min((Math.abs(value) / axisMax) * 100, 100) : 0;
  const limitPct = limit != null ? Math.min((Math.abs(limit) / axisMax) * 100, 100) : null;

  return (
    <div className={`relative h-1.5 w-full ${inverted ? "bg-white/25" : "bg-canvas"}`}>
      <div
        className={`absolute inset-y-0 left-0 ${
          inverted ? "bg-white" : danger ? "bg-red" : "bg-line"
        }`}
        style={{ width: `${valuePct}%` }}
      />
      {limitPct != null && (
        <div
          className={`absolute inset-y-0 w-px ${inverted ? "bg-ink" : "bg-ink"}`}
          style={{ left: `${limitPct}%` }}
        />
      )}
    </div>
  );
}
