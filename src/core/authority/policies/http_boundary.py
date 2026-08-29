"""HTTP_ACCESS policy body (TC-EPIC1-06).

Closes F-001/F-003/F-004/F-005/F-008 (FINDINGS_REGISTER.md) at the HTTP transport
boundary in src/http_server.py:
  - F-001: ``if not API_KEY: return await call_next(request)`` fail-OPEN default --
    an unset EXAMPLE_REVIEWER_API_KEY (the shipped docker-compose.yml's actual state)
    served every route, including all MCP tools, with zero authentication.
  - ``auth_header == f"Bearer {API_KEY}"`` -- a ``==`` comparison is a byte-by-byte
    timing side-channel for brute-forcing the key.
  - No rate limiting or request-body-size limits existed anywhere in the module.

``http_access_policy`` is the single pure function of (resource, context) -> Decision
that ``auth_middleware`` (src/http_server.py) consults for every boundary check --
rate limit, body size, and auth -- so all three are audited under one capability
with distinguishing ``policy_id``s, the same pattern TC-EPIC1-02/03 used to collapse
the markdown-write and commit-git gates.

``validate_cors_config`` is a deliberately SEPARATE plain function, not a PDP policy:
it runs once at process startup (before any ``Request`` object exists), refusing to
start rather than gating a per-request decision. Per TC-EPIC1-06's own file-ownership
note this could have been folded into a per-request PDP check, but there is no
request to check against at import time -- this mirrors TC-EPIC1-04's disclosed
scope narrowing of WRITE_MARKDOWN's path allowlist, made explicit rather than
silently deviating from the taskcard's literal phrasing.
"""

from __future__ import annotations

import hmac
from typing import Any, Dict, List, Optional

from src.core.authority.capabilities import Capability
from src.core.authority.pdp import Decision


def http_access_policy(resource: Optional[str], context: Dict[str, Any]) -> Decision:
    """Compute the HTTP_ACCESS decision. ``resource`` is the request path.

    ``context["check"]`` selects which boundary concern this call evaluates
    (auth_middleware issues one check() call per concern, in order):
      - "rate_limit": context["rate_limited"] (bool) -- the token-bucket verdict,
        computed by the caller (rate-limiter state is per-process middleware
        state, not something a pure policy function should own).
      - "body_size": context["body_size"] (int), context["max_body_bytes"] (int).
      - "auth" (default): context["api_key"], context["auth_header"],
        context["dev_mode"] -- see below.

    Auth semantics (the core fix):
      - api_key unset + dev_mode False -> DENY, policy_id="http.auth.no_key_configured"
        (fail CLOSED -- the inverse of the deleted fail-open default).
      - api_key unset + dev_mode True -> ALLOW, policy_id="http.auth.dev_mode_open"
        (explicit, opt-in, loud escape hatch -- auth_middleware logs a warning on
        every request that takes this path).
      - api_key set -> constant-time hmac.compare_digest() against the bearer
        header; ALLOW/"http.auth.valid_key" or DENY/"http.auth.invalid_key".
    """
    check = context.get("check", "auth")

    if check == "rate_limit":
        if context.get("rate_limited"):
            return Decision(
                allow=False,
                reason="Rate limit exceeded for this client.",
                policy_id="http.rate_limit.exceeded",
                capability=Capability.HTTP_ACCESS,
                resource=resource,
            )
        return Decision(
            allow=True,
            reason="Within rate limit.",
            policy_id="http.rate_limit.ok",
            capability=Capability.HTTP_ACCESS,
            resource=resource,
        )

    if check == "body_size":
        body_size = context.get("body_size")
        max_body_bytes = context.get("max_body_bytes")
        if body_size is not None and max_body_bytes is not None and body_size > max_body_bytes:
            return Decision(
                allow=False,
                reason=f"Request body ({body_size} bytes) exceeds the configured maximum ({max_body_bytes} bytes).",
                policy_id="http.body_size.exceeded",
                capability=Capability.HTTP_ACCESS,
                resource=resource,
            )
        return Decision(
            allow=True,
            reason="Request body within the configured size limit.",
            policy_id="http.body_size.ok",
            capability=Capability.HTTP_ACCESS,
            resource=resource,
        )

    # check == "auth"
    api_key = context.get("api_key") or ""
    auth_header = context.get("auth_header") or ""
    dev_mode = bool(context.get("dev_mode", False))

    if not api_key:
        if dev_mode:
            return Decision(
                allow=True,
                reason=(
                    "EXAMPLE_REVIEWER_API_KEY is unset but EXAMPLE_REVIEWER_DEV_MODE=true "
                    "was explicitly set: serving without authentication."
                ),
                policy_id="http.auth.dev_mode_open",
                capability=Capability.HTTP_ACCESS,
                resource=resource,
            )
        return Decision(
            allow=False,
            reason=(
                "Server not configured for auth: EXAMPLE_REVIEWER_API_KEY is unset and "
                "EXAMPLE_REVIEWER_DEV_MODE is not enabled. Refusing to serve requests. "
                "Set EXAMPLE_REVIEWER_API_KEY, or explicitly set "
                "EXAMPLE_REVIEWER_DEV_MODE=true for local development only."
            ),
            policy_id="http.auth.no_key_configured",
            capability=Capability.HTTP_ACCESS,
            resource=resource,
        )

    # Constant-time comparison: closes the byte-by-byte timing side-channel the
    # original `==` comparison had (FINDINGS_REGISTER.md, this taskcard's finding).
    if hmac.compare_digest(auth_header, f"Bearer {api_key}"):
        return Decision(
            allow=True,
            reason="Valid bearer token.",
            policy_id="http.auth.valid_key",
            capability=Capability.HTTP_ACCESS,
            resource=resource,
        )
    return Decision(
        allow=False,
        reason="Missing or invalid bearer token.",
        policy_id="http.auth.invalid_key",
        capability=Capability.HTTP_ACCESS,
        resource=resource,
    )


def validate_cors_config(origins: List[str], allow_credentials: bool) -> None:
    """Refuse a wildcard-origin + credentialed-CORS combination.

    Raises ``RuntimeError`` if ``"*"`` is present in ``origins`` while
    ``allow_credentials`` is True -- that combination lets any origin make
    credentialed requests (some browsers already reject it outright; where
    permitted/misconfigured it is a real cross-origin credential leak).
    Called once at import time in src/http_server.py, not per-request.
    """
    if allow_credentials and "*" in origins:
        raise RuntimeError(
            "Refusing to start: CORS wildcard origin ('*') combined with "
            "allow_credentials=True lets any origin make credentialed requests. "
            "Set EXAMPLE_REVIEWER_CORS_ORIGINS to an explicit comma-separated "
            "allowlist of origins, or leave EXAMPLE_REVIEWER_CORS_ALLOW_CREDENTIALS "
            "unset/false."
        )
