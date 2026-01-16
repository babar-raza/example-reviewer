"""Wrapper to run CLI with vendored packages and .env support."""
import sys
import os
from pathlib import Path

# Add vendored packages to path
sys.path.insert(0, str(Path(__file__).parent / 'Python313Libsite-packages'))

# Load .env file manually
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# Run CLI
from src.cli import main

if __name__ == '__main__':
    main()
