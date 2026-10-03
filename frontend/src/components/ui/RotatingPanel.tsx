import { useEffect, useState, type MouseEvent, type ReactNode } from "react";

export interface RotatingSlide {
  key: string;
  caption: string;
  content: ReactNode;
}

// One panel that cycles through several charts on its own, so a glance shows different trends
// without taking more room. Pauses while hovered, can be driven by the arrows or dots, and a
// click anywhere else opens the full version in a pop-up.
export function RotatingPanel({
  label,
  slides,
  onOpen,
  intervalMs = 7000,
}: {
  label: string;
  slides: RotatingSlide[];
  onOpen: () => void;
  intervalMs?: number;
}) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const count = slides.length;

  useEffect(() => {
    if (count <= 1 || paused) return;
    const id = window.setInterval(() => setIndex((i) => (i + 1) % count), intervalMs);
    return () => window.clearInterval(id);
  }, [count, paused, intervalMs]);

  if (count === 0) {
    return (
      <div className="flex h-full flex-col border border-line bg-paper">
        <Header label={label} />
        <div className="flex flex-1 items-center justify-center text-12 text-mute">No data</div>
      </div>
    );
  }

  const current = slides[Math.min(index, count - 1)];

  function step(delta: number, e: MouseEvent) {
    e.stopPropagation();
    setIndex((i) => (i + delta + count) % count);
  }

  return (
    <div
      className="flex h-full min-h-0 cursor-pointer flex-col border border-line bg-paper hover:bg-canvas/40"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onClick={onOpen}
    >
      <div className="flex shrink-0 items-center justify-between px-2 pt-1 text-12 uppercase tracking-wide text-mute">
        <span>
          {label}
          <span className="ml-1 normal-case tracking-normal text-ink">{current.caption}</span>
        </span>
        {count > 1 && (
          <span className="flex items-center gap-0.5">
            <button
              type="button"
              aria-label="Previous chart"
              onClick={(e) => step(-1, e)}
              className="px-1 text-mute hover:text-ink"
            >
              ‹
            </button>
            <button
              type="button"
              aria-label="Next chart"
              onClick={(e) => step(1, e)}
              className="px-1 text-mute hover:text-ink"
            >
              ›
            </button>
          </span>
        )}
      </div>
      <div className="min-h-0 flex-1 px-1 py-0.5">{current.content}</div>
      {count > 1 && (
        <div className="flex shrink-0 justify-center gap-1 pb-1">
          {slides.map((s, i) => (
            <button
              key={s.key}
              type="button"
              aria-label={`Show ${s.caption}`}
              onClick={(e) => {
                e.stopPropagation();
                setIndex(i);
              }}
              className={`h-1 w-1 rounded-full ${i === index ? "bg-ink" : "bg-line"}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function Header({ label }: { label: string }) {
  return <div className="px-2 pt-1 text-12 uppercase tracking-wide text-mute">{label}</div>;
}
