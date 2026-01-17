# Implementation Plan: CD-04 - Make Context Extraction Configurable

**Task ID**: CD-04
**Priority**: P2 (MEDIUM)
**Risk**: LOW
**Estimated Time**: 10 hours

## Problem Statement

Current context extraction in discovery_service.py hardcodes settings:
- `max_paragraphs = 2` (not configurable)
- No max_heading_distance control
- No option to include file-level header context
- No control over context window size
- Can't disable context extraction for performance

## Current State Analysis

After reading existing files:

### config.py
- Already has `DiscoveryPatternsConfig` model (lines 107-165)
- CD-02 already added filtering fields: `min_line_count`, `max_line_count`, `content_exclude_patterns`, `require_code_indicators`
- No context extraction configuration present yet
- Uses Pydantic BaseModel with Field validation

### discovery_service.py
- Has `_extract_description_context()` method (lines 206-243)
- Currently hardcodes `max_paragraphs=2` parameter (line 206)
- `_find_section_heading()` method exists (lines 188-204)
- Context extraction is called in `_extract_inline_examples()` (lines 442-443)
- Also called in `_extract_gist_examples()` (lines 499-500)

### global.json
- Has `discovery_patterns` section (lines 68-108)
- Currently includes CD-02 filtering fields
- No context extraction configuration

### zip.json
- Has `discovery_patterns` override section (lines 84-91)
- Limited to fence patterns and language settings only

## Implementation Steps

### Step 1: Add ContextExtractionConfig to config.py
- Create Pydantic model with 6 configurable parameters
- Add as field to `DiscoveryPatternsConfig`
- Ensure backward compatibility with defaults

### Step 2: Update global.json
- Add `context_extraction` section under `discovery_patterns`
- Set sensible defaults matching current behavior

### Step 3: Update zip.json (example override)
- Add context extraction override example
- Show how families can customize settings

### Step 4: Update discovery_service.py
- Refactor `_extract_description_context()` to use config
- Replace hardcoded `max_paragraphs=2` with `config.max_paragraphs`
- Add `max_heading_distance` logic to `_find_section_heading()`
- Add `context_window_lines` control
- Add `min_context_length` filtering
- Add `include_file_header` support
- Support `enabled` flag to skip context extraction entirely
- Rename to `_extract_context()` for simplicity

### Step 5: Create Comprehensive Tests
- Create `tests/test_context_extraction.py`
- 8+ test cases covering all configuration options
- Include performance test (<5ms per snippet)
- Verify no regressions in existing behavior

### Step 6: Verification
- Run pytest on new test file
- Verify configuration loading
- Check backward compatibility
- Test performance

### Step 7: Write Documentation
- changes.md - Detailed file changes with diffs
- evidence.md - Test outputs and verification
- self_review.md - 12-dimension quality assessment

## File Changes Summary

| File | Type | Changes |
|------|------|---------|
| `src/core/config.py` | UPDATE | Add ContextExtractionConfig model (~30 lines) |
| `config/global.json` | UPDATE | Add context_extraction config section |
| `config/families/zip.json` | UPDATE | Add override example |
| `src/services/discovery_service.py` | UPDATE | Use configurable context extraction (~100 lines modified) |
| `tests/test_context_extraction.py` | NEW | Complete test suite (~150 lines) |

## Risk Assessment

**LOW RISK** because:
1. Changes are additive with backward-compatible defaults
2. Context extraction is isolated functionality
3. Existing tests will catch regressions
4. Configuration is optional (defaults preserve current behavior)

## Acceptance Criteria Checklist

- [ ] ContextExtractionConfig Pydantic model added
- [ ] Discovery service uses configurable extraction
- [ ] max_paragraphs configurable
- [ ] max_heading_distance implemented
- [ ] include_file_header option works
- [ ] context_window_lines controls window
- [ ] min_context_length filters short context
- [ ] Context extraction can be disabled
- [ ] Global config has defaults
- [ ] Family configs can override
- [ ] Unit tests pass (8+ tests)
- [ ] No regressions
- [ ] Performance <5ms per snippet

## Timeline

1. Config model (30 min)
2. JSON updates (15 min)
3. Discovery service refactor (2 hours)
4. Test creation (2 hours)
5. Verification (1 hour)
6. Documentation (1 hour)

**Total**: ~6-7 hours (within 10-hour estimate)

## Dependencies

- Must merge with any CD-01, CD-02, CD-03 changes
- No breaking changes to existing APIs
- Preserve backward compatibility
