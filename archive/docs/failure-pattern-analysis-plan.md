# Failure Pattern Analysis Enhancement Plan

**Purpose:** Automatically analyze compilation failures to identify common patterns, suggest new auto-fix rules, and improve the overall success rate of code validation.

---

## 1. Problem Statement

Currently, when snippets fail compilation:
- We see individual error messages (CS0103, CS0246, etc.)
- We don't aggregate patterns across failures
- We can't identify which APIs are commonly misused
- Pattern rules are manually created based on ad-hoc observation

**Goal:** Build an automated system to:
1. Aggregate error patterns across all failures
2. Identify most common compilation errors
3. Suggest new pattern rules automatically
4. Track which APIs are most problematic
5. Measure improvement over time

---

## 2. Architecture Overview

### Components

```
┌─────────────────────────────────────────────────────────┐
│         Failure Pattern Analysis Pipeline                │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
       ┌────────────────────────────────────┐
       │   1. Error Extraction Module       │
       │   - Parse compiler output          │
       │   - Extract error codes (CS####)   │
       │   - Extract entity names           │
       │   - Group by error type            │
       └────────────────┬───────────────────┘
                        │
                        ▼
       ┌────────────────────────────────────┐
       │   2. Pattern Detection Module      │
       │   - Identify recurring patterns    │
       │   - Calculate frequency/impact     │
       │   - Detect API name variations     │
       │   - Find common fix strategies     │
       └────────────────┬───────────────────┘
                        │
                        ▼
       ┌────────────────────────────────────┐
       │   3. Rule Suggestion Module        │
       │   - Generate pattern rule specs    │
       │   - Suggest regex patterns         │
       │   - Propose replacement templates  │
       │   - Estimate confidence scores     │
       └────────────────┬───────────────────┘
                        │
                        ▼
       ┌────────────────────────────────────┐
       │   4. Reporting Module              │
       │   - Generate HTML/JSON reports     │
       │   - Visualize top failures         │
       │   - Track improvement metrics      │
       │   - Export suggested rules         │
       └────────────────────────────────────┘
```

---

## 3. Data Model

### Error Pattern Schema

```python
@dataclass
class ErrorPattern:
    """Represents a recurring error pattern."""

    # Identification
    pattern_id: str              # UUID
    error_codes: List[str]       # e.g., ['CS0246', 'CS0103']

    # Pattern details
    description: str             # Human-readable description
    entity_names: List[str]      # e.g., ['SaveAsync', 'DeflateOptions']
    frequency: int               # Number of occurrences
    affected_snippets: List[int] # Snippet IDs

    # Context
    common_context: str          # Common surrounding code
    error_messages: List[str]    # Full error messages

    # Suggested fix
    suggested_pattern: Optional[Dict]  # Pattern rule template
    confidence_score: float            # 0.0 - 1.0

    # Metadata
    first_seen: datetime
    last_seen: datetime
    family: str                  # e.g., 'zip', 'words'
```

### Analysis Report Schema

```python
@dataclass
class AnalysisReport:
    """Analysis report for a validation run."""

    run_id: int
    family: str
    generated_at: datetime

    # Summary statistics
    total_failures: int
    unique_error_codes: List[str]
    unique_patterns: int

    # Top patterns
    top_patterns: List[ErrorPattern]  # Sorted by frequency

    # API issues
    non_existent_api_calls: Dict[str, int]  # API name → count
    deprecated_api_calls: Dict[str, int]

    # Suggested improvements
    suggested_pattern_rules: List[Dict]
    suggested_non_existent_apis: List[str]

    # Trend analysis (if historical data available)
    success_rate_trend: Optional[List[float]]
    pattern_emergence: Optional[List[Dict]]
```

---

## 4. Error Extraction Module

### Implementation: `src/failure_analyzer.py`

```python
class ErrorExtractor:
    """Extracts structured error information from compiler output."""

    # Error code patterns
    ERROR_CODE_PATTERN = r'CS\d{4}:'
    API_NOT_FOUND_PATTERN = r"The name '(\w+)' does not exist"
    TYPE_NOT_FOUND_PATTERN = r"The type or namespace name '(\w+)' could not be found"
    METHOD_NOT_FOUND_PATTERN = r"'(\w+)' does not contain a definition for '(\w+)'"

    def extract_errors(self, compiler_output: str, code: str) -> List[Dict]:
        """
        Extract structured error information.

        Returns list of dicts with:
        - error_code: str (e.g., 'CS0246')
        - error_message: str
        - entity_name: Optional[str] (extracted API/type name)
        - line_number: Optional[int]
        - category: str ('missing_api', 'wrong_signature', 'syntax', etc.)
        """
        pass

    def categorize_error(self, error_code: str, message: str) -> str:
        """
        Categorize error into high-level types:
        - missing_api: API doesn't exist
        - wrong_signature: Method signature mismatch
        - missing_namespace: Using directive needed
        - async_mismatch: Async/await issues
        - syntax: General syntax errors
        """
        pass
```

---

## 5. Pattern Detection Module

### Key Algorithms

#### 1. Frequency Analysis
```python
def find_frequent_patterns(errors: List[ErrorInfo]) -> List[ErrorPattern]:
    """
    Group errors by:
    1. Error code combination
    2. Entity name (if available)
    3. Similar context (using fuzzy matching)

    Return patterns sorted by frequency.
    """
    pass
```

#### 2. API Name Variation Detection
```python
def detect_api_variations(entity_names: List[str]) -> Dict[str, List[str]]:
    """
    Identify common variations of the same API:
    - SaveAsync vs Save
    - CreateEntry vs AddEntry
    - DeflateOptions vs DeflateSettings

    Uses:
    - Edit distance (Levenshtein)
    - Common suffixes (Async, Options, Settings)
    - Semantic similarity
    """
    pass
```

#### 3. Context Pattern Mining
```python
def extract_context_patterns(snippet_code: str, error_entity: str) -> str:
    """
    Extract common code patterns around errors:
    - Variable declarations
    - Method call chains
    - Parameter usage

    Returns: Generalized pattern with placeholders
    """
    pass
```

---

## 6. Rule Suggestion Module

### Auto-Generate Pattern Rules

```python
class RuleSuggester:
    """Suggests new pattern rules based on detected patterns."""

    def suggest_pattern_rule(self, pattern: ErrorPattern) -> Dict:
        """
        Generate a pattern rule suggestion:

        {
          "name": "auto_detected_deflate_options",
          "description": "Replace DeflateOptions with correct API",
          "detection_regex": r"new DeflateOptions\(\)",
          "replacement_template": "new DeflateCompressionSettings()",
          "confidence": 0.85,
          "frequency": 12,
          "test_cases": [...]
        }
        """
        pass

    def generate_regex_from_examples(self, examples: List[str]) -> str:
        """
        Generate regex pattern from example error cases.
        Uses common substring detection and generalization.
        """
        pass

    def infer_replacement(self, wrong_code: str, correct_code: str) -> str:
        """
        Analyze difference between failing and fixed code
        to infer replacement template.
        """
        pass
```

---

## 7. Reporting Module

### Report Types

#### 7.1 Console Summary Report
```
=== Failure Pattern Analysis ===

Top 5 Most Common Errors:
1. CS0246 - Missing type 'DeflateOptions' (23 occurrences)
   → Suggested: Add pattern rule to replace with DeflateCompressionSettings

2. CS0103 - Name 'SaveAsync' does not exist (18 occurrences)
   → Suggested: Add to non_existent_apis list

3. CS0246 - Missing namespace 'System.Linq' (12 occurrences)
   → Suggested: Add to common_usings in workspace_manager.py

4. CS1061 - 'Archive' does not contain 'AddEntry' (8 occurrences)
   → Suggested: Replace with 'CreateEntry' method

5. CS0029 - Cannot convert 'string' to 'CompressionLevel' (5 occurrences)
   → Manual review needed
```

#### 7.2 HTML Interactive Report
- Charts showing error distribution
- Drill-down into each pattern
- View affected snippets
- One-click copy suggested rules

#### 7.3 JSON Export for CI/CD
```json
{
  "analysis_id": "20260109_144500",
  "family": "zip",
  "summary": {
    "total_failures": 43,
    "unique_patterns": 12,
    "suggested_rules": 5,
    "confidence_threshold": 0.7
  },
  "suggested_rules": [
    {
      "name": "auto_deflate_options",
      "add_to": "config/families/zip.json",
      "rule": {...}
    }
  ],
  "suggested_non_existent_apis": [
    "SaveAsync",
    "CreateZipAsync"
  ]
}
```

---

## 8. CLI Integration

### New Commands

```bash
# Run failure analysis on latest validation run
python src/cli.py analyze-failures --family zip

# Run analysis on specific run
python src/cli.py analyze-failures --family zip --run-id 5

# Generate interactive HTML report
python src/cli.py analyze-failures --family zip --format html --output reports/

# Export suggested rules to review
python src/cli.py analyze-failures --family zip --export-rules rules_to_review.json

# Auto-apply high-confidence rules (confidence > 0.9)
python src/cli.py analyze-failures --family zip --auto-apply --min-confidence 0.9
```

---

## 9. Database Schema Extensions

### New Tables

```sql
-- Store detected error patterns
CREATE TABLE error_patterns (
    pattern_id TEXT PRIMARY KEY,
    family TEXT NOT NULL,
    error_codes TEXT NOT NULL,  -- JSON array
    entity_names TEXT,          -- JSON array
    frequency INTEGER DEFAULT 1,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    suggested_rule TEXT,        -- JSON
    confidence_score REAL,
    status TEXT DEFAULT 'detected'  -- detected, reviewed, applied, rejected
);

-- Link patterns to specific build attempts
CREATE TABLE pattern_occurrences (
    occurrence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id TEXT NOT NULL,
    build_attempt_id INTEGER NOT NULL,
    snippet_id INTEGER NOT NULL,
    FOREIGN KEY (pattern_id) REFERENCES error_patterns(pattern_id),
    FOREIGN KEY (build_attempt_id) REFERENCES build_attempts(attempt_id),
    FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id)
);

-- Store analysis reports
CREATE TABLE analysis_reports (
    report_id TEXT PRIMARY KEY,
    run_id INTEGER NOT NULL,
    family TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_failures INTEGER,
    unique_patterns INTEGER,
    report_json TEXT,  -- Full JSON report
    FOREIGN KEY (run_id) REFERENCES validation_runs(run_id)
);
```

---

## 10. Implementation Phases

### Phase 1: Basic Error Extraction (Week 1)
- [x] Parse compiler output
- [ ] Extract error codes and messages
- [ ] Categorize errors
- [ ] Store in database
- [ ] Basic console report

### Phase 2: Pattern Detection (Week 2)
- [ ] Frequency analysis
- [ ] Group similar errors
- [ ] Detect API name variations
- [ ] Context extraction
- [ ] Pattern scoring

### Phase 3: Rule Suggestions (Week 3)
- [ ] Generate pattern rules
- [ ] Regex generation
- [ ] Replacement templates
- [ ] Confidence scoring
- [ ] JSON export

### Phase 4: Advanced Reporting (Week 4)
- [ ] HTML report generator
- [ ] Interactive visualizations
- [ ] Trend analysis
- [ ] Historical comparison
- [ ] Export to multiple formats

### Phase 5: Automation (Week 5)
- [ ] Auto-apply high-confidence rules
- [ ] CI/CD integration
- [ ] Scheduled analysis
- [ ] Alert on new patterns
- [ ] Continuous improvement loop

---

## 11. Example Usage Workflow

### Scenario: Developer runs validation and gets 43 failures

```bash
# 1. Run validation (as usual)
python src/cli.py validate --family zip

# Output shows: 35 verified, 43 needs fix

# 2. Analyze failure patterns
python src/cli.py analyze-failures --family zip

# Output:
#   - Top 5 error patterns identified
#   - 3 pattern rules suggested with high confidence
#   - 2 APIs detected as non-existent

# 3. Review suggested rules
python src/cli.py analyze-failures --family zip --export-rules review.json

# Developer reviews review.json, approves 2 rules

# 4. Apply approved rules
# Manually add to config/families/zip.json
# OR auto-apply:
python src/cli.py analyze-failures --family zip --apply-rules review_approved.json

# 5. Re-run validation
python src/cli.py validate --family zip

# Output shows: 41 verified, 37 needs fix (6 more fixed!)

# 6. Iterate
```

---

## 12. Success Metrics

### Measurable Goals

1. **Pattern Detection Accuracy**
   - Target: 90% of manually identified patterns are auto-detected
   - Measure: Compare with human-reviewed pattern list

2. **Rule Suggestion Quality**
   - Target: 70% of high-confidence suggestions (>0.8) are accepted
   - Measure: Track acceptance rate of suggested rules

3. **Improvement Rate**
   - Target: Each iteration improves success rate by 5-10%
   - Measure: Track success_rate across runs

4. **Time Savings**
   - Target: Reduce manual pattern identification time by 80%
   - Measure: Time spent on manual vs automated analysis

---

## 13. Advanced Features (Future)

### Machine Learning Integration
- Train ML model on (error, fix) pairs
- Predict best fix strategy for new errors
- Learn from Ollama's successful fixes

### Cross-Family Learning
- Identify patterns common across all Aspose families
- Share fix strategies between families
- Build universal rule library

### Semantic Code Analysis
- Use AST parsing for deeper understanding
- Identify logical errors (not just syntax)
- Suggest architectural improvements

---

## 14. Files to Create/Modify

### New Files
```
src/failure_analyzer.py          # Main analysis module
src/error_extractor.py           # Error parsing
src/pattern_detector.py          # Pattern identification
src/rule_suggester.py            # Rule generation
src/report_generator.py          # Report creation
templates/analysis_report.html   # HTML report template
```

### Modified Files
```
src/cli.py                       # Add analyze-failures command
src/database.py                  # New tables
src/validation_orchestrator.py  # Hook into analysis
config/schema.sql                # New schema
```

---

## Conclusion

This failure pattern analysis system will transform the code review process from reactive (manually fixing errors) to proactive (automatically identifying and suggesting fixes for common patterns). By building a feedback loop that learns from failures, the system continuously improves and reduces manual intervention over time.

**Next Steps:**
1. Implement Phase 1 (Basic Error Extraction)
2. Validate with Aspose.ZIP failures
3. Iterate based on results
4. Extend to other Aspose families
