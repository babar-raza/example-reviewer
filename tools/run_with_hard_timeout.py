#!/usr/bin/env python3
"""
Gate 2: Hard Timeout Enforcement Tool

Run pipeline with hard timeout to prevent hangs.

Requirements (from Plan v2.1):
- Accept --seconds N and command to run
- Use subprocess with timeout (cross-platform, no SIGALRM)
- Kill process tree on timeout (handle child processes)
- Exit code: 0=success, 1=command failed, 124=timeout
- Print stdout/stderr in real-time

Usage:
    python tools/run_with_hard_timeout.py --seconds 1200 -- python -m src.cli.main run --family zip --dry-run
"""

import argparse
import subprocess
import sys
import signal
import os
from typing import List


def kill_process_tree(pid: int):
    """
    Kill process and all its children (cross-platform).

    On Windows, uses taskkill /F /T.
    On Unix, uses process group termination.
    """
    try:
        if sys.platform == 'win32':
            # Windows: use taskkill with /T (tree) flag
            subprocess.run(
                ['taskkill', '/F', '/T', '/PID', str(pid)],
                capture_output=True,
                timeout=5
            )
        else:
            # Unix: send SIGTERM to process group
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except ProcessLookupError:
                pass  # Process already terminated
    except Exception as e:
        print(f"Warning: Failed to kill process tree for PID {pid}: {e}", file=sys.stderr)


def run_with_timeout(command: List[str], timeout_seconds: int) -> int:
    """
    Run command with hard timeout.

    Returns:
        0 if command succeeds
        1 if command fails
        124 if timeout occurs (convention from GNU timeout)
    """
    print(f"Running command with {timeout_seconds}s timeout:")
    print(f"  {' '.join(command)}\n")
    print("="*60)

    try:
        # Create process with platform-appropriate settings
        if sys.platform == 'win32':
            # Windows: CREATE_NEW_PROCESS_GROUP for clean termination
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,  # Line buffered
                creationflags=creationflags
            )
        else:
            # Unix: use process group for tree termination
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,  # Line buffered
                preexec_fn=os.setsid  # Create new session
            )

        # Read output in real-time
        try:
            for line in process.stdout:
                print(line, end='')

            # Wait for process to complete or timeout
            process.wait(timeout=timeout_seconds)

            print("\n" + "="*60)
            print(f"Command completed with exit code: {process.returncode}")

            return 0 if process.returncode == 0 else 1

        except subprocess.TimeoutExpired:
            print("\n" + "="*60)
            print(f"X TIMEOUT: Command exceeded {timeout_seconds} seconds")
            print("="*60)

            # Kill process tree
            print(f"Terminating process tree (PID {process.pid})...")
            kill_process_tree(process.pid)

            # Wait a bit for cleanup
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if still alive
                process.kill()
                try:
                    process.wait(timeout=2)
                except:
                    pass

            return 124  # GNU timeout convention

    except FileNotFoundError:
        print(f"ERROR: Command not found: {command[0]}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: Failed to run command: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Run command with hard timeout (cross-platform)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/run_with_hard_timeout.py --seconds 1200 -- python -m src.cli.main run --family zip --dry-run
  python tools/run_with_hard_timeout.py --seconds 60 -- pytest -q

Exit codes:
  0   - Command succeeded
  1   - Command failed or error occurred
  124 - Timeout occurred (GNU timeout convention)
        """
    )

    parser.add_argument(
        '--seconds',
        type=int,
        required=True,
        help='Timeout in seconds'
    )

    parser.add_argument(
        'command',
        nargs=argparse.REMAINDER,
        help='Command to run (after --)'
    )

    args = parser.parse_args()

    # Remove '--' separator if present
    command = args.command
    if command and command[0] == '--':
        command = command[1:]

    if not command:
        print("ERROR: No command specified", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    if args.seconds <= 0:
        print("ERROR: Timeout must be positive", file=sys.stderr)
        sys.exit(1)

    exit_code = run_with_timeout(command, args.seconds)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
