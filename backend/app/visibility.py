"""Phase 10 server-side money redaction (SPEC section 5.11 / section 5 of the phase-10 brief):
"Money fields are removed in the backend response for Engineer, and for Plant manager on
plants outside their scope. The frontend must not receive values it should not show."

Works on the plain dicts every endpoint already returns, so no response model changes: walks
the structure, and at each dict tracks the plant_code it belongs to (its own "plant_code" key
if present, else the nearest ancestor's), so a row's own plant always wins over the scope it's
nested under. A similar_incidents row from a different plant than the equipment it's attached
to, for example, is judged on its own plant_code, not the equipment's.
"""

MONEY_KEYS = {"loss_kusd", "total_loss_kusd", "estimated_loss_kusd", "pot_loss_kusd", "act_loss_kusd"}


def can_see_money(role: str, plant_scope: str | None, plant_code: str | None) -> bool:
    if role == "Executive":
        return True
    if role == "Plant manager":
        return plant_scope is not None and plant_code is not None and plant_code == plant_scope
    return False  # Engineer


def redact_money(obj, role: str, plant_scope: str | None, inherited_plant: str | None = None):
    if role == "Executive":
        return obj  # no-op fast path; also what every pre-phase-10 caller (no X-Role) gets
    if isinstance(obj, dict):
        plant_here = obj.get("plant_code", inherited_plant)
        out = {}
        for key, value in obj.items():
            if key in MONEY_KEYS:
                if can_see_money(role, plant_scope, plant_here):
                    out[key] = value
                continue
            out[key] = redact_money(value, role, plant_scope, plant_here)
        return out
    if isinstance(obj, list):
        return [redact_money(v, role, plant_scope, inherited_plant) for v in obj]
    return obj
