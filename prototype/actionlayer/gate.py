"""Permission grants + the deterministic gate (spec §4).

The gate is pure code. No LLM judgment is consulted. Checks run in order;
any failure -> REFUSED with a machine-readable reason.
"""
import fnmatch, os
from datetime import datetime, timezone
from .qafiya_shim import now_iso

def make_grant(*, user_id, action_types, target_pattern, constraints=None,
               requires_confirmation=None, expires_at=None):
    return {
        "type": "permission_grant",
        "user_id": user_id,
        "action_types": list(action_types),
        "target_pattern": target_pattern,
        "constraints": constraints or {},
        "requires_confirmation": requires_confirmation or [],
        "not_before": (constraints or {}).get("not_before"),
        "expires_at": expires_at,
    }

def _parse(ts):
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

def canonicalize(target, base):
    """Resolve target against base; return (abs_path, escaped_bool)."""
    p = os.path.realpath(os.path.join(base, target))
    base_r = os.path.realpath(base)
    escaped = not (p == base_r or p.startswith(base_r + os.sep))
    return p, escaped

def _matches(path, pattern, base):
    """fnmatch the path relative to the governed area against the grant pattern."""
    rel = os.path.relpath(path, base)
    pat = pattern.lstrip("/")
    return fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch("/" + rel, pattern)

def check_grant(grant, normalized, targets, base, now=None):
    """targets: list of raw target paths from the normalized action.
    Returns (ok, reason)."""
    now = now or datetime.now(timezone.utc)
    if grant is None:
        return False, "no_grant"
    if grant["action_types"] and normalized["action_type"] not in grant["action_types"]:
        return False, f"action_type_not_granted:{normalized['action_type']}"
    exp = _parse(grant.get("expires_at"))
    if exp and now > exp:
        return False, "grant_expired"
    nb = _parse(grant.get("not_before"))
    if nb and now < nb:
        return False, "grant_not_yet_valid"
    for t in targets:
        ap, escaped = canonicalize(t, base)
        if escaped:
            return False, f"path_escape:{t}"
        if not _matches(ap, grant["target_pattern"], base):
            return False, f"target_out_of_scope:{t}"
    return True, "ok"

def needs_confirmation(grant, reversibility_class, action_type):
    req = (grant or {}).get("requires_confirmation", [])
    return reversibility_class in req or action_type in req

def has_confirmation(record, kind):
    return any(c.get("kind") == kind for c in record.get("confirmations", []))
