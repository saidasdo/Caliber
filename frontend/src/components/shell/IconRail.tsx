import { useAppState } from "../../state/AppStateContext";
import { ResetDemoDataButton } from "./ResetDemoDataButton";

// SPEC section 7: "Slim black icon rail on the far left (48 px)".
export function IconRail() {
  const { productName } = useAppState();

  return (
    <div className="flex h-full w-6 flex-col items-center bg-ink py-1">
      <div
        className="flex h-4 w-4 items-center justify-center rounded bg-blue text-13 font-display font-bold text-white"
        title={productName}
      >
        {productName.charAt(0)}
      </div>
      <nav className="mt-4 flex flex-1 flex-col items-center gap-3">
        <RailIcon label="Assets" active>
          <path d="M3 3h7v7H3V3zm0 11h7v7H3v-7zm11-11h7v7h-7V3zm0 11h7v7h-7v-7z" />
        </RailIcon>
        <RailIcon label="Trends">
          <path d="M3 17l5-6 4 4 7-9" strokeWidth="2" fill="none" stroke="currentColor" />
        </RailIcon>
        <RailIcon label="Alerts">
          <path d="M12 2l10 18H2L12 2z" />
        </RailIcon>
      </nav>
      <div className="mb-2">
        <ResetDemoDataButton />
      </div>
    </div>
  );
}

function RailIcon({
  children,
  label,
  active = false,
}: {
  children: React.ReactNode;
  label: string;
  active?: boolean;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      className={`flex h-4 w-4 items-center justify-center rounded ${
        active ? "bg-white/10 text-white" : "text-mute hover:text-white"
      }`}
    >
      <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
        {children}
      </svg>
    </button>
  );
}
