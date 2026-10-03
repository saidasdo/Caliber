/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    // SPEC section 7: "Tailwind is allowed only with the custom tokens in section 7
    // (disable or ignore the default palette)." theme.colors is replaced wholesale
    // (not extended) so Tailwind's default reds/blues/purples/pastels do not exist
    // as utility classes at all.
    colors: {
      transparent: "transparent",
      current: "currentColor",
      white: "#FFFFFF",
      black: "#000000",
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
    },
    fontFamily: {
      // No Inter, Roboto or system-default sans-serif fonts (section 7 explicit ban).
      display: ["Archivo Variable", "Archivo", "sans-serif"],
      sans: ["IBM Plex Sans", "sans-serif"],
    },
    fontSize: {
      12: ["12px", { lineHeight: "16px" }],
      13: ["13px", { lineHeight: "17px" }],
      15: ["15px", { lineHeight: "19px" }],
      20: ["20px", { lineHeight: "24px" }],
      28: ["28px", { lineHeight: "32px" }],
      44: ["44px", { lineHeight: "48px" }],
    },
    borderRadius: {
      // Capped at 3px (section 7: "Radius 0 to 3px"). `full` is kept only for small round
      // indicator dots/status lights, never for panel or card corners.
      none: "0px",
      sm: "1px",
      DEFAULT: "2px",
      md: "3px",
      full: "9999px",
    },
    spacing: {
      0: "0px",
      1: "8px",
      2: "16px",
      3: "24px",
      4: "32px",
      5: "40px",
      6: "48px",
      7: "56px",
      8: "64px",
      px: "1px",
      0.5: "4px",
      1.5: "12px",
    },
    extend: {
      boxShadow: {
        // Reserved for popovers/menus only (section 7: "No shadows except popovers and menus").
        popover: "0 4px 16px rgba(14, 17, 22, 0.16)",
      },
    },
  },
  plugins: [],
};
