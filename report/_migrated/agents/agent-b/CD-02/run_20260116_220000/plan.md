# Implementation Plan: CD-02 - Add Line Count and Content-Based Filtering

**Agent**: Agent B (Implementation)
**Task ID**: CD-02
**Priority**: P1 (HIGH)
**Risk**: MEDIUM (changes discovery logic)
**Estimated Time**: 10 hours
**Start Time**: 2026-01-16 22:00:00

## Objective

Add line count and content-based filtering to the discovery service to exclude non-code content (JSON/XML configs, command outputs, file listings) and snippets that are too short or too long.

## Current State Analysis

### Existing Files Review
1. **src/core/config.py** (445 lines)
   - Contains: GlobalConfig, FamilyConfig, ConfigurationManager
   - Does NOT contain DiscoveryPatternsConfig (CD-01 not implemented)
   - Safe to add new configuration classes

2. **src/services/discovery_service.py** (500 lines)
   - Contains: DiscoveryService, GistResolver
   - Current filtering: Only filters by language (VALIDATABLE_LANGUAGES)
   - No line count or content filtering implemented
   - Need to add filtering logic in _extract_inline_examples method

3. **config/global.json** (93 lines)
   - Contains LLM, git, gist, telemetry, vector_db, backfill, final_review configs
   - Does NOT contain discovery configuration
   - Need to add discovery section

4. **config/families/zip.json** (84 lines)
   - Contains family-specific config
   - Does NOT contain discovery_patterns configuration
   - Need to add discovery_patterns section

### Dependencies
- No CD-01 changes detected (DiscoveryPatternsConfig doesn't exist)
- Will implement both configuration model and filtering logic from scratch

## Implementation Plan

### Phase 1: Configuration Model (30 min)
**File**: src/core/config.py

1. Add DiscoveryPatternsConfig class after line 104 (after BackfillConfig):
   ```python
   class DiscoveryPatternsConfig(BaseModel):
       """Discovery filtering configuration."""
       min_line_count: int = Field(default=5, ...)
       max_line_count: int = Field(default=500, ...)
       content_exclude_patterns: List[str] = Field(default=[...], ...)
       require_code_indicators: List[str] = Field(default=[...], ...)
   ```

2. Add discovery_patterns field to GlobalConfig (after line 139):
   ```python
   discovery_patterns: DiscoveryPatternsConfig = Field(default_factory=DiscoveryPatternsConfig)
   ```

3. Update _parse_global_config method to parse discovery_patterns (after line 310)

4. Verify Pydantic validation works with default values

### Phase 2: Filtering Logic (1 hour)
**File**: src/services/discovery_service.py

1. Import DiscoveryPatternsConfig at top of file

2. Add filter_snippet method to DiscoveryService class (after __init__):
   ```python
   def filter_snippet(self, code: str, config: DiscoveryPatternsConfig) -> Tuple[bool, str]:
       """Filter snippet based on content rules."""
       # Line count check
       # Content exclusion patterns
       # Code indicator check
       # Return (should_include, reason)
   ```

3. Update __init__ to accept optional filtering_config parameter

4. Modify _extract_inline_examples to apply filtering (around line 287):
   - Call filter_snippet before creating ExampleRecord
   - Track filtered snippets in stats
   - Log filter reasons at DEBUG level

5. Add telemetry tracking for filtered snippets

### Phase 3: Configuration Files (30 min)
**File**: config/global.json

1. Add discovery_patterns section:
   ```json
   "discovery_patterns": {
     "min_line_count": 5,
     "max_line_count": 500,
     "content_exclude_patterns": [
       "^\\s*{\\s*$",
       "^\\s*<\\?xml",
       "^\\s*Output:",
       "^\\s*\\$"
     ],
     "require_code_indicators": [
       "\\bclass\\b",
       "\\bpublic\\b",
       "\\bvoid\\b",
       "\\busing\\b",
       "\\bnamespace\\b"
     ]
   }
   ```

**File**: config/families/zip.json

1. Add discovery_patterns override (optional, can use global defaults)

### Phase 4: Testing (2 hours)
**File**: tests/test_discovery_filters.py (NEW)

Create comprehensive test suite:
1. test_line_count_filtering_too_short
2. test_line_count_filtering_too_long
3. test_line_count_filtering_valid
4. test_content_exclusion_json
5. test_content_exclusion_xml
6. test_content_exclusion_output
7. test_code_indicators_present
8. test_code_indicators_missing
9. test_filter_integration_with_discovery

### Phase 5: Integration Testing (1 hour)
1. Run discovery on ZIP family
2. Verify filtering metrics in telemetry
3. Check that real code snippets are NOT filtered
4. Verify non-code content IS filtered

### Phase 6: Documentation (30 min)
1. Update changes.md with all modifications
2. Document test results in evidence.md
3. Complete self_review.md with 12-dimension assessment
4. Update commands.sh with all verification commands

## Risk Mitigation

### Risk 1: False Positives (filtering valid code)
- **Mitigation**: Use lenient code indicators (only require ONE keyword)
- **Testing**: Test with real ZIP family examples
- **Rollback**: Configuration can be adjusted without code changes

### Risk 2: Regex Pattern Errors
- **Mitigation**: Test all regex patterns individually
- **Testing**: Unit tests for each pattern
- **Validation**: Use re.compile() to validate patterns at config load

### Risk 3: Breaking Existing Discovery
- **Mitigation**: Make filtering optional via configuration
- **Testing**: Compare discovery results before/after
- **Fallback**: Set min_line_count=1 to disable line filtering

### Risk 4: Performance Impact
- **Mitigation**: Filter checks are O(n) where n = code length
- **Testing**: Benchmark discovery time before/after
- **Optimization**: Compile regex patterns once, reuse

## Success Criteria

- [ ] DiscoveryPatternsConfig added to config.py with validation
- [ ] filter_snippet method implemented with all checks
- [ ] Filtering integrated into _extract_inline_examples
- [ ] Configuration files updated (global.json)
- [ ] Unit tests created and passing (8+ tests)
- [ ] Telemetry metrics tracked: discovery.snippets_filtered_out
- [ ] Filter reasons logged and counted
- [ ] End-to-end test: ZIP discovery excludes non-code
- [ ] No false negatives: Real code still included
- [ ] All self-review dimensions ≥4/5

## Timeline

| Phase | Task | Duration | Status |
|-------|------|----------|--------|
| 1 | Configuration Model | 30 min | Pending |
| 2 | Filtering Logic | 1 hour | Pending |
| 3 | Configuration Files | 30 min | Pending |
| 4 | Unit Tests | 2 hours | Pending |
| 5 | Integration Tests | 1 hour | Pending |
| 6 | Documentation | 30 min | Pending |
| **Total** | | **5.5 hours** | |

## File Safety Protocol

For each file modification:
1. Read file completely first
2. Verify no conflicts with other changes
3. Make surgical edits using Edit tool
4. Preserve all existing functionality
5. Add, don't replace (unless explicitly replacing)

## Next Steps

1. Implement Phase 1: Configuration Model
2. Implement Phase 2: Filtering Logic
3. Implement Phase 3: Configuration Files
4. Implement Phase 4: Unit Tests
5. Run Phase 5: Integration Testing
6. Complete Phase 6: Documentation
