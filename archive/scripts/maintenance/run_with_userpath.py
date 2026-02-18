"""Wrapper to run Python scripts with user site-packages enabled."""
import sys
import os

# Add user site-packages to path
user_site = r'C:\Users\prora\AppData\Roaming\Python\Python313\site-packages'
if user_site not in sys.path:
    sys.path.insert(0, user_site)

# Also set environment variable for subprocesses
os.environ['PYTHONPATH'] = user_site + os.pathsep + os.environ.get('PYTHONPATH', '')

# Run the target module
if len(sys.argv) < 2:
    print("Usage: python run_with_userpath.py <module> [args...]")
    sys.exit(1)

module_name = sys.argv[1]
# Remove this script and module from argv
sys.argv = [sys.argv[0]] + sys.argv[2:]

import runpy
runpy.run_module(module_name, run_name='__main__')
