#!/bin/bash
# Rollback script for LLM migration
# Reverts configuration changes to use Ollama instead of custom endpoint

set -e

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                     LLM Migration Rollback Script                            ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "This will revert your LLM configuration back to Ollama."
echo ""

# Check if we're in the right directory
if [ ! -f "config/global.json" ]; then
    echo "Error: config/global.json not found. Are you in the project root?"
    exit 1
fi

# Confirm with user
read -p "Are you sure you want to rollback? [y/N]: " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled"
    exit 0
fi

echo ""
echo "Starting rollback..."
echo ""

# Backup current config
BACKUP_DIR="backups/llm_migration_rollback_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "1. Backing up current configuration to $BACKUP_DIR..."
cp config/global.json "$BACKUP_DIR/global.json"
if [ -f "config/families/zip.json" ]; then
    cp config/families/zip.json "$BACKUP_DIR/zip.json"
fi
if [ -f "config/families/words.json" ]; then
    cp config/families/words.json "$BACKUP_DIR/words.json"
fi
echo "   ✓ Backup complete"
echo ""

# Revert global.json
echo "2. Reverting config/global.json to Ollama configuration..."

# Use jq if available, otherwise use sed
if command -v jq &> /dev/null; then
    # Update using jq
    jq '.llm.provider = "ollama" |
        .llm.model = "qwen2.5-coder:7b" |
        .llm.base_url = "http://localhost:11434/v1" |
        .llm.api_key_env_var = "OPENAI_API_KEY" |
        .final_review.provider = "ollama" |
        .final_review.model = "qwen2.5-coder:7b" |
        .model_routing.model_tiers.small = "qwen2.5-coder:1.5b" |
        .model_routing.model_tiers.medium = "qwen2.5-coder:7b" |
        .model_routing.model_tiers.large = "qwen2.5-coder:32b"' \
        config/global.json > config/global.json.tmp && mv config/global.json.tmp config/global.json

    echo "   ✓ Reverted using jq"
else
    # Fallback: use sed (less robust but works)
    sed -i.bak 's/"provider": "openai"/"provider": "ollama"/g' config/global.json
    sed -i.bak 's/"model": "gpt-oss"/"model": "qwen2.5-coder:7b"/g' config/global.json
    sed -i.bak 's|"base_url": "https://llm.professionalize.com/v1"|"base_url": "http://localhost:11434/v1"|g' config/global.json
    sed -i.bak 's/"api_key_env_var": "litellm_key"/"api_key_env_var": "OPENAI_API_KEY"/g' config/global.json

    echo "   ✓ Reverted using sed"
    echo "   ⚠ Note: Manual verification recommended (jq not available)"
fi
echo ""

# Clear environment variables
echo "3. Clearing LLM_* environment variables..."

if [ -n "$SHELL_RC" ]; then
    SHELL_RC=""
    if [ -n "$BASH_VERSION" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="$HOME/.zshrc"
    fi

    if [ -n "$SHELL_RC" ] && [ -f "$SHELL_RC" ]; then
        # Remove LLM configuration from shell RC
        if grep -q "LLM Configuration for example-reviewer" "$SHELL_RC" 2>/dev/null; then
            sed -i.bak '/# LLM Configuration for example-reviewer/,/^$/d' "$SHELL_RC"
            echo "   ✓ Removed LLM configuration from $SHELL_RC"
        else
            echo "   - No LLM configuration found in $SHELL_RC"
        fi
    fi
fi

# Unset for current session
unset LLM_PROVIDER
unset LLM_MODEL
unset LLM_BASE_URL
unset LLM_API_KEY_ENV_VAR

echo "   ✓ Environment variables cleared"
echo ""

# Git status
echo "4. Checking git status..."
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "   Files modified:"
    git status --short config/
    echo ""
    echo "   To commit the rollback:"
    echo "     git add config/"
    echo "     git commit -m \"chore: rollback LLM migration to Ollama\""
else
    echo "   Not a git repository (skipping)"
fi
echo ""

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                           Rollback Complete!                                 ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration has been reverted to use Ollama."
echo ""
echo "Next steps:"
echo "  1. Restart your terminal (to apply environment variable changes)"
echo "  2. Verify: python test_llm_migration.py"
echo "  3. Test: python -m src.cli.main run --family zip --max-examples 1"
echo ""
echo "Backup saved to: $BACKUP_DIR"
echo ""
