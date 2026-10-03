// SPEC section 4: "When the replay date is outside an equipment's hourly window... show a
// clear gray 'No hourly data for this date' state. Never show zeros for missing data."
export function NoHourlyData({ height = 160 }: { height?: number }) {
  return (
    <div
      className="flex items-center justify-center bg-canvas text-13 text-mute"
      style={{ height }}
    >
      No hourly data for this date
    </div>
  );
}
