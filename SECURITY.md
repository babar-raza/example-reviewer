# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.x     | Yes                |
| < 1.0   | No                 |

## Reporting a Vulnerability

If you discover a security vulnerability in Example Reviewer, please report it
responsibly:

1. **Do not** open a public issue.
2. Email the maintainers at the address listed in `CODEOWNERS` with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
3. You will receive an acknowledgement within 48 hours.
4. A fix will be developed and released as a patch version.

## Security Controls

### Path Guards

All file write operations are validated by `src/core/path_guard.py`:

- Test data directories (`test-data/`, `test-examples/`, `tests/fixtures/`) are
  strictly read-only at runtime.
- Path traversal attempts are blocked by prefix-based validation after
  normalization.
- Write operations are logged for audit trail.

### Provenance Guards

Markdown updates require provenance validation (`src/core/provenance_guard.py`):

- Only examples that have passed the verify-fix-verify pipeline can update
  source markdown.
- Each update carries a provenance signal with example ID, verification status,
  and code hash.

### LLM Interaction Safety

- LLM calls use structured output (via `instructor`) to prevent prompt
  injection from affecting pipeline state.
- The `--allow-md-write` flag must be explicitly set for any markdown mutation.
- Semantic drift detection prevents LLM-generated code from diverging too far
  from the original intent.

### Dependency Management

- Dependencies are pinned in `requirements.txt`.
- CI runs `pip-audit` to check for known vulnerabilities in dependencies.
- No secrets are stored in the repository; all credentials are passed via
  environment variables.

### Container Security

- The Dockerfile runs as a non-root user (`appuser`).
- Build tools are removed after compilation to reduce attack surface.
- Health checks are configured for liveness monitoring.
