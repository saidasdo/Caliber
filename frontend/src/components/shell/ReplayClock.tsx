import { useAppState } from "../../state/AppStateContext";
import { formatDate } from "../../lib/format";

// SPEC section 4: "Global replay date in the top bar... Presets: '1 week before failure' for
// each of the five equipment."
export function ReplayClock() {
  const { replayDate, setReplayDate, presets } = useAppState();

  return (
    <div className="flex items-center gap-1.5 border border-line px-1.5 py-1">
      <svg viewBox="0 0 24 24" width="14" height="14" className="fill-mute">
        <path d="M12 2a10 10 0 100 20 10 10 0 000-20zm1 10.6l4.2 2.5-.7 1.2-5-3V6h1.5v6.6z" />
      </svg>
      <span className="text-12 uppercase tracking-wide text-mute">Replay</span>
      <input
        type="date"
        value={replayDate}
        onChange={(e) => setReplayDate(e.target.value)}
        className="tabular border-0 bg-transparent text-13 font-medium text-ink outline-none"
      />
      <span className="tabular hidden text-12 text-mute sm:inline">{formatDate(replayDate)}</span>
      {presets.length > 0 && (
        <select
          aria-label="Replay date presets"
          value=""
          onChange={(e) => {
            if (e.target.value) setReplayDate(e.target.value);
          }}
          className="border-0 border-l border-line bg-transparent pl-1.5 text-12 text-mute outline-none"
        >
          <option value="">Presets...</option>
          {presets.map((preset) => (
            <option key={preset.equipment_tag} value={preset.replay_date}>
              {preset.equipment_tag}: {preset.label}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
