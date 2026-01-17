#!/bin/bash
# CD-04: Make Context Extraction Configurable
# All commands executed during implementation

# Create deliverables directory
mkdir -p "c:\Users\prora\OneDrive\Documents\GitHub\example-reviewer\reports\agents\agent-b\CD-04\run_20260117_000000\artifacts"

# Read existing files to understand current state
# (Read commands executed via tool - config.py, discovery_service.py, global.json, zip.json)

# Install dependencies
python -m pip install -r requirements.txt --user

# Run tests
"venv/Scripts/python.exe" tests/test_context_extraction_simple.py

# Verification - test output captured to artifacts/test_output.txt
