## LLM-Consumable Workflow Spec (Plain Points)

### Entities and Inputs

* **family**: Product family identifier (e.g., `Aspose.ZIP`) used to resolve configs, DLLs, repos, and sample paths.
* **target scope**:

  * A **directory path** to scan, OR
  * A **family** that maps to one or more content roots.
* **content files**: Markdown files (`*.md`) inside the target scope.
* **example source types**:

  * **Inline fenced code blocks** inside `.md`
  * **Embedded Gist snippets** referenced inside `.md`
* **product DLL**: Latest version of the family’s product DLL used for compilation verification.
* **test data**:

  * Local path: `test-data/{family}/...`
  * If missing: fetch from a configured GitHub “Example repo” source for that family.

---

## Workflow: End-to-End Pipeline

### Phase A — Discovery and Extraction

1. Scan all `.md` files in the target scope.
2. For each `.md`, extract all code examples:

   * Inline fenced code blocks.
   * Gist-based examples (resolve gist metadata needed to fetch the code).
3. Normalize each extracted example into a canonical record:

   * `family`, `file_path`, `example_id` (stable hash), `source_type` (inline/gist), `language`, `original_code`, `location_in_file` (block index / anchors), and any gist identifiers.

---

### Phase B — Compilation Verification Loop

4. For each extracted example, compile/validate it against the **latest product DLL**.

5. If compilation fails:

   * Prepare an LLM “fix request” payload containing:

     * The **problematic code**
     * **compiler errors/logs**
     * Relevant **API references** for the family
     * Any required project scaffolding/context (namespaces, imports, framework target, etc.)
   * Send payload to LLM and request corrected code output only (plus minimal explanation if needed).

6. Re-compile the corrected code against the latest product DLL.

7. Repeat the “LLM fix → compile” loop until either:

   * Compilation succeeds, OR
   * A configured retry limit is reached (and mark as failed).

8. When compilation succeeds:

   * Store a mapping in the database:

     * `original_code` → `compilable_code`
   * Update example status to **COMPILABLE**.

---

### Phase C — Runtime Verification Loop

9. Execute the compilable code against an appropriate runtime scenario using samples from:

   * `test-data/{family}` if present, otherwise download test data from the family’s configured Example repo.
10. If runtime data is missing locally:

* Fetch test data from GitHub using family config:

  * repo URL
  * data location/path inside repo
  * checkout/ref rules (branch/tag/commit)

11. Run the example; capture:

* stdout/stderr
* exception traces
* runtime logs
* environment info needed for reproducibility (OS, framework, DLL version, etc.)

12. If runtime fails:

* Ensure “existing examples for guidance” are available in a **vector database**:

  * If not present, backfill them from the family’s configured Example repo (example location/path).
* Prepare an LLM “runtime fix request” payload containing:

  * runtime-errored code
  * runtime logs/stack trace
  * relevant existing examples (retrieved from vector DB)
  * the execution scenario details (sample file used, parameters, steps)

13. Send payload to LLM for corrected code.
14. Re-run the corrected code with the **same runtime scenario**.
15. Repeat the “LLM fix → runtime test” loop until either:

* Runtime succeeds, OR
* A configured retry limit is reached (and mark as failed).

16. When runtime succeeds:

* Store verified result in database:

  * `verified_code`
  * status **VERIFIED**
  * evidence references (logs, sample id, dll version)

---

### Phase D — Markdown Update (Inline or Gist)

17. Replace the original code in the `.md` with the **verified code**, preserving the authoring mode:

* If original was **inline** → replace inline fenced block with verified code (proper fences, language id, formatting).
* If original was **gist-based**:

  * Upload verified code to the designated gist account/repo (configured in app config).
  * Obtain new gist metadata: `owner`, `gist_id/hash`, `filename`.
  * Replace gist reference in `.md` with the new gist metadata.

---

### Phase E — Final LLM Review (Content Relevance + Correct Injection)

18. Send the full updated `.md` content to an LLM for final review:

* Confirm the code is relevant to the topic.
* Confirm correct injection (inline fences or gist embed correctness).
* Confirm formatting and minimal editorial issues around the snippet.

19. If final review fails:

* Apply required corrections (configurable: auto-apply vs manual gate).
* Re-run the final review if configured.

---

### Phase F — Persist, Telemetry, Commit

20. On success:

* Update database final status and store all finalized artifacts.
* Log full run details in **local-telemetry** and internal telemetry.
* Commit changes back to the content repo:

  * Only include **touched files**.
  * Use configurable commit message + description template.
  * Record commit hash in telemetry/database.

---

## Cross-Cutting Requirements (System-Level)

### Configurability

* All operations MUST be configurable via config files and/or CLI options:

  * scanning scope, family mapping, retry limits, model selection, gist settings, repo settings, commit templates, runtime runners, etc.

### CLI / Cmdlets

* Provide cmdlets/commands for each operation.
* Every major phase must be independently executable, e.g.:

  * `scan`
  * `extract`
  * `compile-verify`
  * `compile-fix`
  * `runtime-verify`
  * `runtime-fix`
  * `md-update`
  * `final-review`
  * `commit`
  * `backfill`

### Independent Execution

* Each operation should run standalone using shared persisted state (DB + artifacts), not requiring the full pipeline every time.

### Persistence and Databases

* Maintain persistent, well-organized databases for:

  * extracted examples and metadata
  * original→compilable mapping
  * verified code outputs
  * execution evidence (logs pointers)
  * vector database for “existing examples”
  * run history and status transitions

### Backfill for LLM Consumption

* If any LLM-required context is missing (API refs, existing examples, samples), system must support backfill flows to populate it automatically.

### Telemetry

* Maintain:

  * internal telemetry (pipeline phase timings, retries, failures, resource usage)
  * local-telemetry (durable run logs + artifacts, queryable)

### Layered Architecture + Model Switching

* System must be layered (clear separation of concerns).
* LLM layer must support switching to any OpenAI-supported model via configuration.

### Intelligent VRAM Usage

* System must auto-detect available VRAM and select execution strategy intelligently:

  * choose local GPU vs CPU where applicable
  * enforce configured limits (VRAM/RAM/CPU)
  * record resource decisions in telemetry

---

## Status Model (Suggested Plain States)

* `DISCOVERED` → extracted from `.md`
* `COMPILE_FAILED` / `COMPILABLE`
* `RUNTIME_FAILED` / `VERIFIED`
* `MD_UPDATED`
* `FINAL_REVIEW_PASSED`
* `COMMITTED`
* Terminal failure states should include reason + evidence references.
