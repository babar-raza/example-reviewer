#!/bin/bash
# Phase-2 Gate B Remediation Verification Script
# Run this to verify all fixes are working correctly

set -e

echo "========================================================================"
echo "Phase-2 Gate B Remediation - Verification Script"
echo "========================================================================"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
    echo "ERROR: No virtual environment found (.venv or venv)"
    echo "Please create one with: python -m venv .venv && source .venv/Scripts/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
if [ -d ".venv" ]; then
    echo "[1/6] Activating .venv virtual environment..."
    source .venv/Scripts/activate
elif [ -d "venv" ]; then
    echo "[1/6] Activating venv virtual environment..."
    source venv/Scripts/activate
fi

# Check Python syntax
echo "[2/6] Verifying Python syntax of modified files..."
python -m py_compile src/pipeline/orchestrator.py || { echo "ERROR: orchestrator.py has syntax errors"; exit 1; }
python -m py_compile src/services/example_substitution_service.py || { echo "ERROR: example_substitution_service.py has syntax errors"; exit 1; }
echo "  ✓ Syntax check passed"
echo ""

# Check backfill data exists
echo "[3/6] Verifying backfill data exists..."
if [ ! -f "artifacts/backfill/zip/examples-index.json" ]; then
    echo "  WARNING: examples-index.json not found. Run: python tools/provision_test_data_zip.py --family zip"
else
    EXAMPLE_COUNT=$(cat artifacts/backfill/zip/examples-index.json | python -c "import sys, json; print(json.load(sys.stdin)['total_examples'])")
    echo "  ✓ Found $EXAMPLE_COUNT examples in index"
fi
echo ""

# Run single test measurement
echo "[4/6] Running single test measurement (this will take 5-10 minutes)..."
python tools/run_e2e_zip.py \
    --family zip \
    --seed 12345 \
    --runs 1 \
    --skip-provision \
    --safe-workspace \
    --use-workspace-copy \
    --no-dry-run \
    --verbose 2>&1 | tee /tmp/gate_b_test_run.log

echo ""
echo "[5/6] Analyzing results..."

# Find the latest e2e summary
LATEST_SUMMARY=$(find reports/e2e -name "e2e_summary.json" -type f | sort -r | head -1)

if [ -z "$LATEST_SUMMARY" ]; then
    echo "  ERROR: No e2e_summary.json found"
    exit 1
fi

echo "  Found summary: $LATEST_SUMMARY"
echo ""

# Extract key metrics
ELIGIBLE_VERIFIED_RATE=$(cat "$LATEST_SUMMARY" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('phase2_metrics', {}).get('eligible_verified_rate', 0))" 2>/dev/null || echo "0")
INFRA_BLOCKED=$(cat "$LATEST_SUMMARY" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('phase2_metrics', {}).get('infra_blocked_count', 0))" 2>/dev/null || echo "0")
VERIFIED=$(cat "$LATEST_SUMMARY" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('phase2_metrics', {}).get('verified_count', 0))" 2>/dev/null || echo "0")

echo "[6/6] Verification Results:"
echo "  ────────────────────────────────────────"
echo "  eligible_verified_rate: $ELIGIBLE_VERIFIED_RATE%"
echo "  verified_count: $VERIFIED"
echo "  infra_blocked_count: $INFRA_BLOCKED"
echo ""

# Check infra_breakdown
echo "  Infra Breakdown:"
cat "$LATEST_SUMMARY" | python -c "
import sys, json
data = json.load(sys.stdin)
breakdown = data.get('phase2_metrics', {}).get('infra_breakdown', {})
total = sum(breakdown.values())
for key, val in breakdown.items():
    if val > 0:
        print(f'    - {key}: {val}')
print(f'  Total: {total}')
" 2>/dev/null || echo "    (Unable to parse breakdown)"

echo ""

# Check for fixes applied
echo "  Fixes Applied (check logs):"
echo "  ────────────────────────────────────────"
grep -c "Applied quick fixes" /tmp/gate_b_test_run.log && echo "  ✓ Quick fixes applied" || echo "  ✗ No quick fixes found"
grep -c "Substitution triggered" /tmp/gate_b_test_run.log && echo "  ✓ Substitutions triggered" || echo "  ✗ No substitutions found"
grep -c "Reclassifying.*as COMPILE_FAILED" /tmp/gate_b_test_run.log && echo "  ✓ Runtime reclassifications" || echo "  ✗ No reclassifications found"
echo ""

# Gate B result
if (( $(echo "$ELIGIBLE_VERIFIED_RATE >= 90.0" | bc -l) )); then
    echo "  ✅ GATE B: PASS (eligible_verified_rate >= 90%)"
else
    echo "  ❌ GATE B: FAIL (eligible_verified_rate < 90%)"
fi

echo ""
echo "========================================================================"
echo "Next Steps:"
echo "========================================================================"
echo "1. Review the test output above"
echo "2. If Gate B PASSED, run full 2-run measurement:"
echo "   python tools/run_e2e_zip.py --family zip --seed 12345 --runs 2 \\"
echo "     --skip-provision --safe-workspace --use-workspace-copy --no-dry-run --verbose"
echo "3. If determinism passes, run md-update:"
echo "   python -m src.cli.main --safe-workspace --deterministic --seed 12345 \\"
echo "     run --family zip --use-workspace-copy --allow-md-write --max-examples 50"
echo "4. Generate evidence reports"
echo "========================================================================"
