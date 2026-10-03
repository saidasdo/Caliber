// SPEC section 7 color tokens, as plain values for ECharts (canvas rendering cannot read
// CSS custom properties). Keep in sync with tailwind.config.js and src/styles/tokens.css.
export const colors = {
  ink: "#0E1116",
  paper: "#FFFFFF",
  canvas: "#F1F2F4",
  line: "#D3D6DB",
  mute: "#5F6670",
  blue: "#0A5CD6",
  green: "#1A7A30",
  amber: "#F2B300",
  orange: "#BB4F0C",
  red: "#D7191C",
  black: "#000000",
} as const;

export type StatusColor = "green" | "amber" | "orange" | "red" | "black" | "mute";

export const statusColor: Record<StatusColor, string> = {
  green: colors.green,
  amber: colors.amber,
  orange: colors.orange,
  red: colors.red,
  black: colors.black,
  mute: colors.mute,
};
