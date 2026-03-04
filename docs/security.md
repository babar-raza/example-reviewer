# Security Guide

Security practices for the Example Reviewer system, covering token management,
data protection, and secrets handling.

---

## Table of Contents

1. [GitHub Token Management](#1-github-token-management)
2. [Rate Limiting](#2-rate-limiting)
3. [Data Security](#3-data-security)
4. [Secrets Management](#4-secrets-management)
5. [Vulnerability Disclosure](#5-vulnerability-disclosure)

---

## 1. GitHub Token Management

### What tokens are used

The pipeline uses GitHub tokens in two places:

| Purpose | Env var | Required? |
|---------|---------|-----------|
| Fetching public gists during discovery / backfill | Configured via `pat_env_var` in family JSON | Optional — increases rate limit from 60 → 5,000 req/hr |
| Publishing verified examples back to gists | Same `pat_env_var` | Required only when `upload_mode` ≠ `inline-only` |

The environment variable name is **per-family** and set in each `config/families/<family>.json`
under `gist.pat_env_var`. Examples:

```json
// config/families/zip.json
{ "gist": { "pat_env_var": "GITHUB_GIST_TOKEN" } }

// config/families/words.json
{ "gist": { "pat_env_var": "GITHUB_PAT" } }
```

The default when no family override is set is `GIST_PAT`.

### Token scopes

| Operation | Required scope |
|-----------|---------------|
| Reading public gists (discovery, backfill) | None — public read requires no scopes |
| Publishing / updating gists (`upload-on-change`, `upload-always`) | `gist` scope |

Use a fine-grained PAT with no permissions for read-only access. For publishing,
a classic PAT with only the `gist` scope is sufficient.

### Creating a token

1. Go to **GitHub Settings → Developer settings → Personal access tokens**
2. For read-only: fine-grained token, no permissions selected
3. For publishing: classic token, tick only the `gist` scope
4. Set expiry to 90 days; rotate before expiry

### Token storage

Store tokens in a `.env` file at the repo root (already in `.gitignore`):

```bash
# .env  —  never commit this file
GITHUB_GIST_TOKEN=ghp_your_token_here   # for zip family
GITHUB_PAT=ghp_your_token_here          # for words family
# Add one line per family as needed
```

Loaded automatically at startup via `python-dotenv`. For CI, use repository secrets.

### Token redaction in logs

The pipeline never logs full token values. `GistPublisher` reads the token via
`os.environ.get(token_env_var)` and logs only debug-level availability checks
(`"GistPublisher unavailable: no authentication token"`). No token value
ever appears in log output.

### Verifying your token

```bash
# Check rate limit without token (expect limit: 60)
curl https://api.github.com/rate_limit

# Check rate limit with token (expect limit: 5000)
curl -H "Authorization: token $GITHUB_GIST_TOKEN" https://api.github.com/rate_limit
```

---

## 2. Rate Limiting

| Auth | Requests/hour |
|------|--------------|
| None | 60 |
| With token | 5,000 |

The pipeline detects HTTP 403 + `X-RateLimit-Remaining: 0` and logs a warning.
Setting the family's `pat_env_var` token in your environment is the only action needed.

---

## 3. Data Security

### SQLite database

**Path**: `data/example_reviewer.db` (development) / `data/example_reviewer_prod.db` (production)

Both paths are gitignored (`/data/` in `.gitignore`).

**What is stored**: file paths, extracted code snippets, compile/runtime results,
LLM fix history, telemetry run records. No credentials or PII.

### Cache and workspace directories

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

### OneDrive / WSL note

SQLite WAL mode is incompatible with OneDrive sync and WSL DrvFS. Use
`--safe-workspace` to move the DB and workspace to a local path:

```bash
PYTHONPATH=. python -m src.cli.main run --family zip --safe-workspace
```

---

## 4. Secrets Management

### What must never be committed

The `.gitignore` already excludes:

```
.env
.env.local
/secrets/
/data/
```

Verify before pushing:

```bash
git log --all --full-history -S "ghp_" -- .   # should return nothing
```

### Required `.env` entries

```bash
# LLM provider key (required)
litellm_key=sk-your-api-key-here

# GitHub gist token — one per family, using that family's pat_env_var name
GITHUB_GIST_TOKEN=ghp_your_token_here    # zip
GITHUB_PAT=ghp_your_token_here           # words

# Optional: telemetry HTTP endpoint
TELEMETRY_API_URL=http://localhost:8765
```

### CI/CD

```yaml
# GitHub Actions example
- name: Run pipeline
  env:
    litellm_key: ${{ secrets.LITELLM_KEY }}
    GITHUB_GIST_TOKEN: ${{ secrets.GITHUB_GIST_TOKEN }}
  run: PYTHONPATH=. python -m src.cli.main run --family zip --max-examples 50
```

---

## 5. Vulnerability Disclosure

If you find a security vulnerability in this project:

1. **Do not** open a public GitHub issue
2. Email the maintainer directly with:
   - Description and steps to reproduce
   - Potential impact
   - Suggested fix (if any)
3. Expected response: acknowledgment within 48 hours, fix timeline based on severity

---

**Last Updated**: 2026-03-04
