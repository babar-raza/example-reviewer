# REORG-03 Verification Commands

Quick reference for verifying the migration was successful.

---

## 1. Verify All Files Moved

```bash
# List all files in new locations
find src/validation -name "*.py" -type f | sort
```

**Expected Output** (11 files):
```
src/validation/__init__.py
src/validation/analysis/__init__.py
src/validation/analysis/code_pattern_detector.py
src/validation/analysis/namespace_validator.py
src/validation/analysis/pattern_registry.py
src/validation/fixing/__init__.py
src/validation/fixing/dependency_resolver.py
src/validation/fixing/persistent_fix_service.py
src/validation/orchestrator.py
src/validation/workspace/__init__.py
src/validation/workspace/workspace_manager.py
```

---

## 2. Verify Old Files Removed

```bash
# Check each old file
for file in validation_orchestrator code_pattern_detector pattern_registry namespace_validator persistent_fix_service dependency_resolver workspace_manager; do
  if [ -f "src/${file}.py" ]; then
    echo "ERROR: ${file}.py still at old location"
  else
    echo "✓ ${file}.py moved"
  fi
done
```

**Expected Output**:
```
✓ validation_orchestrator.py moved
✓ code_pattern_detector.py moved
✓ pattern_registry.py moved
✓ namespace_validator.py moved
✓ persistent_fix_service.py moved
✓ dependency_resolver.py moved
✓ workspace_manager.py moved
```

---

## 3. Verify Git Status

```bash
git status --short
```

**Expected Output** (should include):
```
R  src/pattern_registry.py -> src/validation/analysis/pattern_registry.py
RM src/validation_orchestrator.py -> src/validation/orchestrator.py
RM src/workspace_manager.py -> src/validation/workspace/workspace_manager.py
```

---

## 4. Verify Syntax (All Files)

```bash
# Test each file
python -m py_compile src/validation/orchestrator.py && echo "✓ orchestrator.py"
python -m py_compile src/validation/analysis/code_pattern_detector.py && echo "✓ code_pattern_detector.py"
python -m py_compile src/validation/analysis/pattern_registry.py && echo "✓ pattern_registry.py"
python -m py_compile src/validation/analysis/namespace_validator.py && echo "✓ namespace_validator.py"
python -m py_compile src/validation/fixing/persistent_fix_service.py && echo "✓ persistent_fix_service.py"
python -m py_compile src/validation/fixing/dependency_resolver.py && echo "✓ dependency_resolver.py"
python -m py_compile src/validation/workspace/workspace_manager.py && echo "✓ workspace_manager.py"
```

**Expected Output**:
```
✓ orchestrator.py
✓ code_pattern_detector.py
✓ pattern_registry.py
✓ namespace_validator.py
✓ persistent_fix_service.py
✓ dependency_resolver.py
✓ workspace_manager.py
```

---

## 5. View Import Changes (Git Diff)

```bash
# View orchestrator.py import changes
git diff src/validation/orchestrator.py | grep -E "^[-+]from|^[-+]import"

# View persistent_fix_service.py import changes (if tracked)
git diff src/validation/fixing/persistent_fix_service.py | grep -E "^[-+]from|^[-+]import"

# View workspace_manager.py import changes
git diff src/validation/workspace/workspace_manager.py | grep -E "^[-+]from|^[-+]import"
```

**Expected Output** (orchestrator.py):
```diff
-from database import Database, Snippet
-from telemetry import TelemetryClient
-from pattern_registry import PatternRegistry
-from workspace_manager import WorkspaceManager
-from ollama_integration import OllamaClient
+from src.core.database import Database, Snippet
+from src.core.telemetry import TelemetryClient
+from src.llm.ollama_integration import OllamaClient
+from src.api_reference.api_reference_service import ApiReferenceService
+from .analysis.pattern_registry import PatternRegistry
+from .analysis.namespace_validator import NamespaceValidator
+from .fixing.persistent_fix_service import PersistentFixService, FixResult
+from .fixing.dependency_resolver import DependencyResolver
+from .workspace.workspace_manager import WorkspaceManager
```

---

## 6. Check Package __init__.py Files

```bash
# Check main __init__.py
cat src/validation/__init__.py

# Check analysis __init__.py
cat src/validation/analysis/__init__.py

# Check fixing __init__.py
cat src/validation/fixing/__init__.py

# Check workspace __init__.py
cat src/validation/workspace/__init__.py
```

All should have proper exports defined.

---

## 7. Verify File Sizes (Integrity Check)

```bash
# Check orchestrator.py size
wc -l src/validation/orchestrator.py
# Expected: ~424 lines

# Check persistent_fix_service.py size
wc -l src/validation/fixing/persistent_fix_service.py
# Expected: ~626 lines

# Check workspace_manager.py size
wc -l src/validation/workspace/workspace_manager.py
# Expected: ~522 lines
```

---

## 8. Quick Import Test (Optional - Requires Dependencies)

```bash
# Test package-level imports (may fail if missing dependencies like 'requests')
python -c "from src.validation import ValidationOrchestrator"
python -c "from src.validation.analysis import PatternRegistry"
python -c "from src.validation.fixing import PersistentFixService"
python -c "from src.validation.workspace import WorkspaceManager"
```

**Note**: These may fail with `ModuleNotFoundError: No module named 'requests'` due to missing dependencies, but that indicates the import paths are correct (just missing external deps).

---

## 9. Count Statistics

```bash
# Total Python files in validation package
find src/validation -name "*.py" | wc -l
# Expected: 11 (7 modules + 4 __init__.py)

# Total lines of code
find src/validation -name "*.py" -type f -exec wc -l {} + | tail -1
# Expected: ~2000+ lines
```

---

## 10. Verify Git Rename Detection

```bash
# Show renames with similarity detection
git status --short | grep "^R"
```

**Expected Output** (should show 3 renames):
```
R  src/pattern_registry.py -> src/validation/analysis/pattern_registry.py
RM src/validation_orchestrator.py -> src/validation/orchestrator.py
RM src/workspace_manager.py -> src/validation/workspace/workspace_manager.py
```

The `R` prefix indicates git detected a rename (history preserved).
The `M` after `R` (e.g., `RM`) indicates the file was also modified (imports updated).

---

## Summary

If all commands return expected outputs, REORG-03 is successfully completed.

✅ All 9 files moved
✅ 1 file renamed (validation_orchestrator → orchestrator)
✅ All imports updated
✅ Git history preserved (3 tracked renames)
✅ Zero syntax errors
✅ Old files removed
