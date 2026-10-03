import { useParams, useNavigate } from "react-router-dom";
import { useAppState } from "../../state/AppStateContext";
import { ROLE_CONFIG } from "../../roles/roleConfig";
import type { Role } from "../../lib/types";

const ROLES: Role[] = ["Executive", "Plant manager", "Engineer"];

// SPEC section 5.11 / phase 10 section 6: "Role switch in the top bar." Plant manager picks a
// plant (defaulted to ZCU in AppStateContext.setRole); Engineer gets the same control as an
// optional filter. Pinned to the bottom of the viewport as a floating popup rather than the
// header, so it stays reachable (and a visible reminder of whose eyes you're viewing through)
// no matter how far the page scrolls.
export function RoleSwitch() {
  const { role, setRole, selectedPlant, setSelectedPlant, overview, topAlertTag } = useAppState();
  const plants = overview.status === "ready" ? overview.data.loss_by_plant : [];
  const params = useParams<{ tag?: string }>();
  const navigate = useNavigate();

  function handleRoleChange(next: Role) {
    const openTag = params.tag;
    setRole(next);
    // Phase 10 section 6: "keep the selected equipment in context if one was open, so the
    // demo can show KO-3201 from three perspectives without navigating away." Otherwise go to
    // that role's own landing page.
    if (openTag) {
      navigate(`/equipment/${openTag}`);
    } else {
      navigate(ROLE_CONFIG[next].landingRoute({ selectedPlant, topAlertTag }));
    }
  }

  return (
    <div className="fixed bottom-2 left-1/2 z-50 flex -translate-x-1/2 items-center gap-1.5 border border-line bg-paper px-1.5 py-1.5 shadow-md">
      <span className="text-12 font-semibold uppercase tracking-wide text-mute">
        Viewing as {role}
        {selectedPlant ? ` · ${selectedPlant}` : role === "Engineer" ? " · all plants" : ""}
      </span>
      {(role === "Plant manager" || role === "Engineer") && (
        <select
          value={selectedPlant ?? ""}
          onChange={(e) => setSelectedPlant(e.target.value || null)}
          className="border border-line bg-paper px-1.5 py-1 text-12 text-ink"
          aria-label={role === "Plant manager" ? "Plant manager's plant" : "Engineer's plant filter (optional)"}
        >
          <option value="">{role === "Plant manager" ? "Pick a plant..." : "All plants"}</option>
          {plants.map((p) => (
            <option key={p.plant_code} value={p.plant_code}>
              {p.plant_code}
            </option>
          ))}
        </select>
      )}
      <div className="flex border border-line">
        {ROLES.map((r, i) => (
          <button
            key={r}
            type="button"
            onClick={() => handleRoleChange(r)}
            className={`px-1.5 py-1 text-12 font-medium ${i > 0 ? "border-l border-line" : ""} ${
              role === r ? "bg-ink text-white" : "bg-paper text-mute hover:text-ink"
            }`}
          >
            {r}
          </button>
        ))}
      </div>
    </div>
  );
}
