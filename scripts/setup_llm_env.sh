#!/bin/bash
# Setup script for LLM environment variables
# This configures the example-reviewer to use the custom OpenAI-compatible endpoint

set -e

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                     LLM Environment Variable Setup                           ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Detect shell configuration file
if [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
    SHELL_NAME="bash"
elif [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
    SHELL_NAME="zsh"
else
    echo "Warning: Unknown shell. Please manually add environment variables."
    SHELL_RC=""
    SHELL_NAME="unknown"
fi

echo "Detected shell: $SHELL_NAME"
if [ -n "$SHELL_RC" ]; then
    echo "Configuration file: $SHELL_RC"
fi
echo ""

# Environment variables to set
ENV_VARS="
# LLM Configuration for example-reviewer (Custom OpenAI-compatible endpoint)
export LLM_API_KEY_ENV_VAR=litellm_key
export litellm_key=\"YOUR_API_KEY_HERE\"

# Optional: Override provider/model/url (config files have these by default)
# export LLM_PROVIDER=openai
# export LLM_MODEL=gpt-oss
# export LLM_BASE_URL=https://llm.professionalize.com/v1
"

# Check if API key is already set
if [ -n "$litellm_key" ]; then
    echo "✓ litellm_key is already set: ${litellm_key:0:15}...${litellm_key: -10}"
    echo ""
else
    echo "✗ litellm_key is NOT set"
    echo ""
fi

# Ask user what to do
echo "What would you like to do?"
echo ""
echo "  1) Add environment variables to $SHELL_RC (persistent across sessions)"
echo "  2) Set environment variables for current session only (temporary)"
echo "  3) Display environment variables to manually add"
echo "  4) Exit without changes"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        if [ -z "$SHELL_RC" ]; then
            echo "Error: Unknown shell, cannot auto-configure"
            exit 1
        fi

        echo ""
        echo "Adding environment variables to $SHELL_RC..."

        # Check if already configured
        if grep -q "LLM_API_KEY_ENV_VAR" "$SHELL_RC" 2>/dev/null; then
            echo "Warning: LLM configuration already exists in $SHELL_RC"
            read -p "Overwrite? [y/N]: " overwrite
            if [[ ! "$overwrite" =~ ^[Yy]$ ]]; then
                echo "Skipping..."
                exit 0
            fi
            # Remove old configuration
            sed -i.bak '/# LLM Configuration for example-reviewer/,/^$/d' "$SHELL_RC"
        fi

        # Append new configuration
        echo "$ENV_VARS" >> "$SHELL_RC"

        echo "✓ Environment variables added to $SHELL_RC"
        echo ""
        echo "IMPORTANT: Update YOUR_API_KEY_HERE with your actual API key!"
        echo "Edit: $SHELL_RC"
        echo ""
        echo "To apply changes:"
        echo "  source $SHELL_RC"
        ;;

    2)
        echo ""
        echo "Setting environment variables for current session..."

        # Export for current session
        export LLM_API_KEY_ENV_VAR=litellm_key

        # Check if API key is set
        if [ -z "$litellm_key" ]; then
            read -p "Enter your litellm API key: " api_key
            export litellm_key="$api_key"
        fi

        echo "✓ Environment variables set for current session"
        echo ""
        echo "Current values:"
        echo "  LLM_API_KEY_ENV_VAR = $LLM_API_KEY_ENV_VAR"
        echo "  litellm_key = ${litellm_key:0:15}...${litellm_key: -10}"
        echo ""
        echo "Note: These will be lost when you close this terminal"
        ;;

    3)
        echo ""
        echo "Copy these lines to your shell configuration file:"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "$ENV_VARS"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "Then run: source ~/.bashrc (or ~/.zshrc)"
        ;;

    4)
        echo "Exiting without changes"
        exit 0
        ;;

    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✓ Setup complete!"
echo ""
echo "To verify the configuration works:"
echo "  python test_llm_migration.py"
