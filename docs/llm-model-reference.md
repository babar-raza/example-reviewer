# LLM Model Reference

**Last Updated**: 2026-02-11
**Discovery Run**: Initial migration from Ollama to OpenAI-compatible endpoint

## Provider Configuration

### Primary: Custom OpenAI-Compatible Endpoint
- **Base URL**: `https://llm.professionalize.com/v1`
- **Auth**: Bearer token from env var `litellm_key`
- **Purpose**: Primary LLM provider for all code fixes
- **Available Models**: 6 total (4 usable, 2 specialized)

### Fallback: Ollama Local
- **Base URL**: `http://localhost:11434/v1`
- **Auth**: None (placeholder "ollama")
- **Purpose**: Fallback when remote endpoint unavailable or times out
- **Available Models**: 34+ models (10+ excellent for coding)

## Discovery Results

### Custom Endpoint Models (llm.professionalize.com)

| Model ID | Actual Model | Parameters | Type | Status | Notes |
|----------|--------------|------------|------|--------|-------|
| `recommended` | gpt-oss-120b | 120B | Reasoning | ✅ Working | Alias to gpt-oss, best general model |
| `gpt-oss` | gpt-oss-120b | 120B | Reasoning | ✅ Working | Open source GPT variant, reasoning-capable |
| `experimental` | Unknown | Unknown | General | ⚠️ Unstable | Not recommended for production |
| `qwen3-next` | N/A | N/A | Code | ❌ Error | Connection error, not available |
| `qwen3-embedding-8b` | qwen3-embedding-8b | 8B | Embedding | ⚠️ Specialized | Not for chat completions |
| `Qwen2.5-VL-7B` | Qwen2.5-VL-7B | 7B | Vision-Language | ⚠️ Specialized | For image+text, not pure code |

**Working Model for Code**: `gpt-oss` or `recommended` → **gpt-oss-120b (120B parameters)**
- Reasoning-capable (has `reasoning_content` field in responses)
- Suitable for complex code fixes and semantic understanding
- Single model serves all complexity tiers

### Ollama Local Models (localhost:11434)

**Top Coding Models** (ordered by capability):

| Model ID | Parameters | Type | Best For | Notes |
|----------|------------|------|----------|-------|
| `deepseek-r1:32b` | 32B | Reasoning | Complex errors, architecture | Latest reasoning model, excellent for hard problems |
| `qwen3-coder-next:latest` | Unknown (latest) | Code | Fast coding tasks | Newest Qwen coder, very fast |
| `deepseek-coder-v2:16b` | 16B | Code | Balanced code fixes | Excellent code understanding |
| `phi4:14b` | 14B | General | Mixed tasks | Fast, capable, good fallback |
| `devstral:latest` | Unknown | Code | Developer tasks | Mistral's developer-focused model |
| `qwen2.5-coder:7b` | 7B | Code | Simple fixes | Current model, proven reliable |
| `qwen3:14b` | 14B | General | Balanced tasks | Newer Qwen, good general model |
| `ministral-3:latest` | Unknown | General | Fast inference | Compact Mistral variant |

**Additional Available Models**: 26+ more models including llama3.3, gemma2/3, codellama, etc.

## Recommended Model Tier Configuration

### Configuration Strategy: Primary Remote + Tiered Fallback

This configuration uses the powerful 120B remote model as primary for all tiers, with intelligent Ollama fallbacks optimized by complexity.

### Small Tier (Simple Errors)
**Primary**: `gpt-oss` (remote, 120B)
**Fallback**: `qwen3-coder-next:latest` (Ollama, fast)

**Use cases**:
- Missing using directives (CS0246)
- Undefined variables (CS0103)
- Simple namespace errors (CS0260)
- Type not found in namespace (CS0234 - namespace only)

**Why this tier**:
- Remote model handles these trivially
- Fallback is fastest local model for quick resolution
- ~70% of errors fall in this category

### Medium Tier (Moderate Complexity)
**Primary**: `gpt-oss` (remote, 120B)
**Fallback**: `deepseek-coder-v2:16b` (Ollama, 16B)

**Use cases**:
- Type mismatches (CS1503)
- Missing arguments (CS7036)
- Member not found (CS0117)
- Constructor signature errors (CS0534)
- Simple runtime errors (missing files, null refs)

**Why this tier**:
- Remote model provides excellent fixes
- Fallback is specialized coder model with great understanding
- ~25% of errors fall in this category

### Large Tier (Complex Errors)
**Primary**: `gpt-oss` (remote, 120B)
**Fallback**: `deepseek-r1:32b` (Ollama, 32B reasoning)

**Use cases**:
- Complex namespace errors (CS0234 with multiple missing types)
- Multi-error scenarios (cascading failures)
- Complex runtime errors (logic bugs, architectural issues)
- Semantic refactoring needs

**Why this tier**:
- Remote 120B model's reasoning capabilities shine here
- Fallback is largest local reasoning model
- ~5% of errors fall in this category

### Final Review Model
**Primary**: `gpt-oss` (remote, 120B)
**Fallback**: `qwen2.5-coder:7b` (Ollama, proven reliable)
**Timeout**: 60 seconds (stricter than regular fixes)

**Purpose**:
- Review generated code for correctness before marking as verified
- Catch any remaining issues not caught by compilation/runtime
- Final quality gate

**Why these models**:
- Remote 120B provides thorough review with reasoning
- Fallback is proven model from current production config
- Tighter timeout prevents review phase from blocking pipeline

## Alternative Configuration: Tiered by Cost/Speed

If the remote endpoint has usage limits or cost concerns, this configuration optimizes by using local models for simple tasks and reserving the remote model for complex problems.

### Small Tier
**Primary**: `qwen3-coder-next:latest` (Ollama, fast)
**Fallback**: `gpt-oss` (remote, 120B)

### Medium Tier
**Primary**: `deepseek-coder-v2:16b` (Ollama, 16B)
**Fallback**: `gpt-oss` (remote, 120B)

### Large Tier
**Primary**: `gpt-oss` (remote, 120B)
**Fallback**: `deepseek-r1:32b` (Ollama, 32B)

**Trade-offs**:
- ✅ Minimizes remote API calls and costs
- ✅ Fast local inference for majority of errors
- ❌ May have lower accuracy for edge cases in small/medium tiers
- ❌ More complex fallback logic (provider switches mid-tier)

## Model Selection Logic (Current Pipeline)

1. **Error Classification**: Orchestrator extracts error code (e.g., CS0246, CS1503)
2. **Complexity Scoring**: Error classified as simple/moderate/complex based on error code
3. **Tier Selection**: Routes to small/medium/large tier based on classification
4. **Primary Attempt**: Calls remote endpoint (`gpt-oss`) with standard timeout (120s)
5. **Fallback on Failure**: If remote fails (timeout/connection/API error), falls back to Ollama model for that tier
6. **Response Validation**: Ensures response contains code, not just explanation
7. **Retry Logic**: Up to 5 retries with exponential backoff (configurable per tier)

## Model Performance Characteristics

### gpt-oss-120b (Remote)
**Strengths**:
- Massive parameter count (120B) provides excellent understanding
- Reasoning-capable (includes reasoning traces in responses)
- Handles complex semantic and architectural fixes
- Single model simplifies configuration

**Limitations**:
- Network latency (remote calls)
- Potential rate limiting
- Depends on internet connectivity
- Unknown cost per token (monitor usage)

**Estimated Performance**:
- Simple errors: 2-5 seconds
- Medium errors: 5-15 seconds
- Complex errors: 15-60 seconds
- May timeout on very complex scenarios (120s limit)

### Ollama Models (Local)
**Strengths**:
- Zero latency overhead (localhost)
- No rate limiting
- No cost per token
- Proven reliability in current production

**Limitations**:
- Smaller models may struggle with complex reasoning
- Requires local compute resources
- Models must be pulled/updated manually

**Estimated Performance** (on typical hardware):
- qwen3-coder-next: 1-3 seconds (simple)
- deepseek-coder-v2:16b: 3-8 seconds (medium)
- deepseek-r1:32b: 8-30 seconds (complex)

## Configuration Files

### Global Configuration (`config/global.json`)
```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-oss",
    "base_url": "https://llm.professionalize.com/v1",
    "temperature": 0.2,
    "max_retries": 5,
    "timeout_seconds": 120,
    "api_key_env_var": "litellm_key",
    "deterministic_mode": false,
    "enforce_timeout": true
  },
  "final_review": {
    "provider": "openai",
    "model": "gpt-oss",
    "base_url": "https://llm.professionalize.com/v1",
    "api_key_env_var": "litellm_key",
    "timeout_seconds": 60
  },
  "model_routing": {
    "enabled": true,
    "model_tiers": {
      "small": "gpt-oss",
      "medium": "gpt-oss",
      "large": "gpt-oss"
    },
    "fallback_enabled": true
  }
}
```

### Fallback Configuration (Ollama)
The fallback configuration is currently handled by the existing Ollama config in `global.json`. When the primary provider fails, the system falls back to:

```json
{
  "llm": {
    "provider": "ollama",
    "base_url": "http://localhost:11434/v1",
    "model_tiers": {
      "small": "qwen3-coder-next:latest",
      "medium": "deepseek-coder-v2:16b",
      "large": "deepseek-r1:32b"
    }
  }
}
```

**Note**: If the current codebase doesn't support separate fallback model tiers, all tiers will fall back to the same Ollama model specified in the main config. This may require code enhancement in `src/services/llm_service.py`.

## Monitoring and Optimization

### Metrics to Track
1. **Provider distribution**: % calls to remote vs Ollama
2. **Latency by tier**: Average response time per tier
3. **Fallback rate**: How often fallback is triggered
4. **Success rate by model**: Verification rate improvement per tier
5. **Token usage**: Cost tracking for remote endpoint
6. **Error types**: Which error codes benefit most from 120B model

### Telemetry Queries
```sql
-- View provider usage distribution
SELECT provider, model, COUNT(*) as calls, AVG(latency_ms) as avg_latency
FROM llm_telemetry
WHERE run_id = (SELECT run_id FROM telemetry_runs ORDER BY timestamp DESC LIMIT 1)
GROUP BY provider, model;

-- View fallback frequency
SELECT tier, COUNT(*) as total_calls,
       SUM(CASE WHEN provider = 'ollama' THEN 1 ELSE 0 END) as fallback_calls,
       ROUND(100.0 * SUM(CASE WHEN provider = 'ollama' THEN 1 ELSE 0 END) / COUNT(*), 2) as fallback_rate
FROM llm_telemetry
WHERE run_id = (SELECT run_id FROM telemetry_runs ORDER BY timestamp DESC LIMIT 1)
GROUP BY tier;
```

### Optimization Recommendations

**After 1 week of monitoring**:
1. Analyze fallback rate - if >20%, investigate remote endpoint reliability
2. Compare verification rates to baseline (current: 97.7% for ZIP)
3. Check if 120B model is overkill for small tier (latency vs accuracy trade-off)
4. Consider switching to "Alternative Configuration" if cost is concern

**After 1 month of monitoring**:
1. Fine-tune tier assignments based on actual performance
2. Update routing rules to better classify error complexity
3. Consider adjusting timeouts per tier based on observed latency
4. Evaluate if newer models are available (re-run discovery)

## Version History

### v1.0 (2026-02-11)
- Initial discovery and migration from Ollama-only to hybrid configuration
- Identified gpt-oss-120b as primary remote model
- Configured 3-tier fallback system with Ollama
- Baseline: ZIP 97.7% verified, Words 93.2% verified

---

## Quick Reference Card

**Need to add a new model?**
1. Run discovery: `curl https://llm.professionalize.com/v1/models -H "Authorization: Bearer $litellm_key"`
2. Test model: Create test completion request
3. Update this document with findings
4. Update `config/global.json` model_tiers
5. Run regression test to verify

**Remote endpoint not responding?**
- Check: `echo $litellm_key` (should show key)
- Test: `curl https://llm.professionalize.com/v1/models -H "Authorization: Bearer $litellm_key"`
- Fallback should activate automatically if configured correctly
- Check logs: `grep -i "fallback" logs/verify_*.log`

**Want to switch to local-only?**
1. Edit `config/global.json`: Set `provider: "ollama"`, `base_url: "http://localhost:11434/v1"`
2. No need to change model names (Ollama has same model IDs)
3. Remove `api_key_env_var` or set to placeholder

**Want to test new remote endpoint?**
1. Update `base_url` in config
2. Update `api_key_env_var` to new env var name
3. Set new environment variable
4. Run connectivity test: `curl $NEW_BASE_URL/models -H "Authorization: Bearer $NEW_KEY"`
