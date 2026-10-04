import type { PriorityLabel } from "./types";

// Shared full-strength status card treatment for the Overview priority queue and the
// Diagnosis tab, so the same alert reads the same way in both places. Low/no-priority cards
// stay plain: color is reserved for what actually needs attention. Critical, High and Medium
// use solid (not tinted) backgrounds per their own hue, which means body text has to flip to
// whatever actually contrasts against that fill, and the PriorityChip badge has to switch to
// an inverted white pill since its own solid color would otherwise disappear into a
// same-colored card.
export interface PriorityCardStyle {
  container: string;
  heading: string;
  body: string;
  invertedChip: boolean;
}

const PLAIN: PriorityCardStyle = {
  container: "",
  heading: "text-ink",
  body: "text-mute",
  invertedChip: false,
};

const STYLES: Record<PriorityLabel, PriorityCardStyle> = {
  Critical: {
    container: "priority-critical-pulse",
    heading: "text-white",
    body: "text-white/85",
    invertedChip: true,
  },
  High: {
    container: "bg-orange",
    heading: "text-white",
    body: "text-white/85",
    invertedChip: true,
  },
  Medium: {
    container: "bg-amber",
    heading: "text-ink",
    body: "text-ink/75",
    invertedChip: true,
  },
  Normal: PLAIN,
};

export function priorityCardStyle(label: PriorityLabel | null | undefined): PriorityCardStyle {
  return label ? STYLES[label] : PLAIN;
}
