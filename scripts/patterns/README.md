# scripts/patterns/ - Auto-Learn Pattern Management

Scripts for extracting, reviewing, and promoting learned fix patterns.

The auto-learn system observes successful LLM fixes and extracts reusable patterns
that can be applied deterministically in future runs.

## Scripts

| Script | Purpose |
|--------|---------|
| `auto_learn.py` | Core pattern extraction engine (clusters failures, extracts patterns via LLM) |
| `review_patterns.py` | Interactive review of pending patterns |
| `detect_manual_fixes.py` | Detect manually-applied fixes that could become patterns |
| `deduplicate_patterns.py` | Remove duplicate patterns across families |
| `promote_global_patterns.py` | Promote family-specific patterns to global scope |
| `inventory_repo_fixtures.py` | Inventory test fixtures across the repository |
