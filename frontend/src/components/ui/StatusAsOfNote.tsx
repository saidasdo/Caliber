// The data has no incident status history, so any status shown during a replay is the status in
// the extract, not the status on the replay date. Said once, next to the status.
export function StatusAsOfNote() {
  return <p className="px-2 pt-1 text-12 italic text-mute">Status as of the data extract, Jul 2026</p>;
}
