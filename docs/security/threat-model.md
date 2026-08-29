# Threat Model — example-reviewer

Taskcard: `TC-L1-01`. Produced 2026-08-29 as the required entry gate for the L1 (Execution Security) taskcard series (`TC-L1-02` through `TC-L1-06`) and Epic 1 (Authorization Kernel). Cites file:line evidence current as of commit `2c837e2661ba681cd3a357aa442a80d1dd4ca3b1`; re-verify citations before relying on them if HEAD has since moved.

## Actors

| Actor | Trust assumed today | Trust that should apply |
|---|---|---|
| End customer / blog reader | N/A — passive consumer of published examples | N/A |
| Pipeline operator | Fully trusted (runs CLI/HTTP server) | Fully trusted, but should not need to be the only line of defense |
| External LLM provider (Anthropic/OpenAI/Ollama) | Fully trusted — its output is compiled/executed like any other code | Untrusted code source; output must pass through the same isolation as any other code |
| Malicious/compromised markdown or gist contributor | Implicitly trusted — the pipeline's whole purpose is to extract and execute C# from a content tree this repo does not itself access-control | Semi-trusted input; content should be treated as untrusted code awaiting compilation |
| Malicious or compromised LLM response | Fully trusted — no distinction made between human-authored and LLM-generated fixes before execution | Untrusted; prompt injection via markdown content or reflected compiler-error text is a live concern |
| Unauthenticated network client | Fully trusted whenever `EXAMPLE_REVIEWER_API_KEY` is unset (the shipped `docker-compose.yml`'s actual state) | Untrusted by default |

## Attack surfaces

### 1. HTTP (`src/http_server.py`)
Generic `/api/v1/tools/{tool_name}` dispatch forwards arbitrary JSON bodies into `MCPServer.call_tool()`. Authentication is optional — enforced only when `EXAMPLE_REVIEWER_API_KEY` is set (`auth_middleware`, lines 84-101; empty-key check returns early, skipping the check entirely). `CORS_ORIGINS` defaults to `*`. No rate limiting or request-size limit exists in any route handler.

### 2. Subprocess (`src/services/compilation_service.py::_run_build` line 548, `src/services/runtime_service.py::_build_and_run` line 451)
Every `dotnet restore`/`build`/`run` invocation inherits the full host/container environment and runs against markdown-sourced content plus LLM-applied fixes, with zero sandboxing: no network restriction, no filesystem containment beyond `cwd=work_dir` (which does not prevent absolute-path access), no resource limits.

### 3. LLM
Prompt injection is possible via markdown content itself, or via compiler error text that gets reflected back into fix-generation prompts. LLM-returned code is compiled and executed with exactly the same lack of isolation as human-authored code — there is no additional scrutiny applied to model output before it reaches the subprocess boundary above.

### 4. Git / telemetry
`gitpython`-based commit automation (scoped per-file staging, no `git push` found anywhere in the codebase per this investigation's static analysis) and a telemetry POST target (`localhost:8765` in this investigation's test environment; confirm the production target before treating this as low-risk in a different deployment). Both are outward-writing channels capable of exfiltration or unwanted publication if compromised upstream of them.

## Attack trees

### Tree 1 — Malicious code reaches host execution with attacker-controlled network/filesystem access
```
GOAL: Execute arbitrary code with host privileges, network reach, and filesystem access
├── 1. Reach a compile/execute call site
│   ├── 1a. Unauthenticated HTTP request to a tool that triggers compilation (surface 1)
│   ├── 1b. Malicious content merged into a content root the pipeline scans (surface 2, via surface 4's trust assumption)
│   └── 1c. LLM prompt-injected into returning adversarial "fix" code (surface 3)
├── 2. Code reaches `dotnet build`/`run` with full env, no sandbox (surface 2)
└── 3. GOAL ACHIEVED — no isolation boundary exists at any of the three entry paths above today
```
**Mitigation dependency**: closing path 1a requires the Authorization Kernel (Epic 1, this session); closing step 2 for ALL three paths requires the sandbox (`TC-L1-02/03/04`) — defense in depth requires both, since fixing only the entry paths still leaves surface 2 exploitable by anyone who reaches it through the remaining unfixed path.

### Tree 2 — Attacker causes the pipeline to auto-commit/auto-push malicious code
```
GOAL: Get attacker-controlled code merged into the customer-facing content repo
├── 1. Reach the commit tool with attacker influence
│   ├── 1a. Unauthenticated HTTP call to the commit tool (surface 1, combined with the MCP tool's
│   │       hardcoded allow_commit=True bypassing the family auto_commit opt-out)
│   └── 1b. A compromised/malicious "verified" example reaches FINAL_REVIEW_PASSED status via
│           the dead state machine (no legality check on status transitions today)
├── 2. Commit phase stages and commits the file (scoped per-file staging is real, but doesn't
│      validate WHAT was verified, only WHICH files changed)
└── 3. GOAL ACHIEVED for path 1a today; path 1b requires ALSO compromising the (currently
       unenforced) verification pipeline, so it's a secondary, higher-effort path
```
**Mitigation dependency**: closing path 1a requires `TC-EPIC1-03` (commit gate consolidation); closing path 1b requires `TC-EPIC2-01/02` (State Authority) since it depends on the status-transition legality check that doesn't exist today. No `git push` exists in the codebase today, which caps this tree's blast radius at "local repo commit," not "published to a remote" — a meaningful existing mitigation, not a gap.

## Risk ranking (likelihood × impact)

| Surface / scenario | Likelihood | Impact | Priority | Justification |
|---|---|---|---|---|
| Subprocess isolation (surface 2) | High (zero controls today, trivially reachable via surface 1 or 2) | Critical (full host RCE) | **Critical** — justifies `TC-L1-02/03/04` ahead of all L3/L4 packaging/CI work |
| HTTP auth (surface 1) | High (fails open by default, shipped config doesn't set a key) | Critical (unlocks every other surface) | **Critical** — justifies Epic 1 (Authorization Kernel) landing early |
| Commit/state integrity (surface 4 + state machine) | Medium (requires reaching the commit tool or forging a status) | High (supply-chain-style compromise of published content) | **High** — justifies Epic 2 (State Authority) |
| LLM prompt injection (surface 3) | Medium (requires crafting adversarial content or error text) | Medium (bounded by surface 2's isolation once that lands — same blast radius as any other code source) | **Medium** — no dedicated mitigation card exists yet beyond treating LLM output as untrusted input to the sandbox |
| Telemetry/CORS/rate-limiting gaps | Low-Medium | Low-Medium (availability/cost, not RCE) | **Medium/Low** — addressed incidentally by Epic 1's HTTP-boundary consolidation (`TC-EPIC1-06`) |

This ranking is why `TC-L1-02` through `TC-L1-06` (sandboxing) and Epic 1 (authorization) are prioritized ahead of the L3/L4 packaging and CI taskcards in the governing repair plan's dependency graph — packaging/CI gaps are real but bounded to build-time/developer-experience risk, not runtime RCE.

## Out of scope for this pass

- Supply-chain attacks on the NuGet packages themselves beyond version pinning (`TC-EPIC3-01`) — a compromised-but-pinned package is not addressed by pinning alone; full supply-chain verification (checksums, signing) is not in scope for this threat model or the current repair plan.
- Insider threat from repository committers with direct write access to `main`.
- Physical/infrastructure security of the machines running CI or production deployments.
- A formal STRIDE/PASTA methodology — this document uses actor/attack-tree/risk-ranking structure without mandating a specific named framework, per this taskcard's own explicit non-goal.
- A live penetration test or red-team exercise against a running instance.

## References

- `reports/investigation/20260829_124758_production_readiness/SECURITY_THREAT_MODEL.md` — the investigation's own threat model, produced during the original audit; this document is the permanent, repo-committed counterpart cited going forward by `TC-L1-02` and Epic 1.
- `reports/investigation/20260829_124758_production_readiness/FINDINGS_REGISTER.md` — F-001, F-009, F-010, F-012, F-013, F-040 are the findings this threat model's risk ranking is built from.
- `reports/investigation/20260829_124758_production_readiness/evidence/manifest.json`'s `explicitly_not_run` section — records that this investigation deliberately never executed `dotnet build`/`run` specifically because this threat model did not yet exist.
