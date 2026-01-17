# Configurable Code Discovery Healing Plan

## Context
Phase A (Discovery & Extraction) currently has hardcoded extraction patterns and validation rules in `src/services/discovery_service.py`. Users cannot customize:
- Code fence patterns (hardcoded regex at lines 22-25)
- Validatable languages (hardcoded to C# only at line 38)
- Gist patterns (hardcoded regex at lines 27-35)
- Line count filters (no filtering capability)
- Language-specific extraction rules

This creates inflexibility when:
1. Working with multi-language codebases (Python, Java, JavaScript)
2. Filtering out trivial examples (1-2 line snippets)
3. Excluding specific gist patterns or sources
4. Customizing extraction behavior per family

**Business Impact:** Cannot reuse pipeline for non-C# families without code changes. Cannot filter low-quality snippets automatically.

## Gap → Taskcard Mapping

| Gap/Blocker ID | Description | Taskcard ID(s) |
|----------------|-------------|----------------|
| CD-GAP-01 | Hardcoded code fence regex - cannot customize fence styles | CD-01 |
| CD-GAP-02 | Hardcoded language list (C# only) - cannot validate other languages | CD-01 |
| CD-GAP-03 | No line count filtering - trivial snippets always included | CD-02 |
| CD-GAP-04 | Hardcoded gist patterns - cannot customize gist extraction | CD-03 |
| CD-GAP-05 | No exclude patterns - cannot skip specific code blocks | CD-02 |
| CD-GAP-06 | Context extraction not configurable (max_paragraphs=2 hardcoded) | CD-04 |

---

## Repo Reality Check

**Purpose**: Verify discovery service structure and confirm hardcoded patterns before making changes.

### Validation Commands

```bash
# 1. Verify discovery service file exists
[ -f src/services/discovery_service.py ] && echo "EXISTS: DiscoveryService" || echo "MISSING"

# 2. Check for hardcoded patterns (plan references these)
grep -n "FENCE_PATTERN\|VALIDATABLE_LANGUAGES\|GIST.*PATTERN" src/services/discovery_service.py

# 3. Verify exact line numbers match plan
grep -n "^FENCE_PATTERN" src/services/discovery_service.py  # Plan says line 22-25
grep -n "^VALIDATABLE_LANGUAGES" src/services/discovery_service.py  # Plan says line 38
grep -n "GIST.*PATTERN" src/services/discovery_service.py  # Plan says line 27-35

# 4. Check current config structure
grep -A 5 '"discovery' config/families/zip.json 2>/dev/null || echo "No discovery config yet"
grep -A 5 '"discovery' config/global.json 2>/dev/null || echo "No discovery config yet"

# 5. Verify config system uses Pydantic (not dataclasses)
grep -n "from pydantic import" src/core/config.py
grep -n "class.*Config.*BaseModel" src/core/config.py
```

### Reality Check Results

| Assumption | Status | Evidence |
|------------|--------|----------|
| discovery_service.py exists | ✅ **CORRECT** | File exists with hardcoded patterns |
| FENCE_PATTERN at lines 22-25 | ✅ **CORRECT** | Regex `^```(\w*)\s*\n(.*?)^```` found |
| VALIDATABLE_LANGUAGES at line 38 | ✅ **CORRECT** | Set `{'cs', 'csharp', 'c#'}` hardcoded |
| GIST patterns at lines 27-35 | ✅ **CORRECT** | Multiple gist regex patterns present |
| No discovery config exists | ✅ **CORRECT** | No `discovery_patterns` in configs yet |
| Config system uses Pydantic | ✅ **CORRECT** | All configs inherit from `BaseModel` |

### ChatGPT Review Suggestions

**From reviews/chatgpt.md**:
1. ✅ **Use Pydantic models, not dataclasses** - Config system is Pydantic-based (`BaseModel`)
2. ⚠️ **Regex safety** - Add guardrail for catastrophic backtracking (especially `.*?` with `DOTALL`)
3. ⚠️ **Language normalization** - Current `(\w*)` won't capture `c#` - need `(\w+|c#)` pattern
4. ✅ **Filtering telemetry** - Good idea to make metric names explicit

### Go/No-Go Decision

✅ **GO** - Plan is structurally sound and matches repository reality.

**Enhancements to Incorporate**:
- Use Pydantic `BaseModel` instead of `@dataclass` for DiscoveryPatternsConfig
- Add regex performance acceptance check (complete under X seconds on large files)
- Update fence pattern to handle `c#`: `(\w+|c#)` instead of `(\w*)`
- Make telemetry filter metric names explicit: `filtered_min_lines`, `filtered_exclude_regex`, `filtered_comments_only`

**Estimated Reality Check Time**: 10 minutes

---

## Taskcard CD-01: Make Code Fence and Language Detection Configurable

**Status:** Not Started

**Gap Linkage:** Fixes CD-GAP-01 (Hardcoded code fence regex), CD-GAP-02 (Hardcoded language list)

**Role:** Senior engineer delivering production-ready configurable code extraction patterns for multi-language support.

### Scope

**Fix:**
- Move `FENCE_PATTERN` regex from hardcoded constant to family config
- Move `VALIDATABLE_LANGUAGES` set from hardcoded constant to family config
- Support multiple fence patterns per family (e.g., `~~~` vs ` ``` `)
- Allow language aliases (e.g., `csharp` = `cs` = `c#`)
- Add default patterns in global config for reuse across families
- Maintain backward compatibility (use defaults if not configured)

**Allowed paths:**
- `src/services/discovery_service.py` - read patterns from config
- `src/core/config.py` - add discovery_patterns to FamilyConfig/GlobalConfig
- `config/families/zip.json` - example configuration
- `config/global.json` - default discovery patterns
- `tests/test_pattern_loading.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Add discovery patterns to `config/families/zip.json`:
  ```json
  {
    "discovery_patterns": {
      "fence_patterns": ["^```(\\w*)\\s*\\n(.*?)^```"],
      "fence_flags": ["MULTILINE", "DOTALL"],
      "validatable_languages": ["cs", "csharp", "c#"],
      "language_aliases": {
        "csharp": ["cs", "c#"],
        "python": ["py", "python3"],
        "javascript": ["js", "jsx", "node"]
      }
    }
  }
  ```
- Run `python -m cli scan --family zip`
- Verify examples extracted using configured patterns
- Change `validatable_languages` to `["python", "py"]` and re-scan Python content
- Verify Python examples extracted

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest tests/test_pattern_loading.py -v` passes
- Test default patterns used when family config missing
- Test custom fence patterns override defaults
- Test language aliases work (e.g., `cs` matches `csharp`)
- Test multiple fence patterns supported
- Test invalid regex pattern logs warning and uses default

**Config respected end-to-end:**
- Family config overrides global config
- Global config provides defaults
- Hardcoded fallback if both missing (backward compatible)

**No mock data in production paths:**
- Real regex patterns compiled from config
- Mock config files in tests

### Deliverables

1. **Updated `src/core/config.py`:**
   - Add `DiscoveryPatternsConfig` dataclass:
     ```python
     @dataclass
     class DiscoveryPatternsConfig:
         """Configuration for code discovery patterns."""
         fence_patterns: List[str] = field(default_factory=lambda: [
             r'^```(\w*)\s*\n(.*?)^```'  # Default markdown fence
         ])
         fence_flags: List[str] = field(default_factory=lambda: ['MULTILINE', 'DOTALL'])
         validatable_languages: List[str] = field(default_factory=lambda: ['cs', 'csharp', 'c#'])
         language_aliases: Dict[str, List[str]] = field(default_factory=dict)

         def compile_patterns(self) -> List[re.Pattern]:
             """Compile fence patterns with flags."""
             import re
             flags_map = {
                 'MULTILINE': re.MULTILINE,
                 'DOTALL': re.DOTALL,
                 'IGNORECASE': re.IGNORECASE,
             }
             combined_flags = 0
             for flag_name in self.fence_flags:
                 combined_flags |= flags_map.get(flag_name, 0)

             patterns = []
             for pattern_str in self.fence_patterns:
                 try:
                     patterns.append(re.compile(pattern_str, combined_flags))
                 except re.error as e:
                     logger.warning(f"Invalid regex pattern {pattern_str}: {e}")
             return patterns

         def normalize_language(self, lang: str) -> str:
             """Normalize language using aliases."""
             lang_lower = lang.lower().strip()

             # Check if already in validatable list
             if lang_lower in [vl.lower() for vl in self.validatable_languages]:
                 return lang_lower

             # Check aliases
             for primary, aliases in self.language_aliases.items():
                 if lang_lower in [a.lower() for a in aliases]:
                     return primary.lower()

             return lang_lower

         def is_validatable(self, lang: str) -> bool:
             """Check if language is validatable."""
             normalized = self.normalize_language(lang)
             return normalized in [vl.lower() for vl in self.validatable_languages]
     ```
   - Add `discovery_patterns: DiscoveryPatternsConfig` field to `FamilyConfig`
   - Add `default_discovery_patterns: DiscoveryPatternsConfig` field to `GlobalConfig`

2. **Updated `config/global.json`:**
   ```json
   {
     "default_discovery_patterns": {
       "fence_patterns": [
         "^```(\\w*)\\s*\\n(.*?)^```",
         "^~~~(\\w*)\\s*\\n(.*?)^~~~"
       ],
       "fence_flags": ["MULTILINE", "DOTALL"],
       "validatable_languages": ["cs", "csharp", "c#"],
       "language_aliases": {
         "csharp": ["cs", "c#", "C#"],
         "python": ["py", "python3"],
         "javascript": ["js", "jsx", "typescript", "ts"],
         "java": ["java"],
         "go": ["golang", "go"],
         "rust": ["rs", "rust"]
       }
     },
     ...
   }
   ```

3. **Updated `config/families/zip.json`:**
   ```json
   {
     "family": "zip",
     "discovery_patterns": {
       "validatable_languages": ["cs", "csharp", "c#"],
       "fence_patterns": ["^```(\\w*)\\s*\\n(.*?)^```"]
     },
     ...
   }
   ```

4. **Updated `src/services/discovery_service.py`:**
   - Remove hardcoded constants `FENCE_PATTERN` and `VALIDATABLE_LANGUAGES`
   - Accept `discovery_config: DiscoveryPatternsConfig` in `__init__()`
   - Update `_extract_inline_examples()`:
     ```python
     def _extract_inline_examples(
         self,
         content: str,
         file_path: str,
         family: str
     ) -> List[ExampleRecord]:
         """Extract inline fenced code blocks with configurable patterns."""
         examples = []

         # Use configured patterns
         compiled_patterns = self.discovery_config.compile_patterns()

         for pattern in compiled_patterns:
             for match in pattern.finditer(content):
                 language = match.group(1).strip().lower()
                 code_content = match.group(2)

                 # Use configured language validation
                 if self.discovery_config.is_validatable(language) and code_content.strip():
                     # Extract context and create example...
                     normalized_lang = self.discovery_config.normalize_language(language)
                     # ... rest of extraction logic
     ```
   - Update `discover_family()` to load discovery config:
     ```python
     def discover_family(
         self,
         family: str,
         family_config: FamilyConfig,
         max_files: Optional[int] = None,
     ) -> Dict[str, Any]:
         # Load discovery patterns from family config or global defaults
         if family_config.discovery_patterns:
             self.discovery_config = family_config.discovery_patterns
         else:
             # Load from global config
             global_config = load_global_config()
             self.discovery_config = global_config.default_discovery_patterns
     ```

5. **New test file `tests/test_pattern_loading.py`:**
   - `test_default_patterns_used_when_no_config`
   - `test_family_config_overrides_global`
   - `test_custom_fence_pattern_works`
   - `test_language_aliases_resolve_correctly`
   - `test_multiple_fence_patterns_supported`
   - `test_invalid_regex_pattern_logs_warning_uses_default`
   - `test_language_normalization`
   - `test_is_validatable_works_with_aliases`

6. **Forward-compatible migration:**
   - Existing families without `discovery_patterns` use global defaults
   - Global config defaults match previous hardcoded values (C# only)
   - Existing discovery behavior unchanged unless config added

### Hard Rules

- ✅ Keep public signatures: `DiscoveryService.__init__()` accepts optional config parameter with default
- ✅ No network in offline tests: Pattern compilation is local
- ✅ Deterministic runs: Regex compilation deterministic for same input
- ✅ No new deps: Use built-in `re` module
- ✅ Keep code/docs/tests in sync: Document discovery patterns in config comments

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Patterns compile correctly; language aliases work; validation logic correct |
| **Completeness** | Supports fence patterns, language aliases, flags; three-level config hierarchy works |
| **Robustness** | Invalid patterns handled gracefully; missing config uses defaults; no crashes on malformed config |
| **Testability** | Tests verify pattern compilation, language normalization, config hierarchy |
| **Documentation** | Config schema documented with examples; docstrings explain pattern format |
| **Integration** | Works seamlessly with existing discovery; backward compatible; enables multi-language support |

### Now (Runbook)

```bash
# 1. Read existing discovery service constants
grep -n "FENCE_PATTERN\|VALIDATABLE_LANGUAGES" src/services/discovery_service.py

# 2. Create DiscoveryPatternsConfig dataclass in src/core/config.py
# Add after FamilyConfig definition around line 150
# Include compile_patterns(), normalize_language(), is_validatable() methods

# 3. Update FamilyConfig to include discovery_patterns field
# Add: discovery_patterns: Optional[DiscoveryPatternsConfig] = None

# 4. Update GlobalConfig to include default_discovery_patterns
# Add: default_discovery_patterns: DiscoveryPatternsConfig = field(default_factory=DiscoveryPatternsConfig)

# 5. Update config/global.json with default_discovery_patterns section

# 6. Update config/families/zip.json with discovery_patterns section (optional, to show example)

# 7. Update DiscoveryService.__init__() to accept discovery_config parameter
# Add: self.discovery_config = discovery_config or DiscoveryPatternsConfig()

# 8. Update discover_family() to load config hierarchy
# Load family config → global config → hardcoded defaults

# 9. Refactor _extract_inline_examples() to use self.discovery_config
# Replace FENCE_PATTERN usage with self.discovery_config.compile_patterns()
# Replace VALIDATABLE_LANGUAGES check with self.discovery_config.is_validatable()

# 10. Create test file tests/test_pattern_loading.py
# Test config loading, pattern compilation, language aliases

# 11. Run tests
pytest tests/test_pattern_loading.py -v

# 12. Integration test with custom patterns
# Edit config/families/zip.json to add discovery_patterns
# Run: python -m cli scan --family zip --max-files 5

# 13. Verify custom patterns work
# Check logs for "Using discovery patterns: ..."

# 14. Test language alias
# Change validatable_languages to ["python"] in a test config
# Verify python/py examples extracted

# 15. Test invalid pattern handling
# Add invalid regex to config, verify warning logged and default used
```

---

## Taskcard CD-02: Add Line Count and Content-Based Filtering

**Status:** Not Started

**Gap Linkage:** Fixes CD-GAP-03 (No line count filtering), CD-GAP-05 (No exclude patterns)

**Role:** Senior engineer delivering production-ready snippet filtering for quality control.

### Scope

**Fix:**
- Add `min_lines` and `max_lines` filters to exclude trivial or overly complex snippets
- Add `exclude_patterns` regex list to skip specific content patterns
- Add `include_only_patterns` for allow-list filtering
- Add content filters: comments-only detection, empty code detection
- Track filtered snippets in telemetry for visibility
- Support per-family filter configuration

**Allowed paths:**
- `src/services/discovery_service.py` - implement filtering logic
- `src/core/config.py` - add FilterConfig to DiscoveryPatternsConfig
- `config/families/zip.json` - example filter configuration
- `config/global.json` - default filters
- `tests/test_code_filtering.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Add filters to `config/families/zip.json`:
  ```json
  {
    "discovery_patterns": {
      "filters": {
        "min_lines": 3,
        "max_lines": 500,
        "exclude_patterns": [
          "^\\s*//.*TODO.*$",
          "Console\\.WriteLine\\(\"Hello"
        ],
        "exclude_comments_only": true,
        "exclude_empty_code": true
      }
    }
  }
  ```
- Run `python -m cli scan --family zip`
- Verify 1-2 line snippets excluded (below min_lines)
- Verify snippets matching exclude_patterns skipped
- Check telemetry: `filtered_snippets` metric shows count

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest tests/test_code_filtering.py -v` passes
- Test min_lines filter excludes short snippets
- Test max_lines filter excludes long snippets
- Test exclude_patterns skip matching code
- Test comments-only detection works
- Test empty code detection works
- Test filtered snippets counted in stats

**Config respected end-to-end:**
- Filters applied during discovery phase
- Filtered snippets excluded from database
- Telemetry tracks filter reasons

**No mock data in production paths:**
- Real code filtering on production markdown
- Mock code snippets in tests

### Deliverables

1. **Updated `src/core/config.py`:**
   - Add `FilterConfig` dataclass:
     ```python
     @dataclass
     class FilterConfig:
         """Configuration for code snippet filtering."""
         min_lines: int = 0  # 0 = no minimum
         max_lines: int = 0  # 0 = no maximum
         exclude_patterns: List[str] = field(default_factory=list)
         include_only_patterns: List[str] = field(default_factory=list)
         exclude_comments_only: bool = True
         exclude_empty_code: bool = True

         def compile_exclude_patterns(self) -> List[re.Pattern]:
             """Compile exclude patterns."""
             import re
             patterns = []
             for pattern_str in self.exclude_patterns:
                 try:
                     patterns.append(re.compile(pattern_str, re.MULTILINE))
                 except re.error as e:
                     logger.warning(f"Invalid exclude pattern {pattern_str}: {e}")
             return patterns

         def compile_include_patterns(self) -> List[re.Pattern]:
             """Compile include-only patterns."""
             import re
             patterns = []
             for pattern_str in self.include_only_patterns:
                 try:
                     patterns.append(re.compile(pattern_str, re.MULTILINE))
                 except re.error as e:
                     logger.warning(f"Invalid include pattern {pattern_str}: {e}")
             return patterns

         def should_exclude(self, code: str) -> Tuple[bool, Optional[str]]:
             """
             Check if code should be excluded.

             Returns:
                 (should_exclude: bool, reason: str)
             """
             lines = code.strip().split('\n')
             non_empty_lines = [l for l in lines if l.strip()]

             # Line count filters
             if self.min_lines > 0 and len(non_empty_lines) < self.min_lines:
                 return True, f"below_min_lines_{self.min_lines}"

             if self.max_lines > 0 and len(non_empty_lines) > self.max_lines:
                 return True, f"above_max_lines_{self.max_lines}"

             # Empty code check
             if self.exclude_empty_code and not code.strip():
                 return True, "empty_code"

             # Comments-only check (C# style, can be extended)
             if self.exclude_comments_only:
                 code_lines = [l.strip() for l in non_empty_lines
                               if not l.strip().startswith('//')
                               and not l.strip().startswith('/*')
                               and not l.strip().startswith('*')
                               and not l.strip() == '*/']
                 if not code_lines:
                     return True, "comments_only"

             # Exclude patterns
             exclude_compiled = self.compile_exclude_patterns()
             for pattern in exclude_compiled:
                 if pattern.search(code):
                     return True, f"exclude_pattern_matched:{pattern.pattern[:50]}"

             # Include-only patterns (if specified, code must match at least one)
             if self.include_only_patterns:
                 include_compiled = self.compile_include_patterns()
                 matched = False
                 for pattern in include_compiled:
                     if pattern.search(code):
                         matched = True
                         break
                 if not matched:
                     return True, "include_pattern_not_matched"

             return False, None
     ```
   - Add `filters: FilterConfig` field to `DiscoveryPatternsConfig`

2. **Updated `config/global.json`:**
   ```json
   {
     "default_discovery_patterns": {
       "filters": {
         "min_lines": 2,
         "max_lines": 1000,
         "exclude_patterns": [],
         "include_only_patterns": [],
         "exclude_comments_only": true,
         "exclude_empty_code": true
       },
       ...
     }
   }
   ```

3. **Updated `config/families/zip.json`:**
   ```json
   {
     "discovery_patterns": {
       "filters": {
         "min_lines": 3,
         "max_lines": 500,
         "exclude_patterns": [
           "Console\\.WriteLine\\(\"Hello World"
         ]
       }
     }
   }
   ```

4. **Updated `src/services/discovery_service.py`:**
   - Update `_extract_inline_examples()` to apply filters:
     ```python
     # After extracting code content
     if self.discovery_config.is_validatable(language) and code_content.strip():
         # Apply filters before creating example
         should_exclude, reason = self.discovery_config.filters.should_exclude(code_content)

         if should_exclude:
             logger.debug(f"Filtered snippet in {file_path}:{i} - reason: {reason}")
             stats['filtered_snippets'] += 1
             stats['filter_reasons'][reason] = stats['filter_reasons'].get(reason, 0) + 1
             continue  # Skip this snippet

         # Create example record...
     ```
   - Update `discover_family()` to initialize filter stats:
     ```python
     stats = {
         'files_found': 0,
         'files_processed': 0,
         'examples_found': 0,
         'inline_examples': 0,
         'gist_examples': 0,
         'filtered_snippets': 0,  # NEW
         'filter_reasons': {},     # NEW: {reason: count}
         'errors': 0,
     }
     ```
   - Log filter statistics at end:
     ```python
     if stats['filtered_snippets'] > 0:
         logger.info(f"Filtered {stats['filtered_snippets']} snippets:")
         for reason, count in stats['filter_reasons'].items():
             logger.info(f"  - {reason}: {count}")
     ```

5. **New test file `tests/test_code_filtering.py`:**
   - `test_min_lines_filter_excludes_short_snippets`
   - `test_max_lines_filter_excludes_long_snippets`
   - `test_exclude_pattern_matches_skip_snippet`
   - `test_comments_only_detection`
   - `test_empty_code_detection`
   - `test_include_only_patterns_allow_list`
   - `test_filter_stats_tracked`
   - `test_no_filters_includes_all`

6. **Forward-compatible migration:**
   - Default filters have min_lines=0, max_lines=0 (no filtering for backward compat)
   - Existing families inherit defaults (no filtering unless configured)

### Hard Rules

- ✅ Keep public signatures: Filtering is internal to discovery service
- ✅ Deterministic runs: Same code + config → same filtering result
- ✅ No new deps: Use built-in `re` module
- ✅ Keep code/docs/tests in sync: Document filter config schema

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Line counts accurate; patterns match correctly; comments detection works |
| **Completeness** | All filter types work; stats tracked; reasons logged |
| **Robustness** | Edge cases handled (empty code, all comments, boundary conditions) |
| **Testability** | Tests cover all filter types; tests verify stats tracking |
| **Documentation** | Filter config documented with examples; filter reasons clear |
| **Integration** | Works seamlessly with discovery; telemetry includes filter stats |

### Now (Runbook)

```bash
# 1. Create FilterConfig dataclass in src/core/config.py
# Include should_exclude() method with all filter logic

# 2. Add filters field to DiscoveryPatternsConfig
# Add: filters: FilterConfig = field(default_factory=FilterConfig)

# 3. Update global.json with default filters section

# 4. Update discovery_service.py to apply filters
# In _extract_inline_examples(), call should_exclude() before creating example

# 5. Add filter stats tracking to discover_family()
# Track filtered_snippets count and filter_reasons dict

# 6. Log filter statistics at end of discovery
# Show breakdown of filter reasons

# 7. Create test file tests/test_code_filtering.py
# Test all filter types

# 8. Run tests
pytest tests/test_code_filtering.py -v

# 9. Integration test with filters
# Add min_lines=3 to config, run scan on content with short snippets
# Verify short snippets excluded

# 10. Verify telemetry
# Check stats output includes filtered_snippets and filter_reasons
```

---

## Taskcard CD-03: Make Gist Pattern Detection Configurable

**Status:** Not Started

**Gap Linkage:** Fixes CD-GAP-04 (Hardcoded gist patterns)

**Role:** Senior engineer delivering configurable gist detection for multi-platform support.

### Scope

**Fix:**
- Move `GIST_SHORTCODE_PATTERN` and `GIST_SCRIPT_PATTERN` from hardcoded to config
- Support multiple gist platforms (GitHub, GitLab, Bitbucket)
- Allow custom gist shortcode formats per family
- Add enable/disable toggle for gist extraction
- Support gist filtering by owner/organization

**Allowed paths:**
- `src/services/discovery_service.py` - read gist patterns from config
- `src/core/config.py` - add GistPatternsConfig
- `config/families/zip.json` - example gist configuration
- `config/global.json` - default gist patterns
- `tests/test_gist_patterns.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Add gist config to `config/families/zip.json`:
  ```json
  {
    "discovery_patterns": {
      "gist_extraction": {
        "enabled": true,
        "shortcode_patterns": [
          "\\{\\{<\\s*gist\\s+([^\\s]+)\\s+([^\\s]+)(?:\\s+[\"']?([^\"'>\\s]+)[\"']?)?\\s*>\\}\\}",
          "\\[gist:([^/]+)/([^/]+)/([^\\]]+)\\]"
        ],
        "script_patterns": [
          "<script\\s+src=[\"']https://gist\\.github\\.com/([^/]+)/([^.]+)\\.js(?:\\?file=([^\"']+))?[\"']"
        ],
        "allowed_owners": ["aspose-com-gists", "aspose-zip"],
        "blocked_owners": ["spam-account"]
      }
    }
  }
  ```
- Run `python -m cli scan --family zip`
- Verify gists extracted with custom patterns
- Verify gists from blocked_owners skipped
- Set `enabled: false` and verify no gists extracted

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest tests/test_gist_patterns.py -v` passes
- Test default gist patterns work
- Test custom shortcode pattern matches
- Test allowed_owners filter works
- Test blocked_owners filter works
- Test gist extraction can be disabled
- Test multiple gist patterns supported

**Config respected end-to-end:**
- Gist extraction respects enabled flag
- Owner filters applied correctly
- Custom patterns override defaults

**No mock data in production paths:**
- Real gist pattern matching on markdown
- Mock gist references in tests

### Deliverables

1. **Updated `src/core/config.py`:**
   - Add `GistPatternsConfig` dataclass:
     ```python
     @dataclass
     class GistPatternsConfig:
         """Configuration for gist detection patterns."""
         enabled: bool = True
         shortcode_patterns: List[str] = field(default_factory=lambda: [
             r'\{\{<\s*gist\s+([^\s]+)\s+([^\s]+)(?:\s+["\']?([^"\'>\\s]+)["\']?)?\s*>\}\}',
         ])
         script_patterns: List[str] = field(default_factory=lambda: [
             r'<script\s+src=["\']https://gist\.github\.com/([^/]+)/([^.]+)\.js(?:\?file=([^"\']+))?["\']',
         ])
         allowed_owners: List[str] = field(default_factory=list)  # Empty = all allowed
         blocked_owners: List[str] = field(default_factory=list)

         def compile_shortcode_patterns(self) -> List[re.Pattern]:
             """Compile shortcode patterns."""
             import re
             patterns = []
             for pattern_str in self.shortcode_patterns:
                 try:
                     patterns.append(re.compile(pattern_str, re.IGNORECASE))
                 except re.error as e:
                     logger.warning(f"Invalid gist shortcode pattern {pattern_str}: {e}")
             return patterns

         def compile_script_patterns(self) -> List[re.Pattern]:
             """Compile script tag patterns."""
             import re
             patterns = []
             for pattern_str in self.script_patterns:
                 try:
                     patterns.append(re.compile(pattern_str, re.IGNORECASE))
                 except re.error as e:
                     logger.warning(f"Invalid gist script pattern {pattern_str}: {e}")
             return patterns

         def should_include_owner(self, owner: str) -> Tuple[bool, Optional[str]]:
             """Check if gist owner should be included."""
             # Check blocked first
             if owner in self.blocked_owners:
                 return False, f"blocked_owner:{owner}"

             # Check allowed (empty = all allowed)
             if self.allowed_owners and owner not in self.allowed_owners:
                 return False, f"not_in_allowed_owners"

             return True, None
     ```
   - Add `gist_extraction: GistPatternsConfig` field to `DiscoveryPatternsConfig`

2. **Updated `config/global.json`:**
   ```json
   {
     "default_discovery_patterns": {
       "gist_extraction": {
         "enabled": true,
         "shortcode_patterns": [
           "\\{\\{<\\s*gist\\s+([^\\s]+)\\s+([^\\s]+)(?:\\s+[\"']?([^\"'>\\s]+)[\"']?)?\\s*>\\}\\}",
           "\\[gist:([^/]+)/([^/]+)/([^\\]]+)\\]"
         ],
         "script_patterns": [
           "<script\\s+src=[\"']https://gist\\.github\\.com/([^/]+)/([^.]+)\\.js(?:\\?file=([^\"']+))?[\"']",
           "<script\\s+src=[\"']https://gitlab\\.com/([^/]+)/-/snippets/([^/]+)\\.js[\"']"
         ],
         "allowed_owners": [],
         "blocked_owners": []
       },
       ...
     }
   }
   ```

3. **Updated `src/services/discovery_service.py`:**
   - Remove hardcoded `GIST_SHORTCODE_PATTERN` and `GIST_SCRIPT_PATTERN`
   - Update `_extract_gist_examples()`:
     ```python
     def _extract_gist_examples(
         self,
         content: str,
         file_path: str,
         family: str
     ) -> List[ExampleRecord]:
         """Extract gist references with configurable patterns."""
         examples = []

         # Check if gist extraction enabled
         if not self.discovery_config.gist_extraction.enabled:
             return examples

         lines = content.split('\n')
         topic = self._extract_topic_from_path(file_path)

         # Try all shortcode patterns
         shortcode_patterns = self.discovery_config.gist_extraction.compile_shortcode_patterns()
         for i, line in enumerate(lines):
             for pattern in shortcode_patterns:
                 for match in pattern.finditer(line):
                     owner = match.group(1)
                     gist_id = match.group(2)
                     filename = match.group(3) if len(match.groups()) >= 3 else ""

                     # Apply owner filter
                     should_include, reason = self.discovery_config.gist_extraction.should_include_owner(owner)
                     if not should_include:
                         logger.debug(f"Filtered gist {owner}/{gist_id} - reason: {reason}")
                         stats['filtered_gists'] = stats.get('filtered_gists', 0) + 1
                         continue

                     # Create gist example...

         # Try all script patterns
         script_patterns = self.discovery_config.gist_extraction.compile_script_patterns()
         # Similar logic for script tags...

         return examples
     ```

4. **New test file `tests/test_gist_patterns.py`:**
   - `test_default_gist_shortcode_pattern`
   - `test_default_gist_script_pattern`
   - `test_custom_shortcode_pattern`
   - `test_allowed_owners_filter`
   - `test_blocked_owners_filter`
   - `test_gist_extraction_disabled`
   - `test_multiple_gist_patterns`
   - `test_gitlab_snippet_pattern`

5. **Forward-compatible migration:**
   - Default patterns match previous hardcoded values
   - Gist extraction enabled by default (backward compatible)

### Hard Rules

- ✅ Keep public signatures: Gist extraction is internal to discovery
- ✅ Deterministic runs: Same content + config → same gist extraction
- ✅ No new deps: Use built-in `re` module
- ✅ Keep code/docs/tests in sync: Document gist pattern config

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Gist patterns match correctly; owner filters work; extraction can be disabled |
| **Completeness** | Multiple patterns supported; shortcode and script tags; owner filtering |
| **Robustness** | Invalid patterns handled; missing owners don't crash; graceful degradation |
| **Testability** | Tests verify pattern matching, owner filtering, enable/disable toggle |
| **Documentation** | Gist config documented with examples; pattern format explained |
| **Integration** | Works with existing gist resolution; backward compatible |

### Now (Runbook)

```bash
# 1. Create GistPatternsConfig dataclass in src/core/config.py
# Include should_include_owner() method

# 2. Add gist_extraction field to DiscoveryPatternsConfig
# Add: gist_extraction: GistPatternsConfig = field(default_factory=GistPatternsConfig)

# 3. Update global.json with gist_extraction section

# 4. Update discovery_service.py to use configurable patterns
# Remove hardcoded GIST_SHORTCODE_PATTERN and GIST_SCRIPT_PATTERN
# Use self.discovery_config.gist_extraction patterns

# 5. Apply owner filters in _extract_gist_examples()
# Call should_include_owner() for each gist

# 6. Add gist filter stats to discovery stats
# Track filtered_gists count

# 7. Create test file tests/test_gist_patterns.py
# Test all gist pattern scenarios

# 8. Run tests
pytest tests/test_gist_patterns.py -v

# 9. Integration test with custom gist patterns
# Add blocked_owners to config
# Verify gists from blocked owners skipped

# 10. Test with gist extraction disabled
# Set enabled=false, verify no gists extracted
```

---

## Taskcard CD-04: Make Context Extraction Configurable

**Status:** Not Started

**Gap Linkage:** Fixes CD-GAP-06 (Context extraction not configurable)

**Role:** Senior engineer delivering configurable context extraction for improved LLM prompts.

### Scope

**Fix:**
- Make `max_paragraphs` configurable (currently hardcoded to 2)
- Add `max_heading_distance` config (how far to look for headings)
- Add `include_file_header` option to capture file-level context
- Add `context_window_lines` for custom context window size
- Support disabling context extraction for performance

**Allowed paths:**
- `src/services/discovery_service.py` - configurable context extraction
- `src/core/config.py` - add ContextExtractionConfig
- `config/families/zip.json` - example context configuration
- `config/global.json` - default context settings
- `tests/test_context_extraction.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Add context config to `config/families/zip.json`:
  ```json
  {
    "discovery_patterns": {
      "context_extraction": {
        "enabled": true,
        "max_paragraphs": 3,
        "max_heading_distance": 50,
        "include_file_header": true,
        "context_window_lines": 20
      }
    }
  }
  ```
- Run `python -m cli scan --family zip`
- Verify examples have richer context (3 paragraphs vs 2)
- Set `enabled: false` and verify no context extracted (performance mode)

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest tests/test_context_extraction.py -v` passes
- Test max_paragraphs configurable
- Test max_heading_distance limits heading search
- Test include_file_header captures frontmatter
- Test context extraction can be disabled
- Test context_window_lines limits search range

**Config respected end-to-end:**
- Context extraction respects all config options
- Disabled mode improves performance

**No mock data in production paths:**
- Real context extraction on markdown
- Mock markdown in tests

### Deliverables

1. **Updated `src/core/config.py`:**
   - Add `ContextExtractionConfig`:
     ```python
     @dataclass
     class ContextExtractionConfig:
         """Configuration for code context extraction."""
         enabled: bool = True
         max_paragraphs: int = 2
         max_heading_distance: int = 100  # Lines to search for heading
         include_file_header: bool = False  # Include YAML frontmatter
         context_window_lines: int = 50  # Max lines to look back for context
     ```
   - Add `context_extraction: ContextExtractionConfig` to `DiscoveryPatternsConfig`

2. **Updated `config/global.json`:**
   ```json
   {
     "default_discovery_patterns": {
       "context_extraction": {
         "enabled": true,
         "max_paragraphs": 2,
         "max_heading_distance": 100,
         "include_file_header": false,
         "context_window_lines": 50
       },
       ...
     }
   }
   ```

3. **Updated `src/services/discovery_service.py`:**
   - Update `_find_section_heading()`:
     ```python
     def _find_section_heading(self, lines: List[str], code_start: int) -> str:
         max_distance = self.discovery_config.context_extraction.max_heading_distance
         search_start = max(0, code_start - max_distance)

         for i in range(code_start - 1, search_start - 1, -1):
             line = lines[i].strip()
             if line.startswith('#'):
                 return line.lstrip('#').strip()
         return ""
     ```
   - Update `_extract_description_context()`:
     ```python
     def _extract_description_context(self, lines: List[str], code_start: int) -> str:
         if not self.discovery_config.context_extraction.enabled:
             return ""

         max_paragraphs = self.discovery_config.context_extraction.max_paragraphs
         context_window = self.discovery_config.context_extraction.context_window_lines
         search_start = max(0, code_start - context_window)

         # Extract paragraphs within window...
     ```
   - Add `_extract_file_header()`:
     ```python
     def _extract_file_header(self, content: str) -> Optional[str]:
         """Extract YAML frontmatter or file-level comments."""
         if not self.discovery_config.context_extraction.include_file_header:
             return None

         # Try YAML frontmatter (---\n...\n---)
         if content.startswith('---'):
             end_idx = content.find('---', 3)
             if end_idx != -1:
                 return content[3:end_idx].strip()

         return None
     ```

4. **New test file `tests/test_context_extraction.py`:**
   - `test_max_paragraphs_configurable`
   - `test_max_heading_distance_limits_search`
   - `test_include_file_header_captures_frontmatter`
   - `test_context_window_lines_limits_search`
   - `test_context_extraction_disabled_mode`
   - `test_default_context_settings`

5. **Forward-compatible migration:**
   - Default settings match previous hardcoded behavior
   - Context extraction enabled by default

### Hard Rules

- ✅ Keep public signatures: Context extraction internal to discovery
- ✅ Deterministic runs: Same content + config → same context
- ✅ No new deps: Pure Python string processing
- ✅ Keep code/docs/tests in sync: Document context config options

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Context extraction accurate; limits respected; frontmatter parsed correctly |
| **Completeness** | All config options work; enable/disable toggle; performance mode available |
| **Robustness** | Edge cases handled (no heading, no paragraphs, malformed frontmatter) |
| **Testability** | Tests verify all config options; tests cover edge cases |
| **Documentation** | Context config documented; examples show different settings |
| **Integration** | Works with LLM service; provides better prompts; backward compatible |

### Now (Runbook)

```bash
# 1. Create ContextExtractionConfig in src/core/config.py

# 2. Add context_extraction field to DiscoveryPatternsConfig

# 3. Update global.json with context_extraction section

# 4. Update _find_section_heading() to use max_heading_distance

# 5. Update _extract_description_context() to use max_paragraphs and context_window_lines

# 6. Add _extract_file_header() method for frontmatter extraction

# 7. Create test file tests/test_context_extraction.py

# 8. Run tests
pytest tests/test_context_extraction.py -v

# 9. Integration test with different settings
# Set max_paragraphs=5, verify more context captured

# 10. Performance test with disabled mode
# Set enabled=false, verify faster discovery
```

---

## Summary

**4 Taskcards Created:**
- **CD-01:** Make code fence and language detection configurable → Enables multi-language support (Python, Java, etc.)
- **CD-02:** Add line count and content-based filtering → Improves quality by filtering trivial snippets
- **CD-03:** Make gist pattern detection configurable → Supports multiple gist platforms and owner filtering
- **CD-04:** Make context extraction configurable → Improves LLM prompts with customizable context

**Priority Order:**
1. **CD-01** (High - enables multi-language support, critical for expansion)
2. **CD-02** (High - improves quality, reduces noise in pipeline)
3. **CD-03** (Medium - enhances gist support, nice-to-have)
4. **CD-04** (Low - optimization, improves LLM context quality)

**Key Integration Points:**
- All configs follow three-level hierarchy: family config > global config > hardcoded defaults
- Backward compatible: existing families work unchanged with defaults matching previous hardcoded behavior
- Telemetry integration: filter stats tracked for visibility
- Performance: context extraction can be disabled for speed

**Configuration Schema Summary:**
```json
{
  "discovery_patterns": {
    "fence_patterns": ["regex_pattern"],
    "fence_flags": ["MULTILINE", "DOTALL"],
    "validatable_languages": ["cs", "python", "java"],
    "language_aliases": {"csharp": ["cs", "c#"]},
    "filters": {
      "min_lines": 3,
      "max_lines": 500,
      "exclude_patterns": ["regex"],
      "include_only_patterns": ["regex"],
      "exclude_comments_only": true,
      "exclude_empty_code": true
    },
    "gist_extraction": {
      "enabled": true,
      "shortcode_patterns": ["regex"],
      "script_patterns": ["regex"],
      "allowed_owners": ["user1"],
      "blocked_owners": ["spam"]
    },
    "context_extraction": {
      "enabled": true,
      "max_paragraphs": 2,
      "max_heading_distance": 100,
      "include_file_header": false,
      "context_window_lines": 50
    }
  }
}
```

**Total Estimated Effort:** 4-5 days for all taskcards (CD-01: 12h, CD-02: 10h, CD-03: 8h, CD-04: 6h)

**Dependencies:**
- CD-02 builds on CD-01 (filtering requires patterns to be configured)
- CD-03 independent (can be done in parallel)
- CD-04 independent (can be done in parallel)

**Risk Assessment:**
- **Low Risk:** All taskcards (non-breaking, backward compatible, opt-in features)
- **High Value:** CD-01 and CD-02 unlock new use cases and improve quality significantly
