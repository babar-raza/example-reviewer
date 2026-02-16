# Pre-Run State for Phase 0 Empirical Investigation

## Date/Time
2026-02-12

## Git State
- **Current Commit**: `15abc5142fba7efd35edf63b7020d56ca02b2957`
- **Branch**: `main`
- **Recent Commits**:
  - 15abc51: config: update family configurations and align test suites
  - e1ff9c3: feat(pipeline): orchestrator improvements, bug fixes, and service enhancements
  - 0d74e98: feat(fixes): enhanced deterministic fixes and intelligent fixture resolver
  - 2f01446: feat(llm): migrate to OpenAI-compatible provider with model routing
  - 3e8bbb3: feat(catalog): DLL reflection-based API catalog with enriched metadata

## Modified Files (Staged/Unstaged)
- config/families/words.json
- config/global.json
- docs/local-telemetry-api.md
- src/cli/main.py
- src/core/config.py
- src/core/database.py
- src/mcp_tools/tools.py
- src/pipeline/orchestrator.py

## BarCode Content Roots
From config/families/barcode.json:
1. `D:/onedrive/Documents/GitHub/aspose.net/content/blog.aspose.net/barcode`
2. `D:/onedrive/Documents/GitHub/aspose.net/content/docs.aspose.net/barcode/en`
3. `D:/onedrive/Documents/GitHub/aspose.net/content/kb.aspose.net/barcode/en`

## Configuration
- Markdown writes: ENABLED (allow_markdown_write: true in global.json)
- LLM Provider: openai
- LLM Model: qwen2.5-coder:7b (local), gpt-oss (final review)
- Final review enabled: true
- Only review LLM fixed: true

## Pipeline Command
```bash
.venv/Scripts/python.exe -m src.cli.main run \
  --family barcode \
  --allow-md-write \
  --max-examples 0
```

## Expected Outcomes
- Discovery: ~199 examples (based on previous runs)
- Compilation attempts: Will vary based on fixes needed
- Runtime attempts: Will vary
- Markdown edits: Should write to filesystem this time
