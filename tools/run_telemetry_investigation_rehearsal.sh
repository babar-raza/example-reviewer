#!/bin/bash
# Task C: Mini Rehearsal Script for Telemetry Investigation
#
# This script runs a mini rehearsal to test the telemetry API and strict validator
# DB wiring end-to-end.
#
# USAGE:
#   bash tools/run_telemetry_investigation_rehearsal.sh

set -e  # Exit on error

echo "========================================="
echo "Telemetry Investigation Mini Rehearsal"
echo "========================================="
echo ""

# Step 1: Run tests
echo "[Step 1] Running tests..."
python -m pytest -q
echo ""

# Step 2: Run pipeline with safe workspace
echo "[Step 2] Running pipeline with safe workspace..."
echo "Command: python -m src.cli.main run --family zip --config config/global_strict_context.json \\"
echo "  --safe-workspace --use-workspace-copy --no-dry-run --skip-llm-fixes --max-examples 5 --verbose"
echo ""

RUN_OUTPUT=$(python -m src.cli.main run --family zip --config config/global_strict_context.json \
  --safe-workspace --use-workspace-copy --no-dry-run --skip-llm-fixes --max-examples 5 --verbose 2>&1)

echo "$RUN_OUTPUT"
echo ""

# Extract RUN_ID from output
RUN_ID=$(echo "$RUN_OUTPUT" | grep -oP 'RUN_ID:\s*\K[a-f0-9]+' | head -1)
if [ -z "$RUN_ID" ]; then
    echo "[ERROR] Could not extract RUN_ID from pipeline output"
    exit 1
fi

echo "[INFO] Captured RUN_ID: $RUN_ID"
echo ""

# Extract DB_PATH from output
DB_PATH=$(echo "$RUN_OUTPUT" | grep -oP 'DB_PATH:\s*\K.+' | head -1)
if [ -z "$DB_PATH" ]; then
    echo "[WARN] Could not extract DB_PATH from pipeline output, will use auto-location"
    DB_PATH_ARG=""
else
    echo "[INFO] Captured DB_PATH: $DB_PATH"
    DB_PATH_ARG="--db-path \"$DB_PATH\""
fi
echo ""

# Step 3: Run strict validator
echo "[Step 3] Running strict context validator..."
if [ -n "$DB_PATH_ARG" ]; then
    python tools/validate_strict_context_mode.py --run-id "$RUN_ID" $DB_PATH_ARG \
      --output reports/telemetry_investigation/validation_report.json
else
    python tools/validate_strict_context_mode.py --run-id "$RUN_ID" \
      --output reports/telemetry_investigation/validation_report.json
fi
echo ""

# Step 4: Run telemetry verify (assuming telemetry API is running on localhost:8765)
echo "[Step 4] Running telemetry verify..."
TELEMETRY_URL="${TELEMETRY_URL:-http://localhost:8765}"
echo "Telemetry API URL: $TELEMETRY_URL"

python -m src.cli.main telemetry-verify --run-id "$RUN_ID" --telemetry-url "$TELEMETRY_URL" \
  > reports/telemetry_investigation/telemetry_verify_output.txt 2>&1 || {
    echo "[WARN] Telemetry verify failed or API not available"
    echo "Output saved to reports/telemetry_investigation/telemetry_verify_output.txt"
}
echo ""

# Step 5: Collect evidence
echo "[Step 5] Evidence collection complete"
echo "  - RUN_ID: $RUN_ID"
echo "  - DB_PATH: ${DB_PATH:-<auto-located>}"
echo "  - Validation report: reports/telemetry_investigation/validation_report.json"
echo "  - Telemetry verify output: reports/telemetry_investigation/telemetry_verify_output.txt"
echo ""

echo "========================================="
echo "Rehearsal Complete"
echo "========================================="
