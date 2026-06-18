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

## Token Management

The pipeline uses GitHub tokens in two places:

| Purpose | Env var | Required? |
|---------|---------|-----------|
| Fetching public gists during discovery / backfill | Configured via `pat_env_var` in family JSON | Optional — increases rate limit from 60 → 5,000 req/hr |
| Publishing verified examples back to gists | Same `pat_env_var` | Required only when `upload_mode` ≠ `inline-only` |

The environment variable name is **per-family** and set in each `config/families/<family>.json`
under `gist.pat_env_var`. The default when no family override is set is `GIST_PAT`.

### Token Scopes

| Operation | Required scope |
|-----------|---------------|
| Reading public gists (discovery, backfill) | None — public read requires no scopes |
| Publishing / updating gists (`upload-on-change`, `upload-always`) | `gist` scope |

### Creating a Token

1. Go to **GitHub Settings → Developer settings → Personal access tokens**
2. For read-only: fine-grained token, no permissions selected
3. For publishing: classic token, tick only the `gist` scope
4. Set expiry to 90 days; rotate before expiry

### Token Storage

Store tokens in a `.env` file at the repo root (already in `.gitignore`):

```bash
# .env  —  never commit this file
GITHUB_GIST_TOKEN=ghp_your_token_here   # for zip family
GITHUB_PAT=ghp_your_token_here          # for words family
```

Loaded automatically at startup via `python-dotenv`. For CI, use repository secrets.

### Token Redaction

The pipeline never logs full token values. `GistPublisher` reads the token via
`os.environ.get(token_env_var)` and logs only debug-level availability checks.

## Data Security

### SQLite Database

**Path**: `data/example_reviewer.db` (development) / `data/example_reviewer_prod.db` (production)

Both paths are gitignored (`/data/` in `.gitignore`).
**What is stored**: file paths, extracted code snippets, compile/runtime results,
LLM fix history, telemetry run records. No credentials or PII.

### Cache and Workspace Directories

All runtime-generated directories are gitignored:

```
/cache/          # HTTP response cache
/workspace/      # dotnet build scratch space
/workspaces/     # safe-workspace mode
/artifacts/      # test data, fixture registry
/logs/
/runs/
```

None of these contain secrets. They are safe to delete and will be rebuilt on next run.

### OneDrive / WSL Note

SQLite WAL mode is incompatible with OneDrive sync and WSL DrvFS. Use
`--safe-workspace` to move the DB and workspace to a local path:

```bash
PYTHONPATH=. python -m src.cli.main run --family zip --safe-workspace
```

## Secrets Management

### What Must Never Be Committed

The `.gitignore` already excludes `.env`, `.env.local`, `/secrets/`, `/data/`.

Verify before pushing:
```bash
git log --all --full-history -S "ghp_" -- .   # should return nothing
```

### Required `.env` Entries

```bash
# LLM provider key (required)
litellm_key=sk-your-api-key-here

# GitHub gist token — one per family, using that family's pat_env_var name
GITHUB_GIST_TOKEN=ghp_your_token_here    # zip
GITHUB_PAT=ghp_your_token_here           # words

# Optional: telemetry HTTP endpoint
TELEMETRY_API_URL=http://localhost:8765
```

### CI/CD Secrets

```yaml
# GitHub Actions example
- name: Run pipeline
  env:
    litellm_key: ${{ secrets.LITELLM_KEY }}
    GITHUB_GIST_TOKEN: ${{ secrets.GITHUB_GIST_TOKEN }}
  run: PYTHONPATH=. python -m src.cli.main run --family zip --max-examples 50
```

## Rate Limiting

| Auth | Requests/hour |
|------|--------------|
| None | 60 |
| With token | 5,000 |

The pipeline detects HTTP 403 + `X-RateLimit-Remaining: 0` and logs a warning.
Setting the family's `pat_env_var` token in your environment is the only action needed.
