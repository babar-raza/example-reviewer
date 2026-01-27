# SQLite Locking Hardening Guide

## Overview

This document describes the SQLite locking issues encountered during Phase 2 E2E validation and the comprehensive hardening measures implemented to prevent database lock failures.

## Problem Statement

During Phase 2 E2E testing, the pipeline encountered frequent `sqlite3.OperationalError: database is locked` errors during discovery and concurrent write operations. Root cause analysis identified two primary issues:

### 1. Risky Filesystem Environments

SQLite has known issues with certain filesystem configurations:

- **OneDrive**: Cloud sync can interfere with SQLite's file locking mechanism, causing corruption and deadlocks
- **WSL DrvFS** (`/mnt/*` paths): Windows filesystem mounted in WSL has incomplete POSIX file locking support
- **Network Drives**: Remote filesystems often lack proper file locking semantics

### 2. Concurrent Write Contention

The discovery phase spawns multiple operations that can write to the database concurrently:
- Example record insertion
- Run state tracking
- Compile/runtime attempt logging

Without proper synchronization, these concurrent writes caused lock timeouts and failures.

## Solutions Implemented

### Task 1: Safe Workspace Mode

A first-class safe workspace mode that automatically relocates database and artifacts to filesystem locations known to work well with SQLite.

#### CLI Flags

```bash
--safe-workspace
```
Enables safe workspace mode. Automatically creates a workspace directory outside OneDrive/DrvFS:
- **Windows**: `%LOCALAPPDATA%\ExampleReviewer\workspaces\<timestamp>\`
- **Linux/WSL**: `~/.cache/example_reviewer/workspaces\<timestamp>/`

```bash
--safe-root <path>
```
Override the default safe workspace root with a custom path.

#### Directory Structure

When `--safe-workspace` is enabled, the following structure is created:

```
<safe_root>/
├── db/
│   └── example_reviewer.db
├── artifacts/
│   └── (pipeline artifacts)
└── workspace/
    └── (workspace copies and runtime files)
```

#### Usage Examples

```bash
# Use default safe workspace (recommended for OneDrive/DrvFS environments)
python -m src.cli.main run --family zip --safe-workspace --deterministic --seed 12345

# Use custom safe workspace root
python -m src.cli.main run --family zip --safe-workspace --safe-root /tmp/my_workspace

# E2E harness with safe workspace
python tools/run_e2e_zip.py --family zip --seed 12345 --runs 3 --safe-workspace
```

### Task 2: SQLite Configuration Hardening

#### 2A: Enforced WAL Mode and Pragmas

All database connections now enforce optimal SQLite settings:

```sql
PRAGMA journal_mode=WAL;         -- Write-Ahead Logging for concurrent reads
PRAGMA synchronous=NORMAL;       -- Balance durability and performance
PRAGMA temp_store=MEMORY;        -- Store temp tables in memory
PRAGMA busy_timeout=<config_ms>; -- Configurable lock timeout
PRAGMA foreign_keys=ON;          -- Maintain referential integrity
```

**Benefits:**
- **WAL mode** allows concurrent readers during writes
- **NORMAL synchronous** reduces fsync overhead without compromising safety
- **MEMORY temp_store** avoids temp file contention
- **Configurable busy_timeout** allows tuning for slow filesystems

#### CLI Flags

```bash
--sqlite-busy-timeout-ms <milliseconds>
```
Configure SQLite busy timeout (default: 120000ms = 2 minutes)

```bash
--sqlite-wal / --no-sqlite-wal
```
Enable/disable WAL mode (default: enabled, recommended to keep enabled)

#### Usage Examples

```bash
# Increase timeout for slow network drives
python -m src.cli.main run --family zip --sqlite-busy-timeout-ms 300000

# Disable WAL (not recommended, for debugging only)
python -m src.cli.main run --family zip --no-sqlite-wal
```

#### 2B: Single-Writer Protection

Implemented `threading.RLock` in the `Database` class to serialize all write operations within a single process:

```python
# In database.py
self._write_lock = threading.RLock()

# All write methods now protected
def save_example(self, example, run_id=None):
    with self._write_lock:
        with self.get_connection() as conn:
            # ... write operations
```

**Protected Methods:**
- `save_example()`
- `update_example_status()`
- `save_example_run_state()`
- `save_compile_attempt()`
- `save_runtime_attempt()`
- And all other write operations

**Benefits:**
- Prevents concurrent writes from causing lock contention
- Works seamlessly with WAL mode's concurrent reads
- No application-level deadlocks

#### 2C: Transaction Granularity

All transactions are kept short and scoped:
- Each example insertion is its own transaction (commits quickly)
- No loops wrapped in single transactions
- Status updates are individual operations

This ensures locks are held for minimal duration, reducing contention.

### Task 3: Regression Prevention Tests

Created `tests/test_sqlite_locking.py` with comprehensive concurrent access tests:

#### Test: Concurrent Writers (3A)

Spawns 8 threads, each writing 25 examples concurrently:
- Verifies no `database is locked` errors
- Confirms all writes succeed
- Validates run state consistency

```bash
pytest tests/test_sqlite_locking.py::TestSQLiteLocking::test_concurrent_writers_single_process -v
```

#### Test: WAL Mode Applied (3B)

Verifies WAL mode is correctly configured:

```bash
pytest tests/test_sqlite_locking.py::TestSQLiteLocking::test_wal_mode_applied -v
```

#### Test: Pragma Enforcement

Validates all required pragmas are applied on every connection.

#### Running Tests

```bash
# Run all SQLite locking tests
pytest tests/test_sqlite_locking.py -v

# Run with verbose output
pytest tests/test_sqlite_locking.py -v -s
```

### Task 4: Diagnostic Tool

Created `tools/diagnose_sqlite_lock.py` for troubleshooting:

```bash
# Basic diagnostics
python tools/diagnose_sqlite_lock.py --db-path data/example_reviewer.db

# With stress test (recommended for debugging lock issues)
python tools/diagnose_sqlite_lock.py --db-path data/example_reviewer.db --stress-test

# Custom stress test parameters
python tools/diagnose_sqlite_lock.py --stress-test --threads 16 --writes 100

# Save report to file
python tools/diagnose_sqlite_lock.py --stress-test --output reports/sqlite_diag.txt
```

**What It Checks:**
1. **Filesystem Risk**: Detects OneDrive, DrvFS, network drives
2. **PRAGMA Settings**: Verifies all required pragmas
3. **Stress Test**: Concurrent write test with detailed error reporting

**Output Example:**

```
================================================================================
SQLite Lock Diagnostic Report
================================================================================
Generated: 2026-01-22T10:30:00.000000
Database: data/example_reviewer.db

--------------------------------------------------------------------------------
Filesystem Risk Assessment
--------------------------------------------------------------------------------
Risk Level: HIGH
Reason: OneDrive

Recommendations:
  - OneDrive syncing can cause SQLite database corruption and locking
  - Use --safe-workspace flag to move DB outside OneDrive
  - Or disable OneDrive syncing for this directory

--------------------------------------------------------------------------------
SQLite PRAGMA Settings
--------------------------------------------------------------------------------
  journal_mode: wal
  synchronous: 1
  temp_store: 2
  busy_timeout: 120000
  foreign_keys: 1

--------------------------------------------------------------------------------
Write Stress Test Results
--------------------------------------------------------------------------------
Threads: 8
Writes per thread: 50
Total expected writes: 400
Actual writes: 400
Duration: 2.34 seconds
Success: YES

No errors detected!
================================================================================
```

## Troubleshooting Guide

### Symptom: "database is locked" errors during discovery

**Diagnosis:**
```bash
python tools/diagnose_sqlite_lock.py --db-path data/example_reviewer.db --stress-test
```

**Common Causes:**
1. Database on OneDrive/DrvFS
2. Low busy_timeout value
3. WAL mode disabled
4. External process holding lock

**Solutions:**
1. **Use safe workspace mode:**
   ```bash
   python -m src.cli.main run --family zip --safe-workspace
   ```

2. **Increase timeout:**
   ```bash
   python -m src.cli.main run --family zip --sqlite-busy-timeout-ms 300000
   ```

3. **Check WAL mode is enabled:**
   ```bash
   sqlite3 data/example_reviewer.db "PRAGMA journal_mode;"
   # Should return: wal
   ```

4. **Close other connections:**
   - Close any DB browser tools
   - Stop other pipeline processes
   - Check for zombie processes

### Symptom: Slow performance with safe workspace

**Diagnosis:**
Safe workspace should be FASTER due to local filesystem, but if slow:

1. **Check disk I/O:**
   ```bash
   # Linux
   iostat -x 1

   # Windows
   perfmon /res
   ```

2. **Verify safe workspace location:**
   - Should NOT be on network drive
   - Should NOT be on encrypted volume with poor I/O
   - Should be on SSD if available

### Symptom: Tests pass but E2E still fails

**Diagnosis:**
1. **Run diagnostic during actual E2E:**
   ```bash
   # In one terminal
   python tools/run_e2e_zip.py --family zip --seed 12345 --runs 1

   # In another terminal (while running)
   python tools/diagnose_sqlite_lock.py --db-path data/example_reviewer.db
   ```

2. **Check for external interference:**
   - Antivirus scanning database file
   - Backup software
   - File indexing services

3. **Enable verbose logging:**
   ```bash
   python -m src.cli.main run --family zip --safe-workspace --verbose
   ```

## Known Risky Environments

### ❌ OneDrive

**Risk Level:** HIGH

**Why:** OneDrive sync interferes with SQLite's file locking and can cause:
- Lock timeouts
- Database corruption
- Lost writes

**Detection:**
- Path contains `OneDrive` or `onedrive`

**Solution:**
```bash
python -m src.cli.main run --family zip --safe-workspace
```

### ❌ WSL DrvFS (/mnt/*)

**Risk Level:** HIGH

**Why:** Windows filesystem mounted in WSL lacks full POSIX file locking support

**Detection:**
- Running in WSL (`uname -a` shows WSL)
- Path starts with `/mnt/c`, `/mnt/d`, etc.

**Solution:**
```bash
# Move repo to native WSL filesystem
mv /mnt/c/Users/username/repo ~/projects/repo
cd ~/projects/repo

# Or use safe workspace
python -m src.cli.main run --family zip --safe-workspace
```

### ❌ Network Drives

**Risk Level:** HIGH

**Why:** Network filesystems often have:
- High latency
- Incomplete locking semantics
- Sync delays

**Detection:**
- Windows: Drive mapped via `net use`
- Linux: NFS/CIFS mount

**Solution:**
```bash
# Copy repo to local disk
# Or use safe workspace
python -m src.cli.main run --family zip --safe-workspace
```

### ⚠️ Encrypted Volumes (BitLocker, FileVault)

**Risk Level:** MEDIUM

**Why:** Encryption overhead can slow I/O, increasing lock contention

**Solution:**
- Increase busy_timeout: `--sqlite-busy-timeout-ms 300000`
- Use safe workspace on unencrypted partition if available

### ✅ Safe Environments

- **Windows**: Local NTFS drives (C:\, D:\) NOT in OneDrive
- **Linux**: ext4, xfs, btrfs filesystems
- **macOS**: APFS (local, not cloud-synced)

## Best Practices

### Development

```bash
# Always use safe workspace when on OneDrive/DrvFS
python -m src.cli.main run --family zip --safe-workspace --deterministic

# For debugging lock issues
python tools/diagnose_sqlite_lock.py --stress-test
```

### CI/CD

```bash
# Use safe workspace in CI environments
python -m src.cli.main run --family zip --safe-workspace --seed $CI_SEED

# Increase timeout for CI runners with slow I/O
python -m src.cli.main run --family zip --safe-workspace --sqlite-busy-timeout-ms 300000
```

### Production Validation (Phase 2)

```bash
# E2E with safe workspace and determinism
python tools/run_e2e_zip.py \
  --family zip \
  --seed 12345 \
  --runs 3 \
  --safe-workspace \
  --sqlite-busy-timeout-ms 120000
```

## Configuration Reference

### Database.__init__() Parameters

```python
Database(
    db_path=Path("data/example_reviewer.db"),
    busy_timeout_ms=120000,  # 2 minutes
    wal_enabled=True,        # Recommended
)
```

### CLI Global Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--safe-workspace` | False | Enable safe workspace mode |
| `--safe-root <path>` | Auto-detected | Override safe workspace root |
| `--sqlite-busy-timeout-ms <ms>` | 120000 | SQLite busy timeout (milliseconds) |
| `--sqlite-wal` | True | Enable WAL mode |
| `--no-sqlite-wal` | - | Disable WAL mode (not recommended) |

### Environment Variables

Currently none. All configuration is via CLI flags.

## Performance Characteristics

### WAL Mode Impact

- **Reads**: No blocking, concurrent with writes
- **Writes**: Serialized via RLock, typically <10ms per operation
- **Checkpoint**: Automatic, non-blocking
- **Disk Usage**: ~3x database size (DB + WAL + SHM)

### Safe Workspace Impact

- **Setup**: One-time directory creation (~10ms)
- **I/O**: FASTER than OneDrive/DrvFS (no sync overhead)
- **Cleanup**: Manual (workspace persists after run)

### Stress Test Baseline

On local SSD with WAL enabled:
- 8 threads × 50 writes = 400 operations
- Expected duration: 1-3 seconds
- Success rate: 100%

If your environment shows >10 seconds or failures, investigate filesystem performance.

## Migration Guide

### From OneDrive to Safe Workspace

```bash
# Old (risky, may fail)
cd ~/OneDrive/Documents/example-reviewer
python -m src.cli.main run --family zip

# New (safe, recommended)
cd ~/OneDrive/Documents/example-reviewer
python -m src.cli.main run --family zip --safe-workspace
```

Database and artifacts will be created in safe location automatically. Original repo can stay in OneDrive.

### From DrvFS to Native WSL

```bash
# Option 1: Move repo to native WSL filesystem
mv /mnt/c/Users/username/example-reviewer ~/projects/
cd ~/projects/example-reviewer

# Option 2: Keep repo on DrvFS, use safe workspace
cd /mnt/c/Users/username/example-reviewer
python -m src.cli.main run --family zip --safe-workspace
```

## References

- SQLite WAL mode: https://www.sqlite.org/wal.html
- SQLite busy timeout: https://www.sqlite.org/c3ref/busy_timeout.html
- OneDrive + SQLite issues: Known Windows limitation
- WSL file locking: https://github.com/microsoft/WSL/issues/

## Version History

- **v1.0** (2026-01-22): Initial implementation
  - Safe workspace mode
  - WAL mode enforcement
  - Single-writer protection
  - Diagnostic tool
  - Comprehensive tests
