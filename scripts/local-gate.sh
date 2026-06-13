#!/usr/bin/env bash
# local-gate.sh — Pre-push quality gate for Example Reviewer Pipeline.
#
# Run this before pushing to catch issues locally:
#   bash scripts/local-gate.sh
#
# Exit codes:
#   0 = all checks passed
#   1 = one or more checks failed

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

FAILURES=0

step() { echo -e "\n${YELLOW}=== $1 ===${NC}"; }
pass() { echo -e "${GREEN}PASS${NC}: $1"; }
fail() { echo -e "${RED}FAIL${NC}: $1"; FAILURES=$((FAILURES + 1)); }

# 1. Static analysis — import chain check
step "Static analysis (import chains)"
if python scripts/validation/analyze_cli_imports.py src/cli/main.py && \
   python scripts/validation/analyze_cli_imports.py src/pipeline/orchestrator.py && \
   python scripts/validation/analyze_cli_imports.py src/core/database.py; then
    pass "Import chain analysis"
else
    fail "Import chain analysis"
fi

# 2. Unit tests with coverage threshold
step "Unit tests (coverage >= 50%)"
if pytest tests/ -v --timeout=120 \
    --cov=src --cov-fail-under=50 \
    --cov-report=term-missing \
    -m "not integration and not runtime" -q; then
    pass "Unit tests with coverage"
else
    fail "Unit tests with coverage"
fi

# 3. Security scan (bandit)
step "Security scan (bandit)"
if command -v bandit &>/dev/null; then
    if bandit -r src/ -ll -q 2>/dev/null; then
        pass "Bandit security scan"
    else
        fail "Bandit security scan"
    fi
else
    echo "  bandit not installed — skipping (pip install bandit)"
fi

# 4. Dependency audit
step "Dependency audit (pip-audit)"
if command -v pip-audit &>/dev/null; then
    if pip-audit -r requirements.txt --desc 2>/dev/null; then
        pass "Dependency audit"
    else
        fail "Dependency audit"
    fi
else
    echo "  pip-audit not installed — skipping (pip install pip-audit)"
fi

# 5. KB validation
step "Knowledge base validation"
if python scripts/validate_kb.py --all 2>/dev/null; then
    pass "KB validation"
else
    fail "KB validation"
fi

# Summary
echo ""
step "Summary"
if [ "$FAILURES" -eq 0 ]; then
    echo -e "${GREEN}All checks passed.${NC}"
    exit 0
else
    echo -e "${RED}${FAILURES} check(s) failed.${NC}"
    exit 1
fi
