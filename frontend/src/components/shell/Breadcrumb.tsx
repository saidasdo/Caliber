import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams, useSearchParams } from "react-router-dom";
import { useAppState } from "../../state/AppStateContext";
import { useCurrentPlantCode } from "../../lib/useCurrentPlantCode";

const PAGE_LABEL: Record<string, string> = {
  "/diagnosis": "Diagnosis",
  "/actions": "Actions",
  "/backtest": "Backtest",
  "/data": "Data",
};

type Crumb = {
  key: string;
  label: string;
  to: string;
  options?: { label: string; to: string }[];
};

// SPEC section 7: "breadcrumb bar". Always the full hierarchy (All plants / plant /
// equipment), even when the URL only carries the deepest segment (an equipment route has no
// plantCode param), and each level with siblings opens a dropdown to jump sideways instead
// of only up.
export function Breadcrumb() {
  const location = useLocation();
  const params = useParams();
  const [searchParams] = useSearchParams();
  const plantCode = useCurrentPlantCode();
  const { overview } = useAppState();

  const plants = overview.status === "ready" ? overview.data.loss_by_plant : [];
  const equipmentByPlant = new Map<string, string[]>();
  if (overview.status === "ready") {
    for (const row of overview.data.priority_queue) {
      const list = equipmentByPlant.get(row.plant_code) ?? [];
      list.push(row.equipment_tag);
      equipmentByPlant.set(row.plant_code, list);
    }
  }

  const crumbs: Crumb[] = [{ label: "All plants", to: "/", key: "root" }];

  const effectivePlant = plantCode ?? (PAGE_LABEL[location.pathname] ? searchParams.get("plant") : null);
  if (effectivePlant) {
    crumbs.push({
      key: "plant",
      label: effectivePlant,
      to: `/plant/${effectivePlant}`,
      options: plants.map((p) => ({ label: p.plant_code, to: `/plant/${p.plant_code}` })),
    });
  }

  if (params.tag) {
    const siblings = plantCode ? (equipmentByPlant.get(plantCode) ?? []) : [];
    crumbs.push({
      key: "equipment",
      label: params.tag,
      to: `/equipment/${params.tag}`,
      options: siblings.map((tag) => ({ label: tag, to: `/equipment/${tag}` })),
    });
  }

  const pageLabel = PAGE_LABEL[location.pathname];
  if (pageLabel) {
    crumbs.push({ key: "page", label: pageLabel, to: location.pathname + location.search });
  }

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-13 text-mute">
      {crumbs.map((crumb, i) => (
        <span key={crumb.key} className="flex items-center gap-1">
          {i > 0 && <span className="text-line">/</span>}
          {i === crumbs.length - 1 ? (
            <span className="font-medium text-ink">{crumb.label}</span>
          ) : (
            <Link to={crumb.to} className="hover:text-blue">
              {crumb.label}
            </Link>
          )}
          {crumb.options && crumb.options.length > 1 && (
            <CrumbDropdown current={crumb.label} options={crumb.options} />
          )}
        </span>
      ))}
    </nav>
  );
}

function CrumbDropdown({
  current,
  options,
}: {
  current: string;
  options: { label: string; to: string }[];
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={`Switch from ${current}`}
        className="flex h-2 w-2 items-center justify-center text-mute hover:text-ink"
      >
        <svg viewBox="0 0 12 12" width="8" height="8" className="fill-current">
          <path d="M2 4l4 4 4-4z" />
        </svg>
      </button>
      {open && (
        <div className="absolute left-0 top-full z-10 mt-0.5 max-h-[280px] w-[140px] overflow-y-auto border border-line bg-paper shadow-md">
          {options.map((opt) => (
            <Link
              key={opt.to}
              to={opt.to}
              onClick={() => setOpen(false)}
              className={`block px-1.5 py-1 text-12 hover:bg-canvas ${
                opt.label === current ? "bg-canvas font-semibold text-ink" : "text-mute"
              }`}
            >
              {opt.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
