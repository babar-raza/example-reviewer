# Family Knowledge-Base (KB) Subsystem

The Family KB subsystem encodes human-curated knowledge about known API misuses
for specific Aspose product families. It operates in two independent layers:

| Layer | File | Phase | Mechanism |
|-------|------|-------|-----------|
| LLM Guidance | `{family}_review_hints.json` | Phase B + D + D.5 | Injects warnings into LLM prompts |
| Deterministic Enforcement | `{family}_behavioral_patterns.json` | Phase D.4 | Regex-based gating scan |

Both file types live in `config/families/`. The infrastructure is generic —
any family can have KB files. Only `words` currently has them.

---

## Why Two Files?

The files serve architecturally different purposes and should not be merged:

- **Review hints** inject formatted natural language into LLM prompts. They
  override LLM deference to article prose when the prose is wrong.
- **Behavioral patterns** run deterministic regex scans without an LLM.
  They provide consistent, reproducible enforcement unaffected by LLM variation.
  Patterns with `severity: "error"` are **blocking** and can gate pipeline output.

---

## Schema Reference

Full schema for both file types is documented in `config/README.md`.

### Quick Reference: `{family}_review_hints.json`

```json
[
  {
    "id": "words-01",
    "hint": "WriteProtection.SetPassword only restricts editing; it does NOT encrypt.",
    "pattern": "WriteProtection.SetPassword",
    "context": "encrypt",
    "issue_type": "semantic_misuse",
    "correction": "Use OoxmlSaveOptions.Password for real encryption.",
    "detection_keywords": ["WriteProtection", "SetPassword"]
  }
]
```

Required: `id`, `hint`. All other fields are optional.

### Quick Reference: `{family}_behavioral_patterns.json`

```json
[
  {
    "id": "words_write_protection_not_encryption",
    "severity": "error",
    "description": "WriteProtection.SetPassword is used where encryption is intended.",
    "code_regex": "WriteProtection\\.SetPassword",
    "intent_keywords": ["encrypt", "password protect"],
    "suggestion": "Use OoxmlSaveOptions.Password instead."
  }
]
```

Required: `id`, `severity`, `description`, plus at least one of `code_regex` or `required_regex`.

---

## Lifecycle

```
1. CREATION     → Author writes {family}_{type}.json
2. VALIDATION   → Schema validates structure + regex syntax at load time
3. REVIEW       → PR review (see Governance below)
4. RUNTIME LOAD → Generic loader reads + validates on first use per pipeline run
5. AUDIT        → Periodic review against current API version
6. RETIREMENT   → Pattern removed + tests updated
```

---

## Adding a New Family KB

### Step 1: Create the file

For review hints, create `config/families/{family}_review_hints.json` with at
least one entry. Minimum viable entry:

```json
[{"id": "myfam-01", "hint": "Describe the misuse here."}]
```

For behavioral patterns, add `config/families/{family}_behavioral_patterns.json`.
Every pattern must have `id`, `severity`, `description`, and at least one regex field:

```json
[
  {
    "id": "myfam_example_issue",
    "severity": "warning",
    "description": "Brief description of what is wrong.",
    "code_regex": "MyApi\\.BadMethod",
    "suggestion": "Use MyApi.GoodMethod instead."
  }
]
```

### Step 2: Validate locally

```bash
python scripts/validate_kb.py --family myfam
```

Exit 0 = valid. Any structural error or invalid regex is caught here.

### Step 3: Write tests

Add at minimum one structural test in `tests/test_kb_structure.py`:

```python
def test_myfam_review_hints_loads():
    hints = KnowledgeBaseLoader.load_review_hints("myfam", config_dir="config/families")
    assert len(hints) >= 1
```

For behavioral patterns, add a positive test (pattern fires on bad code) and
a negative test (pattern does not fire on clean code).

### Step 4: Open a PR

- Review hints: one reviewer approval required.
- Behavioral patterns with `severity: "error"` or `"critical"`: **two reviewer approvals**
  required (second reviewer confirms regex correctness and understands gating implications).
- PR description must explain the misuse, include a code example, and reference
  the Aspose API documentation where applicable.

---

## Governance

### Severity levels and gating

| Severity | Blocking? | Effect |
|----------|-----------|--------|
| `"error"` | Yes | Example may be marked `NEEDS_REVIEW`; triggers fix-and-rescan loop |
| `"critical"` | Yes | Same as `"error"` |
| `"warning"` | No | Finding reported but does not gate output |

Blocking patterns require the highest scrutiny before merging.

### Modifying existing patterns

- Changing a pattern's `code_regex` or `required_regex`: requires the same
  review tier as creation (two reviewers if severity is `"error"` or `"critical"`).
- Adding `intent_keywords` to narrow a noisy pattern: one reviewer.
- Removing a pattern: one reviewer; PR must document why (stale API? false positive?).

### Repository enforcement setup (admin action required)

CODEOWNERS-based enforcement requires two steps beyond committing the `CODEOWNERS` file:

1. **Push the `CODEOWNERS` file** (root of repo — GitLab checks root, `docs/`, and `.gitlab/`).
2. **Enable "Require code owner approval"** in GitLab project settings:
   - Navigate to: `Settings > Repository > Protected branches`
   - Find the `main` branch entry; click `Edit`
   - Enable `Allowed to push: No one` (or a restricted group) and `Require code owner approval: Yes`
   - Save.

Until step 2 is completed, the `CODEOWNERS` file is present and parsed by GitLab but does NOT block merges. File existence ≠ enforcement. This is a project admin action that cannot be done through a code commit.

**MR templates** (`.gitlab/merge_request_templates/`) are auto-discovered by GitLab once pushed. No additional admin action is required.

### API version maintenance

Some patterns reference version-specific API changes (e.g., `Comment.Text` setter
removed in Aspose.Words v26.1.0). When the library version changes:

1. Run `python scripts/validate_kb.py --family {family}` to confirm files still parse.
2. Review pattern `description` fields that mention version numbers.
3. Update or retire stale patterns via PR.

---

## Runtime Error Behavior

| Condition | Effect |
|-----------|--------|
| File does not exist | Returns `[]` — valid, family has no KB yet |
| File contains invalid JSON | Raises `KBLoadError`, logged at `ERROR` level |
| Schema validation fails | Raises `KBLoadError`, logged at `ERROR` level |
| Regex field is invalid | Raises `KBLoadError` at load time (not silently at scan time) |

When a `KBLoadError` is raised for `{family}_behavioral_patterns.json`, the
behavioral scan phase aborts for that family with `stats["kb_load_error"] = True`.
No silent degradation occurs.

---

## Family Coverage

| Family | Review Hints | Behavioral Patterns | Notes |
|--------|-------------|--------------------|-|
| `words` | 9 hints | 10 patterns (8 blocking) | Pilot family; full coverage |
| `pdf` | None | None | Not yet assessed |
| `slides` | None | None | Not yet assessed |
| `cells` | None | None | Not yet assessed |
| All others | None | None | Not yet assessed |

Families without KB files receive no LLM guidance override and no deterministic
enforcement. This is valid — it does not break the pipeline. It means any API
misuse in those families is caught only by the general LLM review.

---

## Module Reference

The KB subsystem lives in `src/services/kb/`:

| File | Contents |
|------|----------|
| `src/services/kb/__init__.py` | Package init; re-exports `KBLoadError`, `KnowledgeBaseLoader`, `ReviewHint`, `BehavioralPattern` |
| `src/services/kb/models.py` | Pydantic v2 models for `ReviewHint` and `BehavioralPattern` |
| `src/services/kb/loader.py` | `KnowledgeBaseLoader` static loader + `KBLoadError` exception |

Import from the package root:

```python
from src.services.kb import KBLoadError, KnowledgeBaseLoader, ReviewHint, BehavioralPattern
```
