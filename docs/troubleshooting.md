# Troubleshooting Guide

## Common Issues and Solutions

### Discovery Issues

#### No Snippets Found

**Symptom**: Discovery reports 0 snippets found

**Possible Causes**:
1. Wrong content root path
2. Incorrect family pattern
3. No C# code fences in files

**Solutions**:

```bash
# Check content root exists
ls -la ../../content

# Verify family pattern matches files
find ../../content -path "**/zip/**/*.md" | head -5

# Check for C# code fences manually
grep -r "```csharp" ../../content/blog.aspose.net/zip/ | head -5

# Enable debug logging
export LOG_LEVEL="DEBUG"
python src/cli.py discover --family zip -v
```

#### Permission Denied Errors

**Symptom**: `PermissionError: [Errno 13] Permission denied`

**Solution**:

```bash
# Check file permissions
ls -la ../../content

# Fix permissions
chmod -R u+r ../../content
```

#### Database Locked

**Symptom**: `database is locked`

**Solution**:

```bash
# Check for running processes
ps aux | grep example-reviewer

# Kill stale processes
killall python

# Enable WAL mode
sqlite3 data/snippets.db "PRAGMA journal_mode=WAL;"

# Increase timeout
export DATABASE_TIMEOUT="60"
```

---

### Validation Issues

#### CS5001: Program does not contain a static 'Main' method

**Symptom**: All snippets fail with CS5001 error

**Cause**: Library mode not enabled in workspace

**Solution**:

Check `workspace_manager.py` has:

```python
<OutputType>Library</OutputType>
```

Not:

```python
<OutputType>Exe</OutputType>
```

#### CS0246: The type or namespace name could not be found

**Symptom**: Type not found errors

**Possible Causes**:
1. Missing using statement
2. Wrong NuGet package version
3. Package not installed

**Solutions**:

```bash
# Check NuGet package in workspace
cat workspaces/snippet_123/Validator.csproj

# Verify package exists
dotnet list workspaces/snippet_123 package

# Clear NuGet cache
dotnet nuget locals all --clear

# Restore packages
cd workspaces/snippet_123
dotnet restore
```

#### Compilation Timeout

**Symptom**: Validation hangs or times out

**Solution**:

```bash
# Increase timeout
export COMPILATION_TIMEOUT="120"

# Check dotnet is working
dotnet --version

# Test manual compilation
cd workspaces/snippet_123
dotnet build -v detailed
```

#### Pattern Fixes Not Applied

**Symptom**: Known errors not being fixed automatically

**Solution**:

```python
# Check pattern registry
from src.pattern_registry import PatternRegistry

patterns = PatternRegistry.get_pattern_fixes("zip")
for p in patterns:
    print(f"{p.name}: {p.error_pattern}")

# Test pattern matching
import re
error = "CS0246: The type or namespace name 'Archive' could not be found"
for p in patterns:
    if re.search(p.error_pattern, error):
        print(f"Match: {p.name}")
```

---

### Ollama Integration Issues

#### Connection Refused

**Symptom**: `requests.exceptions.ConnectionError: ('Connection aborted.', ConnectionRefusedError(111, 'Connection refused'))`

**Cause**: Ollama not running

**Solution**:

```bash
# Check if Ollama is running
ps aux | grep ollama

# Start Ollama
ollama serve &

# Test connection
curl http://localhost:11434/api/tags

# Check correct URL
export OLLAMA_URL="http://localhost:11434"
```

#### Timeout Errors

**Symptom**: Ollama requests timeout

**Solution**:

```bash
# Increase timeout
export OLLAMA_TIMEOUT="120"

# Check Ollama load
curl http://localhost:11434/api/ps
```

#### Invalid Model

**Symptom**: `Error: model 'llama3.1' not found`

**Solution**:

```bash
# List available models
ollama list

# Pull model
ollama pull llama3.1

# Or use different model
export OLLAMA_MODEL="codellama"
```

#### Poor Fix Quality

**Symptom**: Ollama suggests incorrect fixes

**Solutions**:

1. **Use better model**:
```bash
export OLLAMA_MODEL="deepseek-coder"
```

2. **Adjust temperature**:
```bash
export OLLAMA_TEMPERATURE="0"  # More deterministic
```

3. **Review pattern fixes first**:
Pattern fixes are more reliable than AI fixes. Ensure patterns are tried first.

---

### Patching Issues

#### Could Not Locate Code Fence

**Symptom**: Patching fails with "Could not locate code fence in file"

**Possible Causes**:
1. File modified since discovery
2. All three strategies (hash, context, fuzzy) failed
3. Code fence deleted or language tag changed

**Solutions**:

```bash
# Check file still exists
ls -la content/blog.aspose.net/zip/example/index.md

# Re-discover snippets
python src/cli.py discover --family zip --force

# Try dry-run to see which strategies work
python src/cli.py patch --family zip --dry-run -v

# Manually inspect snippet locator
sqlite3 data/snippets.db "SELECT locator_json FROM snippets WHERE snippet_id = 29;"
```

#### Patch Verification Failed

**Symptom**: "Patch verification failed: Expected code not found in any code fence"

**Cause**: Verification regex doesn't match patched content

**Solution**:

```python
# Debug verification
from src.patching_service import PatchingService

service = PatchingService("../../content", db)

# Get snippet
with db.get_session() as session:
    snippet = session.query(Snippet).get(29)

# Check verification manually
import re
fence_pattern = r'```(?:csharp|cs|c#|dotnet|net)\s*\n(.*?)\n```'
matches = re.finditer(fence_pattern, modified_content, re.DOTALL | re.IGNORECASE)

for match in matches:
    print(match.group(1)[:100])
```

#### Multiple Identical Snippets

**Symptom**: Wrong snippet being patched

**Cause**: Fuzzy matching selected wrong code fence

**Solution**:

Ensure snippets have unique locators:

```python
# Check locator uniqueness
SELECT
    locator_json,
    COUNT(*) as count
FROM snippets
WHERE page_id = 123
GROUP BY locator_json
HAVING count > 1;
```

Use heading context to disambiguate:

```json
{
  "heading_context": ["Method 1"],  // Not just []
  "snippet_ordinal": 1
}
```

---

### Database Issues

#### Database Corruption

**Symptom**: `database disk image is malformed`

**Solution**:

```bash
# Try to recover
sqlite3 data/snippets.db ".recover" | sqlite3 data/snippets_recovered.db

# Verify recovered database
sqlite3 data/snippets_recovered.db "PRAGMA integrity_check;"

# If successful, replace
mv data/snippets.db data/snippets.db.corrupt
mv data/snippets_recovered.db data/snippets.db
```

#### Foreign Key Violations

**Symptom**: `FOREIGN KEY constraint failed`

**Solution**:

```bash
# Check foreign key constraints
sqlite3 data/snippets.db "PRAGMA foreign_key_check;"

# Disable constraints temporarily (risky!)
sqlite3 data/snippets.db "PRAGMA foreign_keys = OFF;"

# Delete orphaned records
sqlite3 data/snippets.db "
DELETE FROM snippets
WHERE page_id NOT IN (SELECT page_id FROM pages);
"
```

#### Slow Queries

**Symptom**: Database queries taking too long

**Solutions**:

```bash
# Analyze query
sqlite3 data/snippets.db "
EXPLAIN QUERY PLAN
SELECT * FROM snippets
JOIN pages ON snippets.page_id = pages.page_id
WHERE pages.family = 'zip';
"

# Add missing index
sqlite3 data/snippets.db "
CREATE INDEX IF NOT EXISTS idx_pages_family ON pages(family);
"

# Vacuum database
sqlite3 data/snippets.db "VACUUM;"

# Enable WAL mode
sqlite3 data/snippets.db "PRAGMA journal_mode=WAL;"
```

---

### Workspace Issues

#### Disk Space Full

**Symptom**: `OSError: [Errno 28] No space left on device`

**Solution**:

```bash
# Check disk space
df -h

# Clean workspaces
rm -rf workspaces/*

# Enable auto-cleanup
export WORKSPACE_CLEANUP_AUTO="true"

# Clean NuGet cache
dotnet nuget locals all --clear
```

#### Workspace Creation Fails

**Symptom**: Cannot create workspace directory

**Solution**:

```bash
# Check permissions
ls -la workspaces/

# Fix permissions
chmod 755 workspaces/

# Check parent directory exists
mkdir -p workspaces
```

#### Stale Build Artifacts

**Symptom**: Compilation uses cached results

**Solution**:

```bash
# Clean specific workspace
rm -rf workspaces/snippet_123/bin workspaces/snippet_123/obj

# Clean all workspaces
find workspaces -name "bin" -type d -exec rm -rf {} +
find workspaces -name "obj" -type d -exec rm -rf {} +

# Force rebuild
dotnet build --no-incremental
```

---

### Performance Issues

#### Slow Discovery

**Symptom**: Discovery takes too long

**Solutions**:

```bash
# Limit to specific subdirectory
find ../../content/blog.aspose.net/zip -name "*.md" | wc -l

# Use more specific pattern
# Instead of: **/zip/**/*.md
# Use: content/blog.aspose.net/zip/**/*.md

# Profile to find bottleneck
python -m cProfile -s cumulative src/cli.py discover --family zip
```

#### Slow Validation

**Symptom**: Validation very slow

**Solutions**:

```bash
# Check compilation time
grep "compilation_time" logs/example-reviewer.log | awk '{sum+=$2; count++} END {print sum/count}'

# Reduce NuGet restore time
# Pre-populate NuGet cache
dotnet restore test-examples/Validator.csproj

# Use faster disk for workspaces
export WORKSPACE_BASE_PATH="/tmp/workspaces"
```

#### Memory Usage

**Symptom**: High memory consumption

**Solutions**:

```python
# Process snippets in batches
from database import Database, Snippet

db = Database()
batch_size = 100

with db.get_session() as session:
    total = session.query(Snippet).count()

    for offset in range(0, total, batch_size):
        snippets = session.query(Snippet).limit(batch_size).offset(offset).all()
        # Process batch
        session.expunge_all()  # Clear session cache
```

---

### Logging Issues

#### No Logs Generated

**Symptom**: Log files empty or not created

**Solution**:

```bash
# Check log directory exists
mkdir -p logs/

# Check permissions
chmod 755 logs/

# Enable logging explicitly
export LOG_LEVEL="DEBUG"
export LOG_FILE_PATH="logs/debug.log"

# Check log configuration
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
logging.debug('Test message')
"
```

#### Too Many Logs

**Symptom**: Log files consuming too much disk

**Solution**:

```python
# Enable log rotation
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "logs/example-reviewer.log",
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5
)

# Or use daily rotation
from logging.handlers import TimedRotatingFileHandler

handler = TimedRotatingFileHandler(
    "logs/example-reviewer.log",
    when="midnight",
    backupCount=7
)
```

---

## Diagnostic Commands

### System Health Check

```bash
#!/bin/bash

echo "=== System Health Check ==="

# Python version
echo "Python: $(python --version)"

# .NET version
echo ".NET: $(dotnet --version)"

# Ollama status
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "Ollama: Running"
else
    echo "Ollama: Not running"
fi

# Database status
if [ -f "data/snippets.db" ]; then
    echo "Database: $(ls -lh data/snippets.db | awk '{print $5}')"
    echo "Snippets: $(sqlite3 data/snippets.db 'SELECT COUNT(*) FROM snippets;')"
else
    echo "Database: Not found"
fi

# Disk space
echo "Disk: $(df -h . | tail -1 | awk '{print $5 " used"}')"

# Workspaces
echo "Workspaces: $(find workspaces -type d -name "snippet_*" | wc -l)"
```

### Database Diagnostics

```bash
# Check database integrity
sqlite3 data/snippets.db "PRAGMA integrity_check;"

# Show table sizes
sqlite3 data/snippets.db "
SELECT
    name as table_name,
    (SELECT COUNT(*) FROM main[name]) as row_count
FROM sqlite_master
WHERE type='table'
ORDER BY row_count DESC;
"

# Show recent validation runs
sqlite3 data/snippets.db -header -column "
SELECT
    run_id,
    family,
    started_at,
    verified_count || '/' || total_snippets as verified,
    needs_fix_count as needs_fix
FROM validation_runs
ORDER BY started_at DESC
LIMIT 5;
"
```

### Workspace Diagnostics

```bash
# List all workspaces
find workspaces -type d -name "snippet_*" | sort

# Check workspace disk usage
du -sh workspaces/

# Find failed compilations
find workspaces -name "*.csproj" -exec sh -c '
    cd $(dirname {}) && dotnet build > /dev/null 2>&1 || echo "Failed: {}"
' \;
```

---

## Getting Help

### Enable Verbose Output

```bash
export LOG_LEVEL="DEBUG"
python src/cli.py <command> -v
```

### Collect Diagnostic Information

```bash
# Create diagnostic bundle
mkdir -p diagnostics/
cp data/snippets.db diagnostics/
cp logs/*.log diagnostics/
sqlite3 data/snippets.db .dump > diagnostics/schema.sql
tar -czf diagnostics-$(date +%Y%m%d).tar.gz diagnostics/
```

### Report Issue

When reporting issues, include:

1. **Error message** (full stack trace)
2. **Command executed**
3. **Environment** (OS, Python version, .NET version)
4. **Logs** (relevant excerpts)
5. **Database state** (snippet counts, validation run status)

### Example Issue Report

```markdown
## Issue Description
Patching fails with "Could not locate code fence in file"

## Steps to Reproduce
1. Run discovery: `python src/cli.py discover --family zip`
2. Run validation: `python src/cli.py validate --family zip`
3. Run patching: `python src/cli.py patch --family zip --dry-run`

## Expected Behavior
49/50 snippets should be patched successfully

## Actual Behavior
Only 38/50 snippets patched

## Environment
- OS: Ubuntu 22.04
- Python: 3.10.12
- .NET: 8.0.100
- Ollama: 0.1.17

## Logs
```
[ERROR] Snippet 29: Could not locate code fence in file
```

## Additional Context
File content/blog.aspose.net/zip/unzip-files-online/index.md was modified after discovery
```

---

## FAQ

### Q: Why are some snippets marked as "needs_fix" instead of being auto-fixed?

**A**: Pattern fixes only cover known error patterns. If an error doesn't match any pattern and Ollama is unavailable or fails, the snippet remains as "needs_fix".

**Solution**: Either add a new pattern fix or run the fix command with Ollama enabled.

### Q: Can I patch snippets even if they failed validation?

**A**: No. Only snippets with `status='verified'` are patched. Failed snippets must be fixed first.

### Q: How do I reset the database and start over?

**A**:

```bash
rm data/snippets.db
python src/cli.py discover --family zip
python src/cli.py validate --family zip
```

### Q: Can I run validation in parallel?

**A**: Currently no. Parallel validation is experimental and not yet stable.

### Q: How do I customize the code wrapper template?

**A**: Edit `workspace_wrapper.py` and modify the `wrap_for_library()` method.

### Q: What if I want to use a different .NET framework version?

**A**:

```bash
export DOTNET_FRAMEWORK="net7.0"
```

And update the .csproj template in `workspace_manager.py`.
