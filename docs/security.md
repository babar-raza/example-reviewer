# Security Guide

This guide covers security best practices for the Example Reviewer system, with special focus on GitHub API token management and data protection.

---

## Table of Contents

1. [GitHub Token Management](#github-token-management)
2. [Rate Limiting](#rate-limiting)
3. [Data Security](#data-security)
4. [Secrets Management](#secrets-management)
5. [Vulnerability Management](#vulnerability-management)
6. [Security Checklist](#security-checklist)

---

## GitHub Token Management

### Token Requirements

The Example Reviewer uses the GitHub Gist API to fetch code examples from public gists.

**Important**: GitHub tokens are **optional** for this system. Public gists can be accessed without authentication.

**Why use a token?**
- Increase rate limit from 60 to 5,000 requests per hour
- Avoid IP-based rate limiting in shared environments
- Better monitoring and tracking of API usage

### Token Scopes

For reading **public gists**, you need **NO special scopes**.

**Classic Personal Access Token**:
- No scopes required (public read is default)
- Can create a token with zero scopes selected
- Token still provides rate limit increase

**Fine-Grained Personal Access Token** (Recommended):
- No permissions required for reading public gists
- More secure than classic tokens
- Can be scoped to specific repositories if needed

**Reference**: [GitHub Documentation - Scopes for OAuth apps](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps)

### Creating a GitHub Token

#### Option 1: Fine-Grained Token (Recommended)

1. Go to GitHub Settings: https://github.com/settings/tokens?type=beta
2. Click "Generate new token" (fine-grained)
3. Configure token:
   - **Token name**: `example-reviewer-gist-access`
   - **Expiration**: 90 days (rotate regularly)
   - **Repository access**: Public Repositories (read-only)
   - **Permissions**: None required for public gists
4. Click "Generate token"
5. **Copy token immediately** (you won't see it again)

#### Option 2: Classic Token

1. Go to GitHub Settings: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Configure token:
   - **Note**: `example-reviewer-gist-access`
   - **Expiration**: 90 days
   - **Scopes**: Leave all unchecked (no scopes needed)
4. Click "Generate token"
5. **Copy token immediately**

### Token Storage

**Environment Variables** (Recommended):

```bash
# Linux/Mac
export GITHUB_TOKEN="ghp_your_token_here"

# Windows Command Prompt
set GITHUB_TOKEN=ghp_your_token_here

# Windows PowerShell
$env:GITHUB_TOKEN="ghp_your_token_here"
```

**Persistent Storage** (for development):

Create a `.env` file in the repository root (already in .gitignore):

```bash
# .env
GITHUB_TOKEN=ghp_your_token_here
```

Load with python-dotenv:
```python
from dotenv import load_dotenv
load_dotenv()
```

**CI/CD Environments**:
- Use repository secrets (GitHub Actions: `secrets.GITHUB_TOKEN`)
- Use environment variables in CI configuration
- Never hardcode tokens in scripts

### Token Verification

Test your token is working:

```bash
# Without token (should show 60 requests/hour limit)
curl https://api.github.com/rate_limit

# With token (should show 5000 requests/hour limit)
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit
```

Expected output with token:
```json
{
  "resources": {
    "core": {
      "limit": 5000,
      "remaining": 5000,
      "reset": 1768149395
    }
  }
}
```

### Token Rotation

**Best Practices**:
1. Set token expiration to 90 days or less
2. Rotate tokens before expiration
3. Revoke old tokens after rotation
4. Document rotation dates in team calendar

**Rotation Process**:
1. Create new token (follow creation steps above)
2. Update environment variable or CI secret
3. Test system works with new token
4. Revoke old token: https://github.com/settings/tokens

### Token Revocation

**When to revoke immediately**:
- Token accidentally committed to git
- Suspicious API activity detected
- Team member leaves project
- System compromise suspected

**How to revoke**:
1. Go to: https://github.com/settings/tokens
2. Find the token in list
3. Click "Delete" or "Revoke"
4. Generate new token if still needed

---

## Rate Limiting

### Rate Limit Tiers

GitHub API enforces rate limits to prevent abuse:

| Authentication | Requests/Hour | Use Case |
|----------------|---------------|----------|
| None | 60 | Small-scale testing, single gist fetches |
| With Token | 5,000 | Production use, batch processing |

### Rate Limit Detection

The system automatically detects rate limiting:

```
[!] GitHub API rate limit exceeded. Set GITHUB_TOKEN env var for higher limits.
```

**HTTP Response Indicators**:
- Status code: `403 Forbidden`
- Header: `X-RateLimit-Remaining: 0`

### Checking Current Rate Limit

```bash
# Check rate limit status
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit

# Extract specific values
curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit | \
  python -c "import json, sys; d=json.load(sys.stdin); print(f\"Remaining: {d['resources']['core']['remaining']}/{d['resources']['core']['limit']}\")"
```

### Rate Limit Reset

When rate limit is exceeded, wait until reset time:

```python
import requests
import time
from datetime import datetime

response = requests.get('https://api.github.com/rate_limit',
                        headers={'Authorization': f'token {token}'})
reset_timestamp = response.json()['resources']['core']['reset']
reset_time = datetime.fromtimestamp(reset_timestamp)
print(f"Rate limit resets at: {reset_time}")
```

### Avoiding Rate Limits

**Best Practices**:
1. **Use token**: Always set GITHUB_TOKEN for production
2. **Cache aggressively**: System uses ETags and 1-hour cache
3. **Batch operations**: Process gists in bulk during off-peak hours
4. **Monitor usage**: Check rate limit before large operations

---

## Data Security

### Cached Data

**Location**: `cache/gists/` (or `$CACHE_DIR`)

**What is cached**:
- Gist API responses (JSON metadata)
- Raw file content (.cs files)
- ETags for conditional requests

**Sensitivity**:
- Public data only (public gists)
- No PII or secrets should be in gists
- Safe to backup or share within organization

**File Permissions**:
```bash
# Recommended permissions
chmod 755 cache/gists/           # Directory readable by all
chmod 644 cache/gists/*          # Files readable by all
```

### Database Content

**Location**: `data/examples.db`

**What is stored**:
- Page metadata (file paths, family)
- Code snippets (from documentation)
- Gist metadata (ID, owner, description)
- Validation results (compilation errors)

**Sensitivity**:
- No credentials or secrets
- Contains file paths (may reveal directory structure)
- Contains code snippets (public documentation)

**File Permissions**:
```bash
# Recommended permissions (more restrictive)
chmod 600 data/examples.db       # Owner read/write only
chmod 700 data/                  # Directory owner-only access
```

### Access Control

**Principle of Least Privilege**:
1. Database: Owner read/write only (600)
2. Cache: World-readable (644) - public data
3. Logs: Owner read/write only (600) - may contain errors
4. Config: Owner read/write only (600) - may contain paths

**Set permissions**:
```bash
chmod 700 data/ logs/
chmod 600 data/examples.db logs/*.log
chmod 755 cache/
chmod 644 cache/gists/*
```

### Data Cleanup

**Secure deletion** of old data:

```bash
# Delete cache (safe - will be rebuilt)
rm -rf cache/gists/

# Delete database (WARNING: destructive)
rm data/examples.db

# Secure overwrite (if paranoid)
shred -vfz -n 3 data/examples.db
```

**Automated cleanup** (recommended):
- See [Operations Guide - Database Cleanup](operations.md#database-cleanup)

### Network Security

**HTTPS Only**:
- All GitHub API calls use HTTPS
- No insecure HTTP fallback
- Certificate validation enabled

**No Proxy by Default**:
- System respects standard `HTTP_PROXY` environment variable
- Ensure proxy is trusted if configured

---

## Secrets Management

### Never Commit Tokens

**Verification**:
Check .gitignore includes:
```bash
# Verify .gitignore
grep -E "\.env|GITHUB_TOKEN|secrets" .gitignore
```

Expected entries:
```
.env
*.env
secrets/
```

**Check for leaked secrets**:
```bash
# Search for potential token patterns in git history
git log --all --full-history --source --pickaxe-regex -S "ghp_[a-zA-Z0-9]{36}" -- .

# Use git-secrets (install separately)
git secrets --scan
```

### Environment Variables

**Best Practice**:
- Use environment variables for tokens
- Never hardcode in source code
- Document required variables in README

**For shell sessions**:
```bash
# Add to ~/.bashrc or ~/.zshrc (but NOT to git)
export GITHUB_TOKEN="ghp_your_token_here"
```

**For systemd services**:
```ini
[Service]
Environment="GITHUB_TOKEN=ghp_your_token_here"
```

### CI/CD Integration

**GitHub Actions**:
```yaml
name: Example Reviewer
on: [push]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run discovery
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python src/cli.py discover --family zip
```

**GitLab CI**:
```yaml
variables:
  GITHUB_TOKEN: $CI_GITHUB_TOKEN  # Set in project settings
```

### Production Key Vaults

For production deployments, use managed secret services:

**AWS Secrets Manager**:
```python
import boto3
client = boto3.client('secretsmanager')
token = client.get_secret_value(SecretId='github-token')['SecretString']
```

**Azure Key Vault**:
```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

client = SecretClient(vault_url="https://myvault.vault.azure.net/",
                      credential=DefaultAzureCredential())
token = client.get_secret("github-token").value
```

**HashiCorp Vault**:
```bash
export GITHUB_TOKEN=$(vault kv get -field=token secret/github)
```

---

## Vulnerability Management

### Dependency Scanning

**Check for known vulnerabilities**:

```bash
# Python dependencies
pip install safety
safety check --json

# Or use pip-audit
pip install pip-audit
pip-audit
```

**GitHub Dependabot**:
- Enable Dependabot alerts in repository settings
- Review and merge security updates promptly

### Known Vulnerabilities

**Check CVE databases**:
- https://nvd.nist.gov/
- https://github.com/advisories

**Monitor dependencies**:
```bash
# List installed packages
pip list

# Check for updates
pip list --outdated
```

### Security Updates

**Apply updates promptly**:
```bash
# Update all packages
pip install --upgrade -r requirements.txt

# Update specific package
pip install --upgrade requests
```

**Test after updates**:
```bash
# Run test suite
pytest tests/

# Run smoke test
python src/cli.py discover --family test --max-pages 1
```

### Security Disclosure Policy

**If you find a security vulnerability**:

1. **DO NOT** open a public issue
2. Email security contact (add your email here)
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

**Response timeline**:
- Acknowledgment: Within 48 hours
- Initial assessment: Within 1 week
- Fix timeline: Based on severity

---

## Security Checklist

### Initial Setup
- [ ] Generate GitHub token with minimal scopes (none for public gists)
- [ ] Store token in environment variable or .env file
- [ ] Verify .gitignore includes .env and secrets
- [ ] Test token with rate limit check
- [ ] Set appropriate file permissions (600 for DB, 644 for cache)

### Regular Operations
- [ ] Monitor rate limit usage
- [ ] Rotate tokens every 90 days
- [ ] Review file permissions monthly
- [ ] Check for dependency updates weekly
- [ ] Backup database before major operations

### Before Deployment
- [ ] Scan for secrets in git history
- [ ] Run dependency vulnerability scan
- [ ] Review all file permissions
- [ ] Test without token (verify graceful degradation)
- [ ] Document token rotation procedure

### After Incident
- [ ] Revoke compromised token immediately
- [ ] Generate new token with different name
- [ ] Review access logs for suspicious activity
- [ ] Update all systems with new token
- [ ] Document incident and lessons learned

---

## Additional Resources

- [GitHub Authentication Documentation](https://docs.github.com/en/authentication)
- [GitHub REST API Rate Limiting](https://docs.github.com/en/rest/rate-limit)
- [GitHub Gist API Reference](https://docs.github.com/en/rest/gists/gists)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

---

**Last Updated**: 2026-01-11
**Next Review**: 2026-04-11 (quarterly)
