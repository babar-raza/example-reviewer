# Implementation Plan: CD-01 - Make Code Fence Detection Configurable

## Task Overview
**ID**: CD-01
**Priority**: P1 (HIGH)
**Risk**: MEDIUM (changes discovery logic)
**Estimated Time**: 12 hours

## Problem Statement
Current discovery service hardcodes fence pattern in `FENCE_PATTERN` regex and `VALIDATABLE_LANGUAGES` set. This prevents:
- Language aliases support (c#, C#, csharp, cs all mean C#)
- Multi-character language tags handling (c# has non-word character)
- Alternative fence formats
- Per-family customization of discovery patterns

## Current State Analysis

### Existing Implementation
1. **src/services/discovery_service.py**:
   - Lines 22-25: Hardcoded `FENCE_PATTERN = re.compile(r'^```(\w*)\s*\n(.*?)^```', ...)`
   - Line 38: Hardcoded `VALIDATABLE_LANGUAGES = {'cs', 'csharp', 'c#'}`
   - Lines 287, 356: Language validation against hardcoded set
   - No normalization of language tags

2. **src/core/config.py**:
   - Contains GlobalConfig and FamilyConfig Pydantic models
   - No DiscoveryPatternsConfig model exists
   - GlobalConfig (lines 130-145): Has placeholders for new config sections

3. **config/global.json**:
   - Contains global configuration
   - No discovery_patterns section

4. **config/families/zip.json**:
   - Family-specific configuration
   - No discovery_patterns section

### Dependencies
- Pydantic BaseModel for validation
- Regex with MULTILINE | DOTALL flags
- FamilyConfig and GlobalConfig already use Pydantic

## Implementation Steps

### Step 1: Add DiscoveryPatternsConfig Model
**File**: `src/core/config.py`
**Action**: Add new Pydantic model after line 105 (after BackfillConfig)

```python
class DiscoveryPatternsConfig(BaseModel):
    """Discovery pattern configuration for code extraction."""
    fence_patterns: List[str] = Field(
        default=["^```(\\w+|c#)\\s*\\n(.*?)^```"],
        description="Regex patterns for code fence detection"
    )
    validatable_languages: List[str] = Field(
        default=["cs", "csharp", "c#"],
        description="Languages that should be validated"
    )
    language_aliases: Dict[str, List[str]] = Field(
        default={
            "csharp": ["cs", "c#", "C#", "csharp", "CSharp"],
            "python": ["py", "python", "python3"]
        },
        description="Language normalization mapping"
    )
    normalize_to_canonical: bool = Field(
        default=True,
        description="Normalize language tags to canonical form"
    )
    regex_timeout_seconds: float = Field(
        default=5.0,
        ge=0.1,
        le=30.0,
        description="Regex execution timeout for safety"
    )
```

**Changes**:
- Import List, Dict from typing (already present)
- Add model after BackfillConfig, before FinalReviewConfig
- Add discovery_patterns field to GlobalConfig
- Update ConfigurationManager._parse_global_config to handle discovery_patterns

### Step 2: Update GlobalConfig and FamilyConfig
**File**: `src/core/config.py`

**GlobalConfig changes** (line 130):
```python
class GlobalConfig(BaseModel):
    # ... existing fields ...
    discovery_patterns: DiscoveryPatternsConfig = Field(default_factory=DiscoveryPatternsConfig)
    # ... rest of fields ...
```

**FamilyConfig changes** (line 197):
```python
class FamilyConfig(BaseModel):
    # ... existing fields ...
    discovery_patterns: Optional[DiscoveryPatternsConfig] = None
    # ... rest of fields ...
```

**ConfigurationManager._parse_global_config** (after line 310):
```python
if 'discovery_patterns' in data:
    parsed['discovery_patterns'] = DiscoveryPatternsConfig(**data['discovery_patterns'])
```

**ConfigurationManager._parse_family_config** (after line 398):
```python
if 'discovery_patterns' in data:
    parsed['discovery_patterns'] = DiscoveryPatternsConfig(**data['discovery_patterns'])
```

### Step 3: Update DiscoveryService to Use Configurable Patterns
**File**: `src/services/discovery_service.py`

**Changes**:
1. Remove hardcoded constants (lines 22-38)
2. Add imports for timeout handling and performance monitoring
3. Add config parameter to __init__
4. Add language normalization function
5. Add safe regex compilation with timeout
6. Update _extract_inline_examples to use config patterns
7. Update language validation to use config + normalization

**New __init__ signature** (line 47):
```python
def __init__(
    self,
    db: Database,
    content_roots: Optional[List[str]] = None,
    global_config: Optional[Any] = None,  # GlobalConfig
    family_config: Optional[Any] = None,  # FamilyConfig
):
    self.db = db
    self.content_roots = content_roots or []
    self.global_config = global_config
    self.family_config = family_config

    # Get effective discovery patterns (family overrides global)
    self.discovery_patterns = self._get_effective_discovery_patterns()

    # Compile fence patterns with safety checks
    self.compiled_fence_patterns = self._compile_fence_patterns()
```

**Helper methods**:
```python
def _get_effective_discovery_patterns(self) -> Any:
    """Get effective discovery patterns (family overrides global)."""
    if self.family_config and self.family_config.discovery_patterns:
        return self.family_config.discovery_patterns
    if self.global_config and self.global_config.discovery_patterns:
        return self.global_config.discovery_patterns
    # Fallback to defaults
    from ..core.config import DiscoveryPatternsConfig
    return DiscoveryPatternsConfig()

def _compile_fence_patterns(self) -> List[Any]:
    """Compile fence patterns with catastrophic backtracking prevention."""
    compiled = []
    for pattern in self.discovery_patterns.fence_patterns:
        try:
            compiled.append(re.compile(pattern, re.MULTILINE | re.DOTALL))
        except re.error as e:
            logger.error(f"Failed to compile fence pattern '{pattern}': {e}")
    return compiled

def normalize_language(self, language_tag: str) -> str:
    """Normalize language tag to canonical form."""
    if not self.discovery_patterns.normalize_to_canonical:
        return language_tag

    tag_lower = language_tag.lower()
    for canonical, aliases in self.discovery_patterns.language_aliases.items():
        if tag_lower in [a.lower() for a in aliases]:
            return canonical

    return language_tag

def _is_validatable_language(self, language_tag: str) -> bool:
    """Check if language is validatable (after normalization)."""
    normalized = self.normalize_language(language_tag)
    validatable_lower = [lang.lower() for lang in self.discovery_patterns.validatable_languages]
    return normalized.lower() in validatable_lower
```

**Update _extract_inline_examples** (line 254):
- Replace hardcoded language check (line 287) with `self._is_validatable_language(code_language)`
- Store normalized language: `normalized_lang = self.normalize_language(code_language)`
- Use normalized_lang in ExampleRecord

### Step 4: Update Orchestrator to Pass Config
**File**: `src/pipeline/orchestrator.py`

Check if orchestrator creates DiscoveryService and pass config objects.

### Step 5: Add Default Discovery Patterns to global.json
**File**: `config/global.json`

Add after line 68 (after final_review):
```json
"discovery_patterns": {
  "fence_patterns": [
    "^```(\\w+|c#)\\s*\\n(.*?)^```"
  ],
  "validatable_languages": ["cs", "csharp", "c#"],
  "language_aliases": {
    "csharp": ["cs", "c#", "C#", "csharp", "CSharp"],
    "python": ["py", "python", "python3"]
  },
  "normalize_to_canonical": true,
  "regex_timeout_seconds": 5.0
}
```

### Step 6: Add Discovery Patterns to zip.json (Optional Override)
**File**: `config/families/zip.json`

Add after line 82 (after api_reference):
```json
"discovery_patterns": {
  "fence_patterns": [
    "^```(\\w+|c#)\\s*\\n(.*?)^```"
  ],
  "validatable_languages": ["cs", "csharp", "c#", "C#"],
  "normalize_to_canonical": true
}
```

### Step 7: Create Comprehensive Test Suite
**File**: `tests/test_discovery_patterns.py` (NEW)

**Test Coverage**:
1. `test_discovery_patterns_config_model_defaults()` - Default values work
2. `test_discovery_patterns_config_validation()` - Field validation
3. `test_language_normalization_csharp()` - c#, C#, cs → csharp
4. `test_language_normalization_python()` - py, python, python3 → python
5. `test_language_normalization_disabled()` - No normalization when disabled
6. `test_validatable_languages_check()` - Validation against configured languages
7. `test_fence_pattern_compilation()` - Patterns compile successfully
8. `test_fence_pattern_invalid_regex()` - Invalid regex handled gracefully
9. `test_discovery_service_uses_config()` - Service uses config patterns
10. `test_language_alias_case_insensitive()` - Case-insensitive matching
11. `test_family_config_overrides_global()` - Family overrides global patterns
12. `test_regex_safety_large_file()` - Performance on large markdown files

**Performance Test**: Create 10,000-line markdown file, measure regex execution time.

### Step 8: Integration Testing
**Actions**:
1. Run existing discovery tests to ensure no regressions
2. Test with ZIP family to verify existing functionality works
3. Run end-to-end pipeline test
4. Verify performance benchmarks

### Step 9: Documentation and Evidence
**Actions**:
1. Capture all test outputs
2. Run pytest with verbose output
3. Time regex execution on large files
4. Document all changes in changes.md
5. Collect evidence in evidence.md

## Assumptions
1. ConfigurationManager correctly merges global and family configs
2. Existing code uses ConfigurationManager to load configs
3. DiscoveryService is instantiated by orchestrator
4. Database schema doesn't need changes (language field already exists)
5. Regex patterns should support both \w+ and specific characters like c#

## Rollback Plan
If implementation causes issues:
1. **Immediate rollback**: Revert changes to discovery_service.py, restore hardcoded patterns
2. **Partial rollback**: Keep config model, disable feature by default (normalize_to_canonical: false)
3. **Config rollback**: Remove discovery_patterns from JSON configs, use code defaults
4. **Git rollback**: `git checkout HEAD~1 -- src/services/discovery_service.py src/core/config.py`

## Risk Mitigation
1. **Regex safety**: Add timeout guards, test with large files
2. **Backward compatibility**: Default values match current hardcoded behavior
3. **Validation**: Pydantic ensures config structure is valid
4. **Testing**: Comprehensive unit tests + integration tests
5. **Performance**: Benchmark regex execution, ensure < 10ms per page

## Success Criteria
- [ ] DiscoveryPatternsConfig model added and validated
- [ ] GlobalConfig and FamilyConfig include discovery_patterns
- [ ] DiscoveryService uses configurable patterns
- [ ] Language normalization works (c#, C#, cs → csharp)
- [ ] Global and family configs have discovery_patterns sections
- [ ] Unit tests pass: pytest tests/test_discovery_patterns.py -v (12+ tests)
- [ ] No regressions: existing tests pass
- [ ] Performance: regex < 10ms per page on 10,000-line file
- [ ] All deliverables complete with evidence

## Timeline
1. Step 1-2: Config models (1 hour)
2. Step 3: Discovery service updates (2 hours)
3. Step 4: Orchestrator integration (0.5 hours)
4. Step 5-6: Config files (0.5 hours)
5. Step 7: Test suite (3 hours)
6. Step 8: Integration testing (1 hour)
7. Step 9: Documentation (1 hour)
8. Buffer: 3 hours

**Total**: 12 hours

## Next Actions
1. Read orchestrator.py to understand DiscoveryService instantiation
2. Implement config models in config.py
3. Update discovery_service.py with configurable patterns
4. Write comprehensive test suite
5. Run verification and collect evidence
6. Complete self-review
