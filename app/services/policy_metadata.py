"""Descriptive metadata on ODRL policy documents (dcterms + owl:versionInfo).

The user supplies dcterms:creator, dcterms:publisher, dcterms:description and
owl:versionInfo. The dates are system-generated, as plain xsd:date strings
(YYYY-MM-DD):

- dcterms:created  set once, the first time the policy is stored
- dcterms:issued   set once, when the policy is published (stored / anchored)
- dcterms:modified set on every store
"""

from datetime import date
from typing import Any, Dict, Optional

DCTERMS_NS = "http://purl.org/dc/terms/"
OWL_NS = "http://www.w3.org/2002/07/owl#"

SYSTEM_DATE_KEYS = ("dcterms:created", "dcterms:modified", "dcterms:issued")
DEFAULT_VERSION = "1.0"


def _as_date(value: Any) -> Optional[str]:
    """Reduce an ISO date or datetime string to YYYY-MM-DD, or None if unusable."""
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def _ensure_prefixes(policy: Dict[str, Any]) -> None:
    """Make sure the dcterms and owl prefixes resolve in the policy's @context."""
    ctx = policy.get("@context")
    if ctx is None:
        ctx = []
    elif not isinstance(ctx, list):
        ctx = [ctx]

    declared = {k for entry in ctx if isinstance(entry, dict) for k in entry}
    missing = {p: ns for p, ns in (("dcterms", DCTERMS_NS), ("owl", OWL_NS)) if p not in declared}
    if missing:
        local = next((entry for entry in ctx if isinstance(entry, dict)), None)
        if local is None:
            ctx.append(dict(missing))
        else:
            local.update(missing)
    policy["@context"] = ctx


def stamp_policy_metadata(policy: Dict[str, Any], today: Optional[date] = None) -> Dict[str, Any]:
    """Set the system-generated dates and defaults on a policy (in place) and return it."""
    today_s = (today or date.today()).isoformat()

    policy["dcterms:created"] = _as_date(policy.get("dcterms:created")) or today_s
    policy["dcterms:issued"] = _as_date(policy.get("dcterms:issued")) or today_s
    policy["dcterms:modified"] = today_s

    if not policy.get("owl:versionInfo"):
        policy["owl:versionInfo"] = DEFAULT_VERSION

    _ensure_prefixes(policy)
    return policy
