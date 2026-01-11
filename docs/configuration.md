# Configuration Guide

## Environment Variables

### GITHUB_TOKEN (Optional)
**Purpose**: Increase GitHub API rate limits for gist fetching.

**Default Rate Limits:**
- **Without token**: 60 requests/hour (per IP)
- **With token**: 5,000 requests/hour

**How to Set:**
```bash
# Linux/Mac
export GITHUB_TOKEN="ghp_your_personal_access_token_here"

# Windows (Command Prompt)
set GITHUB_TOKEN=ghp_your_personal_access_token_here

# Windows (PowerShell)
$env:GITHUB_TOKEN="ghp_your_personal_access_token_here"
```

**Creating a Token:**
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token
3. **Scopes required**: `gist` (read access)
4. Copy token and set environment variable

**Security Note:**
- Never commit tokens to git
- Use environment variables or secure key vaults
- Rotate tokens periodically

### CACHE_DIR (Optional)
**Purpose**: Override default gist cache location.

**Default**: `<repo_root>/cache/gists/`

**How to Set:**
```bash
export CACHE_DIR="/path/to/custom/cache"
```

## Directory Structure

### Cache Directory
**Path**: `cache/gists/` (relative to repo root)

**Contents:**
```
cache/gists/
  ├── <gistid>.json          # API response (with ETag)
  └── <gistid>/
      ├── file1.cs.raw       # Cached file content
      └── file2.cs.raw
```

**Cache Behavior:**
- Automatically created on first gist fetch
- ETags used for conditional requests
- Cache checked before API calls
- Stale cache (> 1 hour) triggers revalidation

**Cache Cleanup:**
Safe to delete `cache/gists/` directory:
- Gists will be re-fetched from API
- Database still retains gist metadata
- Content re-cached on next fetch

### Database
**Path**: `data/examples.db`

**Mode**: WAL (Write-Ahead Logging)

**Gist Tables:**
- `gists`: Metadata (id, owner, ETag, fetch status)
- `gist_files`: File content (code, hash, language)

**Migration:**
Schema version 2 adds gist tables.
- Old databases: tables created automatically on `init-db`
- New databases: full schema including gists

## CLI Configuration

### Default Behavior
- **Gist mode**: `inline-on-change` (replace only changed gists)
- **Dry run**: `false` (actually patch files)
- **Max pages**: unlimited
- **Max snippets**: unlimited

### Override via CLI Flags
```bash
# Dry run (preview changes without writing)
python src/cli.py patch --family zip --dry-run

# Gist mode options
python src/cli.py patch --family zip --gist-mode preserve         # Never replace
python src/cli.py patch --family zip --gist-mode inline-on-change # Default
python src/cli.py patch --family zip --gist-mode inline-always    # Always replace

# Limit scope
python src/cli.py discover --family zip --max-pages 10
python src/cli.py validate --family zip --max-snippets 50
```

## Family Configuration

**Path**: `config/families/<family>.json`

Each product family has a JSON configuration file:
```json
{
  "name": "zip",
  "package_id": "Aspose.Zip",
  "version": "24.x",
  "target_framework": "net6.0",
  "skip_patterns": [],
  "ollama_enabled": true
}
```

Family configs are independent of gist support (gist handling is automatic).

## Rate Limit Monitoring

Gist service logs rate limit warnings:
```
[!] GitHub API rate limit exceeded. Set GITHUB_TOKEN env var for higher limits.
```

Check current rate limit status:
```bash
# With token set
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit

# Without token
curl https://api.github.com/rate_limit
```

## Database Queries

### Check Gist Fetch Status
```sql
SELECT gist_id, owner, last_status, last_error, last_fetched_at
FROM gists
WHERE last_status != 'success';
```

### Find Skipped Gists
```sql
SELECT s.snippet_id, s.snippet_type, p.relative_path, s.status
FROM snippets s
JOIN pages p ON s.page_id = p.page_id
WHERE s.snippet_type = 'gist' AND s.status = 'skipped';
```

### Gist File Count
```sql
SELECT gist_id, COUNT(*) as file_count
FROM gist_files
GROUP BY gist_id;
```

## Troubleshooting

### Gists Not Being Fetched
1. Check GITHUB_TOKEN is set correctly
2. Verify network connectivity to api.github.com
3. Check rate limit status (see above)
4. Inspect `gists` table for error messages

### Cache Issues
1. Delete cache directory: `rm -rf cache/gists`
2. Re-run discovery: `python src/cli.py discover --family <family>`
3. Check disk space (cache grows with number of gists)

### Database Errors
1. Ensure schema version 2 is applied: `SELECT * FROM schema_version;`
2. Re-run init-db: `python src/cli.py init-db`
3. Check database file permissions

## Best Practices

1. **Set GITHUB_TOKEN** if processing > 60 gists/hour
2. **Use --dry-run** first to preview patches
3. **Commit before patching** to enable easy rollback
4. **Monitor rate limits** during large discovery runs
5. **Cache directory** can be shared across runs (saves API calls)
6. **Database backup** before major operations
