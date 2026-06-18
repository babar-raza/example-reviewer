## Summary
<!-- What does this MR change and why? -->


## KB Changes (complete this section if any `config/families/` files are modified)

- [ ] `python scripts/validate_kb.py --all` runs clean locally
- [ ] New/changed patterns have been tested against real code samples that should trigger them
- [ ] New/changed patterns have been tested against clean samples that should NOT trigger them
- [ ] Patterns with `severity: "error"` or `"critical"` have a second reviewer assigned (see CODEOWNERS)
- [ ] If a pattern references a specific API version (e.g., "removed in v26.1.0"), the version is noted in `description`
- [ ] `docs/development/family-kb.md` "Family Coverage" table is updated if a new family KB was added
- [ ] Structural tests exist or have been added (see `tests/test_kb_structure.py`)


## Test Plan
<!-- How was this tested? Include the pytest output or note which tests cover this change. -->


## Checklist

- [ ] CI passes (unit tests + validate-kb step)
- [ ] Relevant documentation updated if behaviour changed
