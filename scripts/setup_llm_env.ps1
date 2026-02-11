# Setup script for LLM environment variables (Windows PowerShell)
# This configures the example-reviewer to use the custom OpenAI-compatible endpoint

Write-Host "╔══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                     LLM Environment Variable Setup                           ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($isAdmin) {
    Write-Host "✓ Running as Administrator" -ForegroundColor Green
} else {
    Write-Host "⚠ Not running as Administrator (can only set User-level variables)" -ForegroundColor Yellow
}
Write-Host ""

# Check current environment variables
$currentApiKeyEnvVar = [System.Environment]::GetEnvironmentVariable('LLM_API_KEY_ENV_VAR', 'User')
$currentLitellmKey = [System.Environment]::GetEnvironmentVariable('litellm_key', 'User')

if ($currentLitellmKey) {
    $keyPreview = $currentLitellmKey.Substring(0, [Math]::Min(15, $currentLitellmKey.Length)) + "..." + $currentLitellmKey.Substring([Math]::Max(0, $currentLitellmKey.Length - 10))
    Write-Host "✓ litellm_key is already set: $keyPreview" -ForegroundColor Green
} else {
    Write-Host "✗ litellm_key is NOT set" -ForegroundColor Red
}
Write-Host ""

# Display options
Write-Host "What would you like to do?" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1) Set User environment variables (persistent, current user only)"
Write-Host "  2) Set Machine environment variables (persistent, all users - requires Admin)"
Write-Host "  3) Set Process environment variables (temporary, current session only)"
Write-Host "  4) Display values to manually set"
Write-Host "  5) Exit without changes"
Write-Host ""

$choice = Read-Host "Enter choice [1-5]"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Setting User environment variables..." -ForegroundColor Yellow

        # Get API key from user if not set
        if (-not $currentLitellmKey) {
            $apiKey = Read-Host "Enter your litellm API key" -AsSecureString
            $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($apiKey)
            $litellmKeyValue = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        } else {
            Write-Host "Using existing API key" -ForegroundColor Green
            $litellmKeyValue = $currentLitellmKey
        }

        # Set environment variables
        [System.Environment]::SetEnvironmentVariable('LLM_API_KEY_ENV_VAR', 'litellm_key', 'User')
        [System.Environment]::SetEnvironmentVariable('litellm_key', $litellmKeyValue, 'User')

        Write-Host "✓ Environment variables set for current user" -ForegroundColor Green
        Write-Host ""
        Write-Host "Variables set:" -ForegroundColor Cyan
        Write-Host "  LLM_API_KEY_ENV_VAR = litellm_key"
        Write-Host "  litellm_key = $($litellmKeyValue.Substring(0, [Math]::Min(15, $litellmKeyValue.Length)))...$($litellmKeyValue.Substring([Math]::Max(0, $litellmKeyValue.Length - 10)))"
        Write-Host ""
        Write-Host "Note: Restart your terminal for changes to take effect" -ForegroundColor Yellow
    }

    "2" {
        if (-not $isAdmin) {
            Write-Host ""
            Write-Host "✗ ERROR: Setting Machine variables requires Administrator privileges" -ForegroundColor Red
            Write-Host "Please run PowerShell as Administrator and try again" -ForegroundColor Yellow
            exit 1
        }

        Write-Host ""
        Write-Host "Setting Machine environment variables..." -ForegroundColor Yellow

        # Get API key from user if not set
        if (-not $currentLitellmKey) {
            $apiKey = Read-Host "Enter your litellm API key" -AsSecureString
            $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($apiKey)
            $litellmKeyValue = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        } else {
            Write-Host "Using existing API key" -ForegroundColor Green
            $litellmKeyValue = $currentLitellmKey
        }

        # Set environment variables
        [System.Environment]::SetEnvironmentVariable('LLM_API_KEY_ENV_VAR', 'litellm_key', 'Machine')
        [System.Environment]::SetEnvironmentVariable('litellm_key', $litellmKeyValue, 'Machine')

        Write-Host "✓ Environment variables set for all users" -ForegroundColor Green
        Write-Host ""
        Write-Host "Note: Restart your terminal for changes to take effect" -ForegroundColor Yellow
    }

    "3" {
        Write-Host ""
        Write-Host "Setting Process environment variables (current session only)..." -ForegroundColor Yellow

        # Get API key from user if not set
        if (-not $env:litellm_key) {
            $apiKey = Read-Host "Enter your litellm API key" -AsSecureString
            $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($apiKey)
            $litellmKeyValue = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        } else {
            $litellmKeyValue = $env:litellm_key
        }

        # Set for current process
        $env:LLM_API_KEY_ENV_VAR = 'litellm_key'
        $env:litellm_key = $litellmKeyValue

        Write-Host "✓ Environment variables set for current PowerShell session" -ForegroundColor Green
        Write-Host ""
        Write-Host "Variables set:" -ForegroundColor Cyan
        Write-Host "  `$env:LLM_API_KEY_ENV_VAR = litellm_key"
        Write-Host "  `$env:litellm_key = $($litellmKeyValue.Substring(0, [Math]::Min(15, $litellmKeyValue.Length)))...$($litellmKeyValue.Substring([Math]::Max(0, $litellmKeyValue.Length - 10)))"
        Write-Host ""
        Write-Host "Note: These will be lost when you close this PowerShell window" -ForegroundColor Yellow
    }

    "4" {
        Write-Host ""
        Write-Host "To manually set environment variables:" -ForegroundColor Cyan
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Method 1: PowerShell (User-level, persistent):" -ForegroundColor Yellow
        Write-Host '  [System.Environment]::SetEnvironmentVariable(''LLM_API_KEY_ENV_VAR'', ''litellm_key'', ''User'')'
        Write-Host '  [System.Environment]::SetEnvironmentVariable(''litellm_key'', ''YOUR_API_KEY_HERE'', ''User'')'
        Write-Host ""
        Write-Host "Method 2: GUI (User-level, persistent):" -ForegroundColor Yellow
        Write-Host "  1. Press Win+R, type 'sysdm.cpl', press Enter"
        Write-Host "  2. Go to Advanced tab → Environment Variables"
        Write-Host "  3. Under 'User variables', click 'New'"
        Write-Host "  4. Add: LLM_API_KEY_ENV_VAR = litellm_key"
        Write-Host "  5. Add: litellm_key = YOUR_API_KEY_HERE"
        Write-Host ""
        Write-Host "Method 3: Current session only (temporary):" -ForegroundColor Yellow
        Write-Host '  $env:LLM_API_KEY_ENV_VAR = ''litellm_key'''
        Write-Host '  $env:litellm_key = ''YOUR_API_KEY_HERE'''
        Write-Host ""
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    }

    "5" {
        Write-Host "Exiting without changes" -ForegroundColor Gray
        exit 0
    }

    default {
        Write-Host "Invalid choice" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "✓ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To verify the configuration works:" -ForegroundColor Cyan
Write-Host "  python test_llm_migration.py" -ForegroundColor White
