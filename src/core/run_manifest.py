"""RunManifest (TC-EPIC3-05): the aggregator/consumer for "what actually
happened during this run", closing the gap that none of the following was
ever recorded anywhere queryable after a run completed:

  1. NuGet package version actually resolved and used (TC-EPIC3-01).
  2. Docker image digest actually built from (TC-EPIC3-02).
  3. LLM call reproducibility metadata (TC-EPIC3-03).
  4. The pattern_set_version in effect for the run (TC-EPIC3-04).
  5. Circuit-breaker state at run start (TC-EPIC3-06).

This module does not itself produce any of those five values -- it is a
pure consumer/aggregator, per this taskcard's own explicit non-goal. Every
field capture here is independently best-effort: a manifest capture failure
must never fail the underlying pipeline run (see each capture_*() function's
own try/except).

Deliberately NOT implemented in this initial landing (disclosed scope
narrowing): per_example_elapsed_seconds is present in the schema and always
queryable, but not yet populated with real per-example wall-clock data --
wiring that requires touching multiple compile/runtime-loop call sites
(orchestrator.py's existing per-example timeout tracking) that this
taskcard's own file-ownership section does not name as in scope. The field
exists so a future pass can populate it without a schema change.
"""

from __future__ import annotations

import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RunManifest(BaseModel):
    """Schema is intentionally permissive (no `extra="forbid"`): unlike the
    strict family/global config models, a manifest is an evidence record,
    not a validated user input -- a partially-populated manifest (some
    fields None because their upstream capture failed or that taskcard's
    field genuinely doesn't apply this run) is still a valid, useful record.
    """

    run_id: str
    git_sha: Optional[str] = None
    resolved_nuget_versions: Dict[str, str] = Field(default_factory=dict)
    docker_image_digest: Optional[str] = None
    pattern_set_version: Optional[int] = None
    circuit_breaker_state_at_start: Optional[Dict[str, Any]] = None
    llm_call_stats: Dict[str, Any] = Field(default_factory=dict)
    per_example_elapsed_seconds: Dict[str, float] = Field(default_factory=dict)
    created_at: str
    finalized_at: Optional[str] = None


def capture_git_sha(repo_root: Optional[Path] = None) -> Optional[str]:
    """Best-effort `git rev-parse HEAD`. Returns None (never raises) outside
    a git repo, in a shallow clone with no HEAD, or on any other failure --
    per this taskcard's own negative control, a git-sha lookup failure must
    still let the manifest be written with that field null."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root) if repo_root else None,
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        logger.debug(f"RunManifest: git_sha capture failed (non-fatal): {e}")
    return None


def capture_docker_image_digest() -> Optional[str]:
    """Best-effort read of this running container's own image digest.

    TC-EPIC3-02 pins the Dockerfile's base images by digest but does not
    itself inject a mechanism for a running container to introspect its OWN
    final image's digest (that would require baking it in at build time,
    e.g. via a build ARG/ENV, which is a disclosed follow-up scope item
    TC-EPIC3-02 explicitly deferred to this taskcard). Reads
    EXAMPLE_REVIEWER_IMAGE_DIGEST if a deployment chooses to inject one this
    way; returns None otherwise (including every non-containerized run,
    e.g. local dev / this repo's own test suite).
    """
    return os.getenv("EXAMPLE_REVIEWER_IMAGE_DIGEST")


def capture_resolved_nuget_versions(family_config: Optional[Any]) -> Dict[str, str]:
    """Best-effort extraction of TC-EPIC3-01's pinned versions from a family
    config. Returns {} (never raises) if family_config is None, has no
    nuget_config, or any package's version is unset (dev/exploration mode
    with restore_mode="floating" and no pin -- an empty/partial dict here is
    the honest answer, not an error)."""
    resolved: Dict[str, str] = {}
    try:
        nuget_config = getattr(family_config, "nuget_config", None)
        if nuget_config is None:
            return resolved
        primary = getattr(nuget_config, "primary_package", None)
        if primary is not None and primary.version:
            resolved[primary.name] = primary.version
        for pkg in getattr(nuget_config, "additional_packages", []) or []:
            if pkg.version:
                resolved[pkg.name] = pkg.version
    except Exception as e:
        logger.debug(f"RunManifest: resolved_nuget_versions capture failed (non-fatal): {e}")
    return resolved


def build_run_manifest(
    run_id: str,
    family_config: Optional[Any] = None,
    pattern_set_version: Optional[int] = None,
    circuit_breaker_state_at_start: Optional[Dict[str, Any]] = None,
    repo_root: Optional[Path] = None,
) -> RunManifest:
    """Capture the STATIC fields at run start (this taskcard's proposed
    design point 2) -- git_sha, resolved_nuget_versions, docker_image_digest,
    pattern_set_version, circuit_breaker_state_at_start. Never raises: every
    sub-capture is independently best-effort (see each capture_*() function).
    """
    return RunManifest(
        run_id=run_id,
        git_sha=capture_git_sha(repo_root),
        resolved_nuget_versions=capture_resolved_nuget_versions(family_config),
        docker_image_digest=capture_docker_image_digest(),
        pattern_set_version=pattern_set_version,
        circuit_breaker_state_at_start=circuit_breaker_state_at_start,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def finalize_run_manifest(manifest: RunManifest, llm_call_stats: Optional[Dict[str, Any]] = None) -> RunManifest:
    """Return a new RunManifest with the DYNAMIC fields set at run end (this
    taskcard's proposed design point 2's second half) -- llm_call_stats and
    finalized_at. Pure function: does not mutate the input manifest."""
    return manifest.model_copy(update={
        "llm_call_stats": llm_call_stats or {},
        "finalized_at": datetime.now(timezone.utc).isoformat(),
    })
