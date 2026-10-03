"""Phase 10 role/plant scope (SPEC section 5.11 extended): every request carries the acting
role and, where relevant, the plant it's scoped to, via X-Role / X-Plant headers. Missing
headers default to Executive with no plant scope, so every endpoint written before this phase
(and every existing test, which sends neither header) keeps seeing the full, unredacted data
it always has.
"""

from fastapi import Header, HTTPException

ROLES = ("Executive", "Plant manager", "Engineer")


class RoleScope:
    def __init__(self, role: str, plant: str | None, role_header_sent: bool):
        self.role = role
        self.plant = plant
        self.role_header_sent = role_header_sent


def get_role_scope(
    x_role: str | None = Header(default=None),
    x_plant: str | None = Header(default=None),
) -> RoleScope:
    role = x_role if x_role in ROLES else "Executive"
    return RoleScope(role=role, plant=x_plant, role_header_sent=x_role is not None)


def require_role(scope: RoleScope, *allowed: str) -> None:
    """Enforce a role for an action endpoint. Used only on the new phase-10 endpoints (propose,
    approve-proposal, close, escalate, comment, diagnosis review) that have no pre-phase-10
    caller to stay compatible with; the original approve/reject/status-update endpoints are
    left exactly as they were so existing tests and call sites keep working unmodified. A
    request with no X-Role header defaults to Executive (see get_role_scope) and is rejected
    here just like an explicit wrong role would be."""
    if scope.role not in allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{scope.role}' cannot perform this action (requires: {', '.join(allowed)})",
        )
