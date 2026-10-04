// Shared x-axis arithmetic for charts that end at the replay date (SPEC 4: the app behaves as if
// today is the replay date). Timestamps from the API are "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD".
// They are parsed as UTC, so differences are exact hours and days.

export const HOUR_MS = 3600_000;
export const DAY_MS = 24 * HOUR_MS;

// Axis labels every three days, one per block of 72 hours from the start of the record.
export const TICK_EVERY_HOURS = 72;

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function tsToMs(ts: string): number {
  const [day, time = "00:00:00"] = ts.split(/[ T]/);
  const [y, m, d] = day.split("-").map(Number);
  const [hh = 0, mm = 0, ss = 0] = time.split(":").map(Number);
  return Date.UTC(y, m - 1, d, hh, mm, ss);
}

// Hour offset of a timestamp from the start of the record (0 = first hour).
export function hourIndex(start: string, ts: string): number {
  return Math.round((tsToMs(ts) - tsToMs(start)) / HOUR_MS);
}

// Hour offset of the last hour of the replay date (23:00). Charts use this as the right edge.
export function replayEndIndex(start: string, replayDate: string): number {
  return hourIndex(start, `${replayDate} 23:00:00`);
}

export function dayIndex(startDay: string, day: string): number {
  return Math.round((tsToMs(day) - tsToMs(startDay)) / DAY_MS);
}

export function dayLabel(ms: number): string {
  const d = new Date(ms);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
}

export function hourTimestamp(ms: number): string {
  return new Date(ms).toISOString().slice(0, 16).replace("T", " ");
}
