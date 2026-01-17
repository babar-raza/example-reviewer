# CD-03 Implementation Plan: Make Gist Pattern Detection Configurable

**Agent**: B (Implementation)
**Priority**: P2 (MEDIUM)
**Risk**: LOW (discovery enhancement)
**Estimated Time**: 8 hours
**Start Time**: 2026-01-17

---

## Overview

Make gist pattern detection configurable to support multiple gist platforms (GitHub, GitLab, Bitbucket), custom shortcode formats, owner filtering, and the ability to disable gist extraction.

## Current State Analysis

### Existing Code Review

**src/core/config.py**:
- ✅ Already has `DiscoveryPatternsConfig` (added by CD-01/CD-02)
- ✅ Contains line count and content filtering (CD-02)
- ✅ Integrated into `GlobalConfig` and `FamilyConfig`
- ✅ Pydantic BaseModel structure established

**src/services/discovery_service.py**:
- ✅ Has hardcoded patterns: `GIST_SHORTCODE_PATTERN`, `GIST_SCRIPT_PATTERN` (lines 27-35)
- ✅ Uses patterns in `_extract_gist_examples()` (line 472+)
- ✅ Already has `_get_effective_discovery_patterns()` for config override logic
- ⚠️ No owner filtering implemented
- ⚠️ No stats tracking for filtered gists

**config/global.json**:
- ✅ Has `discovery_patterns` section (lines 68-107)
- ❌ Missing `gist_extraction` subsection

**config/families/zip.json**:
- ✅ Has `discovery_patterns` override (lines 84-91)
- ❌ Missing `gist_extraction` configuration

**tests/**:
- ✅ Good test infrastructure exists: `test_discovery_patterns.py`, `test_discovery_filters.py`
- ✅ Pattern: pytest with tmp_path fixtures, MagicMock for db
- ❌ No gist pattern tests yet

---

## Implementation Strategy

### Phase 1: Add GistPatternsConfig Model (30 min)

**File**: `src/core/config.py`

1. Add `GistPatternsConfig` class after `DiscoveryPatternsConfig` (after line 165)
2. Include fields: `enabled`, `shortcode_patterns`, `script_patterns`, `allowed_owners`, `blocked_owners`
3. Implement helper methods: `compile_shortcode_patterns()`, `compile_script_patterns()`, `should_include_owner()`
4. Add to `DiscoveryPatternsConfig`: `gist_extraction: GistPatternsConfig = Field(default_factory=GistPatternsConfig)`

**Dependencies**: None (pure model addition)

### Phase 2: Update Discovery Service (1 hour)

**File**: `src/services/discovery_service.py`

1. Remove hardcoded patterns (lines 27-35: `GIST_SHORTCODE_PATTERN`, `GIST_SCRIPT_PATTERN`)
2. Add gist pattern compilation in `__init__()` similar to fence patterns
3. Update `_extract_gist_examples()`:
   - Use compiled patterns from config
   - Apply owner filtering with `should_include_owner()`
   - Add stats tracking for `filtered_gists`
4. Update `discover_family()` stats dict to include `filtered_gists`

**Dependencies**: Phase 1 complete

### Phase 3: Update Configuration Files (15 min)

**Files**: `config/global.json`, `config/families/zip.json`

1. **global.json**: Add `gist_extraction` section with default patterns
2. **zip.json**: Add example override with `allowed_owners`

**Dependencies**: Phase 1 complete

### Phase 4: Create Comprehensive Tests (2 hours)

**File**: `tests/test_gist_patterns.py` (NEW)

Test structure following existing patterns:
1. `TestGistPatternsConfig` - Model validation
2. `TestPatternCompilation` - Regex compilation
3. `TestOwnerFiltering` - Allowed/blocked owners
4. `TestGistExtraction` - Pattern matching
5. `TestDisabling` - Enabled flag
6. `TestMultiPlatform` - GitHub, GitLab patterns
7. `TestIntegration` - End-to-end tests
8. `TestStatistics` - Filtered gist tracking

**Dependencies**: Phases 1-3 complete

### Phase 5: Verification & Documentation (30 min)

1. Run full test suite: `pytest tests/test_gist_patterns.py -v`
2. Run existing tests to check for regressions
3. Write evidence.md with test outputs
4. Write self_review.md with 12-dimension assessment

---

## File Changes Summary

### Files to MODIFY (Read → Edit):
1. ✅ `src/core/config.py` - Add GistPatternsConfig, integrate into DiscoveryPatternsConfig
2. ✅ `src/services/discovery_service.py` - Remove hardcoded patterns, use configurable ones
3. ✅ `config/global.json` - Add gist_extraction defaults
4. ✅ `config/families/zip.json` - Add gist_extraction example override

### Files to CREATE:
1. ✅ `tests/test_gist_patterns.py` - Comprehensive test suite (~150 lines)

---

## Risk Assessment

### Technical Risks
- **LOW**: Regex pattern compilation errors → Mitigated by error handling in compile methods
- **LOW**: Breaking existing gist discovery → Mitigated by maintaining backward-compatible defaults
- **LOW**: Config parsing errors → Mitigated by Pydantic validation

### Integration Risks
- **VERY LOW**: CD-01/CD-02 already modified the same files → Will read and merge carefully
- **VERY LOW**: Test conflicts → Will follow existing test patterns

---

## Acceptance Criteria Checklist

- [ ] GistPatternsConfig Pydantic model added to config.py
- [ ] Model includes compile methods and should_include_owner()
- [ ] Discovery service uses configurable patterns
- [ ] Gist extraction can be disabled (enabled flag)
- [ ] Owner filtering works (allowed_owners, blocked_owners)
- [ ] Multiple gist patterns supported (GitHub, GitLab, custom)
- [ ] Global config has sensible defaults
- [ ] Family configs can override gist patterns
- [ ] Unit tests pass: pytest tests/test_gist_patterns.py -v (8+ tests)
- [ ] No regressions in existing gist discovery
- [ ] Stats tracking includes filtered_gists count

---

## Testing Strategy

### Unit Tests
- Config model validation (defaults, custom values, constraints)
- Pattern compilation (valid, invalid, multiple)
- Owner filtering (allowed, blocked, empty lists)
- Gist extraction with different patterns
- Disable flag functionality

### Integration Tests
- End-to-end gist discovery with filtering
- Family config overrides global config
- Stats tracking for filtered gists
- Multiple platform patterns (GitHub, GitLab)

### Regression Tests
- Existing tests must pass: `test_discovery_patterns.py`, `test_discovery_filters.py`
- No changes to inline code extraction
- Existing gist discovery behavior preserved with defaults

---

## Timeline

| Phase | Task | Duration | Dependencies |
|-------|------|----------|--------------|
| 1 | Add GistPatternsConfig model | 30 min | None |
| 2 | Update Discovery Service | 1 hour | Phase 1 |
| 3 | Update Config Files | 15 min | Phase 1 |
| 4 | Create Test Suite | 2 hours | Phases 1-3 |
| 5 | Verification & Docs | 30 min | All |
| **Total** | | **~4 hours** | |

Note: Original estimate was 8 hours, but implementation is simpler due to existing CD-01/CD-02 infrastructure.

---

## Success Metrics

- ✅ All new tests pass (8+ tests)
- ✅ All existing tests pass (no regressions)
- ✅ Self-review scores ≥4/5 on all 12 dimensions
- ✅ Gist extraction configurable per family
- ✅ Owner filtering functional
- ✅ Stats tracking includes filtered_gists

---

## Implementation Notes

### Pattern Safety
- Use `try/except` in compile methods for invalid regex
- Log warnings for invalid patterns
- Fallback to defaults if all patterns fail

### Backward Compatibility
- Default patterns match current hardcoded patterns
- Empty `allowed_owners` list = all owners allowed
- Default `enabled=True` maintains current behavior

### Future Extensibility
- Structure supports adding GitLab, Bitbucket patterns
- Owner filtering extensible to org-level rules
- Pattern list allows multiple formats per platform
