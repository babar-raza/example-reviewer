# src/services/ - Pipeline Services

All specialized services used by the pipeline orchestrator.

## Core Services

| Service | Purpose |
|---------|---------|
| `discovery_service.py` | Discovers C# code examples from markdown files |
| `compilation_service.py` | Compiles C# code via `dotnet build` |
| `runtime_service.py` | Executes compiled C# programs and captures output |
| `markdown_service.py` | Updates markdown files with verified code |
| `llm_service.py` | LLM integration (OpenAI-compatible API) for code fixing |

## Fix Services

| Service | Purpose |
|---------|---------|
| `semantic_microfixes.py` | Deterministic code fixes (using directives, stream disposal, etc.) |
| `semantic_microfixes_zip.py` | ZIP-family-specific deterministic fixes |
| `learned_patterns_service.py` | Applies auto-learned fix patterns from past runs |
| `context_harness_service.py` | Wraps partial code snippets in compilable harnesses |
| `snippet_wrapper_service.py` | Wraps code in Main() method for compilation |

## Support Services

| Service | Purpose |
|---------|---------|
| `api_catalog_service.py` | API catalog access (types, namespaces, constructors from assembly reflection) |
| `fixture_resolver_service.py` | Self-healing test data resolution (5-tier: existing, registry, reverse, extension, generate) |
| `test_data_generator.py` | Generates test data files (.docx, .pdf, .png, etc.) |
| `backfill_service.py` | Fetches code from GitHub gists |
| `drift_detector.py` | Embedding-based semantic drift detection |
| `semantic_signature_service.py` | Structural signature validation for drift prevention |
| `model_discovery_service.py` | Discovers available LLM models |
| `ollama_manager.py` | Ollama LLM server management |
| `vector_db_service.py` | ChromaDB vector database for semantic search |
| `gist_publisher.py` | Publishes code examples to GitHub gists |
| `telemetry_service.py` | Telemetry event emission helpers |
| `llm_contracts.py` | LLM response validation contracts |
| `resource_detection_service.py` | Detects required resources in code examples |
| `example_substitution_service.py` | Substitutes placeholder values in code |
