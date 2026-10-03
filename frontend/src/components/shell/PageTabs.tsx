import { NavLink, useLocation } from "react-router-dom";
import { useCurrentPlantCode } from "../../lib/useCurrentPlantCode";

// SPEC section 7: "page tabs (Overview, Diagnosis, Actions, Backtest, Data)". Diagnosis,
// Actions and Backtest stay global, all-plant pages (the SPEC reason for Diagnosis is
// explicitly "don't open each equipment page one by one"), but from inside a Plant page they
// carry a ?plant= filter so the tab brings you to that plant's slice instead of losing your
// place. Data is dataset documentation, never plant-scoped. Overview resolves to the current
// plant's own page when one is in scope, since that page already is "the overview" for that
// plant. Which of these five are even shown depends on scope (see VISIBLE_KEYS below).
const TABS = [
  { key: "overview", label: "Overview", icon: GridIcon, scoped: false },
  { key: "diagnosis", label: "Diagnosis", icon: PulseIcon, scoped: true },
  { key: "actions", label: "Actions", icon: ChecklistIcon, scoped: true },
  { key: "backtest", label: "Backtest", icon: ClockIcon, scoped: true },
  { key: "data", label: "Data", icon: StackIcon, scoped: false },
] as const;

// Which tabs make sense depends on how deep you are: the "All plants" dashboard only needs
// awareness (what's happening, what needs a look); a plant gets the full working set; a
// single machine already shows its own diagnosis/actions/history inline on one page, so a
// separate tab strip there would just be a second way to the same content.
const VISIBLE_KEYS: Record<"global" | "plant" | "machine", readonly string[]> = {
  global: ["overview", "diagnosis"],
  plant: ["overview", "diagnosis", "actions", "backtest", "data"],
  machine: ["overview"],
};

export function PageTabs() {
  const plantCode = useCurrentPlantCode();
  const location = useLocation();
  const scope = location.pathname.startsWith("/equipment/") ? "machine" : plantCode ? "plant" : "global";
  const visibleTabs = TABS.filter((tab) => VISIBLE_KEYS[scope].includes(tab.key));

  return (
    <nav className="flex gap-1 border-b border-line bg-paper px-2 py-1">
      <div className="flex overflow-hidden rounded border border-line">
        {visibleTabs.map((tab, i) => {
          const href = hrefFor(tab, plantCode);
          const active = isActive(tab, location.pathname);
          return (
            <NavLink
              key={tab.key}
              to={href}
              className={`flex items-center gap-1 px-1.5 py-1 text-12 font-medium ${
                i > 0 ? "border-l border-line" : ""
              } ${active ? "bg-ink text-white" : "bg-paper text-mute hover:text-ink"}`}
            >
              <tab.icon />
              {tab.label}
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}

function hrefFor(tab: (typeof TABS)[number], plantCode: string | null): string {
  if (tab.key === "overview") return plantCode ? `/plant/${plantCode}` : "/";
  if (tab.key === "data") return "/data";
  return plantCode ? `/${tab.key}?plant=${plantCode}` : `/${tab.key}`;
}

function isActive(tab: (typeof TABS)[number], pathname: string): boolean {
  if (tab.key === "overview") {
    return pathname === "/" || pathname.startsWith("/plant/") || pathname.startsWith("/equipment/");
  }
  return pathname === `/${tab.key}`;
}

function GridIcon() {
  return (
    <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor">
      <path d="M3 3h7v7H3V3zm0 11h7v7H3v-7zm11-11h7v7h-7V3zm0 11h7v7h-7v-7z" />
    </svg>
  );
}

function PulseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M2 12h4l2-7 4 14 3-9 2 2h5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChecklistIcon() {
  return (
    <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="4" y="3" width="16" height="18" rx="1" />
      <path d="M8.5 12l2 2 4.5-4.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="8" />
      <path d="M12 7v5l4 2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function StackIcon() {
  return (
    <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor">
      <rect x="3" y="4" width="18" height="4" rx="1" />
      <rect x="3" y="10" width="18" height="4" rx="1" />
      <rect x="3" y="16" width="18" height="4" rx="1" />
    </svg>
  );
}
