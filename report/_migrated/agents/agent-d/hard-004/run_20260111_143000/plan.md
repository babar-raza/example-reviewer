# HARD-004 Execution Plan: Security & Operations Documentation

**Agent**: D (Docs & Specs Specialist)
**Task ID**: HARD-004
**Run Folder**: reports/agents/agent-d/hard-004/run_20260111_143000/
**Started**: 2026-01-11 14:30:00

---

## Mission Summary

Create comprehensive, production-ready security and operations documentation for the Example Reviewer system, with special focus on GitHub Gist integration requirements.

---

## Current State Assessment

### Existing Documentation (Reviewed)

**Strong Areas**:
- docs/configuration.md - Good foundation for GITHUB_TOKEN setup
- docs/troubleshooting.md - Comprehensive troubleshooting guide (753 lines)
- README.md - Well-structured project overview
- specs/database-schema.md - Complete database documentation

**Gaps to Address**:
1. No dedicated security.md document
2. No comprehensive operations.md document (only mentioned in HARD-003)
3. Security best practices scattered across files
4. Cache/database monitoring commands not centralized
5. No clear security section in README

### Key Findings from Code Review

**GITHUB_TOKEN Usage** (from gist_service.py:61-166):
- Optional (public gists work without token)
- Used for rate limit increase: 60/hr → 5,000/hr
- Used in Authorization header: `token {github_token}`
- Scopes needed: Public gist read access (no explicit scopes required for public)

**Cache Structure** (from gist_service.py:59-64):
- Location: `cache/gists/` (or $CACHE_DIR)
- Current size: 22KB (small)
- Structure: `<gistid>.json` + `<gistid>/<filename>.raw`
- ETag support for conditional requests

**Database** (from database schema):
- Location: data/examples.db
- Current size: 196KB
- Tables: pages, snippets, validation_runs, validation_results, gists, gist_files
- WAL mode enabled

---

## Documentation Plan

### 1. docs/security.md (NEW)

**Sections to Create**:

#### 1.1 GitHub Token Management
- **Token Scopes**: What permissions are needed
  - Public gist access: NO scopes required (public read is default)
  - Fine-grained vs classic tokens
  - Minimal permissions principle
- **Token Creation**: Step-by-step with GitHub UI
- **Token Storage**: Environment variables, .env files (never commit)
- **Token Rotation**: Best practices for periodic rotation
- **Verification**: How to test token is working

#### 1.2 Rate Limiting
- **Without Token**: 60 requests/hour per IP
- **With Token**: 5,000 requests/hour
- **Rate Limit Headers**: X-RateLimit-Remaining, X-RateLimit-Reset
- **Handling**: Automatic detection (403 + remaining=0)
- **Monitoring**: How to check current rate limit status

#### 1.3 Data Security
- **Cached Data**: What is stored locally
- **Database Content**: What PII or sensitive data might exist
- **Access Control**: File permissions (600 for .db, 755 for cache)
- **Cleanup**: Secure deletion of old data
- **Network Security**: HTTPS-only API calls

#### 1.4 Secrets Management
- **Never Commit**: .gitignore verification
- **Environment Variables**: Best practice
- **CI/CD Integration**: Secure token injection
- **Key Vaults**: Production alternatives (AWS Secrets Manager, etc.)

#### 1.5 Vulnerability Management
- **Dependency Scanning**: Regular updates
- **Known Vulnerabilities**: Check for CVEs in dependencies
- **Disclosure Policy**: How to report security issues

**Validation Strategy**:
- Test token scope claims against GitHub API documentation
- Verify all commands work as documented
- Confirm .gitignore covers all secrets

---

### 2. docs/operations.md (NEW or UPDATE)

**Coordination with Agent B (HARD-003)**:
- Check if Agent B created operations.md for cache validation
- If exists: MERGE content with timestamp headers
- If not: Create fresh document

**Sections to Create**:

#### 2.1 Cache Management
- **Location**: cache/gists/ (configurable via CACHE_DIR)
- **Structure**: JSON metadata + raw file cache
- **Size Monitoring**:
  ```bash
  du -sh cache/gists/
  du -h cache/gists/ | sort -h | tail -20  # Largest files
  ```
- **Manual Cleanup**:
  ```bash
  rm -rf cache/gists/  # Safe - will be rebuilt
  rm cache/gists/<gistid>.json  # Remove specific gist
  ```
- **Cache Validation**: Integration with HARD-003 verify_cache()
- **Cache Behavior**: ETag conditional requests, 1-hour freshness

#### 2.2 Database Management
- **Location**: data/examples.db (SQLite + WAL)
- **Size Queries**:
  ```sql
  -- Database file size
  SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();

  -- Table row counts
  SELECT name, (SELECT COUNT(*) FROM main[name]) as rows FROM sqlite_master WHERE type='table';
  ```
- **Cleanup Queries**:
  ```sql
  -- Old validation runs (>30 days)
  DELETE FROM validation_runs WHERE started_at < date('now', '-30 days');

  -- Old gist cache (>90 days)
  DELETE FROM gists WHERE last_fetched_at < date('now', '-90 days');

  -- Orphaned snippets (if pages deleted)
  DELETE FROM snippets WHERE page_id NOT IN (SELECT page_id FROM pages);
  ```
- **Integrity Checks**:
  ```bash
  sqlite3 data/examples.db "PRAGMA integrity_check;"
  sqlite3 data/examples.db "PRAGMA foreign_key_check;"
  ```
- **Backup/Restore**:
  ```bash
  # Backup
  cp data/examples.db data/examples.db.backup-$(date +%Y%m%d)

  # Export to SQL
  sqlite3 data/examples.db .dump > backup.sql

  # Restore
  sqlite3 data/examples.db < backup.sql
  ```
- **Vacuum**: Reclaim space after deletions
  ```bash
  sqlite3 data/examples.db "VACUUM;"
  ```

#### 2.3 Monitoring & Health Checks
- **System Health**:
  ```bash
  # Check all components
  python --version
  dotnet --version
  sqlite3 --version
  curl -s http://localhost:11434/api/tags  # Ollama
  ```
- **Database Health**:
  ```sql
  -- Recent activity
  SELECT family, COUNT(*) as pages FROM pages GROUP BY family;
  SELECT status, COUNT(*) as count FROM snippets GROUP BY status;

  -- Latest validation run
  SELECT * FROM validation_runs ORDER BY started_at DESC LIMIT 1;
  ```
- **Performance Metrics**:
  ```sql
  -- Average compilation time
  SELECT AVG(compilation_time) as avg_compile_seconds FROM validation_results WHERE compilation_time IS NOT NULL;
  ```
- **Log Files**: Where to find logs (logs/ directory if configured)

#### 2.4 Troubleshooting Guide (5+ Common Issues)
1. **"No module named 'gist_service'"**
   - Cause: Python path issue, running from wrong directory
   - Solution: Run from repo root, check PYTHONPATH

2. **"GITHUB_TOKEN not found" or rate limit warnings**
   - Cause: Token not set or expired
   - Solution: Set environment variable, verify with curl

3. **"Rate limit exceeded"**
   - Cause: Hit 60/hr limit without token, or 5000/hr with token
   - Solution: Wait for reset, set/rotate token

4. **"Cache corrupted" or JSON parse errors**
   - Cause: Incomplete downloads, disk full during cache write
   - Solution: Run verify_cache() or delete cache directory

5. **"Database locked"**
   - Cause: Multiple processes accessing DB, or stale lock
   - Solution: Enable WAL mode, kill stale processes, increase timeout

6. **"Permission denied" on cache/data directories**
   - Cause: Wrong file permissions or ownership
   - Solution: chmod 755 cache/, chmod 600 data/examples.db

7. **"Network timeout" or connection errors**
   - Cause: GitHub API unreachable, proxy issues, firewall
   - Solution: Test connectivity, check proxy settings, verify HTTPS access

#### 2.5 Disaster Recovery
- **Database Corruption**: Recovery steps
- **Complete Data Loss**: Rebuilding from scratch
- **Cache Corruption**: Safe deletion and rebuild
- **Rollback**: Git-based content rollback

**Validation Strategy**:
- Test every bash command on actual system
- Test every SQL query against real database
- Verify file paths exist or document creation steps
- Capture output samples for documentation

---

### 3. docs/configuration.md (UPDATE)

**Changes to Make**:
- Add "See also" links at top:
  - [Security Guide](security.md) for GITHUB_TOKEN security best practices
  - [Operations Guide](operations.md) for cache/database management
- Add security callout in GITHUB_TOKEN section:
  - Link to security.md for token scope details
  - Emphasize never committing tokens

**Validation Strategy**:
- Preserve all existing content (safe-write protocol)
- Test links work after creation

---

### 4. README.md (UPDATE)

**Changes to Make**:
- Add "Documentation" section (before or after "Installation")
- List all documentation with descriptions:
  ```markdown
  ## Documentation

  - **[Configuration Guide](docs/configuration.md)** - Environment variables, cache, database setup
  - **[Security Guide](docs/security.md)** - GitHub token management, security best practices
  - **[Operations Guide](docs/operations.md)** - Cache/database management, monitoring, troubleshooting
  - **[Architecture](docs/architecture.md)** - System design and components
  - **[Development Guide](docs/development-guide.md)** - Contributing and development workflow
  - **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions
  ```

**Validation Strategy**:
- Verify all linked files exist
- Test all links

---

## Validation Checklist

**CRITICAL**: All commands/queries must be tested before documenting!

### Security.md Validation
- [ ] Token scope claims verified against GitHub API docs
- [ ] Token creation steps tested in GitHub UI
- [ ] Rate limit examples tested with curl
- [ ] All security recommendations are current best practices

### Operations.md Validation
- [ ] `du -sh cache/gists/` command works
- [ ] All SQL queries execute without errors
- [ ] Backup/restore procedure tested
- [ ] All troubleshooting solutions verified
- [ ] File paths exist or creation documented

### Configuration.md Validation
- [ ] Links work to new documents
- [ ] No existing content lost

### README.md Validation
- [ ] All documentation links work
- [ ] All linked files exist

---

## Artifacts to Create

1. **plan.md** (this file) - Complete ✓
2. **progress.md** - Live execution log with validation results
3. **evidence.md** - Final evidence with validation proofs
4. **self_review.md** - 12-dimension scoring

---

## Risk Assessment

**LOW RISK**: Documentation-only task with validation

**Potential Issues**:
1. Agent B may create operations.md during HARD-003 (COORDINATION NEEDED)
   - Mitigation: Check for existence, merge with timestamps
2. Commands may not work on Windows (Git Bash commands)
   - Mitigation: Test all commands, provide Windows alternatives
3. Database queries may fail on schema version mismatches
   - Mitigation: Test against actual database, document schema version

---

## Execution Order

1. **Check for Agent B's operations.md** (coordination)
2. **Create docs/security.md** with full validation
3. **Create/update docs/operations.md** with tested commands
4. **Update docs/configuration.md** with cross-links
5. **Update README.md** with documentation section
6. **Create progress.md** with validation evidence
7. **Create evidence.md** with final proofs
8. **Create self_review.md** with honest scoring

---

## Success Criteria Mapping

| Criterion | Implementation | Validation Method |
|-----------|----------------|-------------------|
| 1. GITHUB_TOKEN scopes documented | security.md §1.1 | GitHub API docs verification |
| 2. Cache monitoring commands | operations.md §2.1 | du command execution |
| 3. Database cleanup queries | operations.md §2.2 | SQL query execution |
| 4. Troubleshooting 5+ issues | operations.md §2.4 | Solution verification |
| 5. Security doc completeness | security.md all sections | Checklist review |
| 6. Links in README | README.md update | Link testing |

---

## Next Steps

1. Check if operations.md exists (Agent B coordination)
2. Begin security.md creation with research
3. Test all commands and queries
4. Document everything with evidence

---

**Status**: Plan complete, ready to execute
**Estimated Duration**: 2-3 hours
**Quality Gate**: All dimensions ≥4/5 required
