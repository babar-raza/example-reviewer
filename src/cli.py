"""
CLI for Aspose Example Review System.
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from database import Database
from telemetry import TelemetryClient
from discovery_service import DiscoveryService
from pattern_registry import PatternRegistry
from ollama_integration import OllamaClient
from workspace_manager import WorkspaceManager
from validation_orchestrator import ValidationOrchestrator
from patching_service import PatchingService
from gist_service import GistService


class CLI:
    """Command-line interface for Example Review System."""

    def __init__(self):
        self.script_dir = Path(__file__).parent.parent
        self.repo_root = self.script_dir
        self.db_path = self.script_dir / "data" / "examples.db"
        self.artifacts_dir = self.script_dir / "artifacts"
        self.config_dir = self.repo_root / "config" / "families"
        self.content_dir = self.repo_root / "content"

        # Initialize components
        self.db = Database(self.db_path)
        self.telemetry = TelemetryClient(self.artifacts_dir)

    def init_db(self):
        """Initialize database schema."""
        print("[*] Initializing database...")
        schema_path = self.script_dir / "schema.sql"

        if not schema_path.exists():
            print(f"[!] Schema file not found: {schema_path}")
            return 1

        try:
            self.db.initialize_schema(schema_path)
            print("[OK] Database initialized successfully")
            print(f"[i] Database location: {self.db_path}")
            return 0
        except Exception as e:
            print(f"[!] Failed to initialize database: {e}")
            return 1

    def discover(self, family: str, max_pages: int = None, content_root: str = None):
        """Run discovery for a family."""
        print(f"[*] Starting discovery for family: {family}")

        # Check family config exists
        family_config_path = self.config_dir / f"{family}.json"
        if not family_config_path.exists():
            print(f"[!] Family config not found: {family_config_path}")
            return 1

        # Determine content root
        if content_root:
            repo_root = Path(content_root)
            print(f"[i] Using custom content root: {repo_root}")
        else:
            repo_root = self.repo_root
            print(f"[i] Using default content root: {repo_root}")

        # Verify cache integrity before discovery
        print("[*] Verifying gist cache integrity...")
        gist_cache_dir = self.script_dir / "cache" / "gists"
        gist_service = GistService(cache_dir=gist_cache_dir, db=self.db)
        cache_result = gist_service.verify_cache()

        if cache_result['corrupted_files'] > 0:
            print(f"[!] Found and removed {cache_result['corrupted_files']} corrupted cache files")
        else:
            print(f"[OK] Cache verification complete: {cache_result['valid_files']} files verified")

        # Create run
        run_id = self.db.create_run('discovery', family)
        run_dir = self.telemetry.start_run(run_id, 'discovery', family)

        print(f"[i] Run ID: {run_id}")
        print(f"[i] Artifacts directory: {run_dir}")

        try:
            # Run discovery
            discovery = DiscoveryService(repo_root, self.db, self.telemetry, self.config_dir)

            if max_pages:
                print(f"[i] Limiting to {max_pages} pages")

            stats = discovery.discover_family(family, max_pages=max_pages)

            # Update run
            self.db.update_run(
                run_id,
                pages_processed=stats['pages_processed'],
                snippets_processed=stats['snippets_found']
            )

            # Complete run
            self.db.complete_run(run_id, 'completed')
            self.telemetry.finish_run('completed')

            # Print summary
            print("\n[OK] Discovery completed")
            print(f"[i] Pages found: {stats['pages_found']}")
            print(f"[i] Pages processed: {stats['pages_processed']}")
            print(f"[i] Snippets found: {stats['snippets_found']}")
            print(f"[i] Errors: {stats['errors']}")

            # Generate report
            self.generate_discovery_report(family, run_dir)

            return 0

        except Exception as e:
            print(f"[!] Discovery failed: {e}")
            self.db.complete_run(run_id, 'failed', str(e))
            self.telemetry.finish_run('failed', str(e))
            return 1

    def generate_discovery_report(self, family: str, run_dir: Path):
        """Generate discovery report."""
        print("[*] Generating discovery report...")

        try:
            stats = self.db.get_family_statistics(family)

            report = {
                "family": family,
                "generated_at": datetime.utcnow().isoformat(),
                "statistics": stats
            }

            # Save JSON report
            report_path = run_dir / "discovery_report.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)

            print(f"[OK] Report saved to: {report_path}")

            # Print summary
            print("\n=== Discovery Summary ===")
            print(f"Total pages: {stats.get('total_pages', 0)}")
            print(f"Total snippets: {stats.get('total_snippets', 0)}")
            print(f"Verified: {stats.get('verified', 0)}")
            print(f"Unverified: {stats.get('unverified', 0)}")
            print(f"Needs fix: {stats.get('needs_fix', 0)}")
            print(f"Skipped: {stats.get('skipped', 0)}")

        except Exception as e:
            print(f"[!] Failed to generate report: {e}")

    def db_status(self, family: str = None):
        """Show database status."""
        print("[*] Database Status")
        print(f"[i] Database: {self.db_path}")

        if family:
            print(f"[i] Family: {family}")
            stats = self.db.get_family_statistics(family)

            print(f"\nPages: {stats.get('total_pages', 0)}")
            print(f"Snippets: {stats.get('total_snippets', 0)}")
            print(f"  - Verified: {stats.get('verified', 0)}")
            print(f"  - Unverified: {stats.get('unverified', 0)}")
            print(f"  - Needs fix: {stats.get('needs_fix', 0)}")
            print(f"  - Skipped: {stats.get('skipped', 0)}")
        else:
            # Show overall stats
            self.db.connect()
            cursor = self.db._conn.execute("SELECT COUNT(*) as cnt FROM pages")
            page_count = cursor.fetchone()['cnt']

            cursor = self.db._conn.execute("SELECT COUNT(*) as cnt FROM snippets")
            snippet_count = cursor.fetchone()['cnt']

            cursor = self.db._conn.execute("SELECT COUNT(*) as cnt FROM runs")
            run_count = cursor.fetchone()['cnt']

            print(f"\nTotal pages: {page_count}")
            print(f"Total snippets: {snippet_count}")
            print(f"Total runs: {run_count}")

        return 0

    def check_ollama(self):
        """Check Ollama availability."""
        print("[*] Checking Ollama...")

        ollama = OllamaClient()

        if not ollama.is_available():
            print("[!] Ollama is not available")
            print("[i] Make sure Ollama is running: ollama serve")
            return 1

        print("[OK] Ollama is available")

        # Select model
        model = ollama.select_model()
        if model:
            print(f"[OK] Selected model: {model}")
        else:
            print("[!] No suitable model found")
            print("[i] Install a code model: ollama pull qwen2.5-coder")
            return 1

        return 0

    def validate(self, family: str, max_snippets: int = None, use_ollama: bool = True, content_root: str = None):
        """Run validation for a family."""
        print(f"[*] Starting validation for family: {family}")

        # Determine content root (for future use)
        if content_root:
            repo_root = Path(content_root)
            print(f"[i] Using custom content root: {repo_root}")
        else:
            repo_root = self.repo_root
            print(f"[i] Using default content root: {repo_root}")

        # Check family config exists
        family_config_path = self.config_dir / f"{family}.json"
        if not family_config_path.exists():
            print(f"[!] Family config not found: {family_config_path}")
            return 1

        # Load family config
        with open(family_config_path, 'r', encoding='utf-8') as f:
            family_config = json.load(f)

        # Create run
        run_id = self.db.create_run('validation', family, family_config)
        run_dir = self.telemetry.start_run(run_id, 'validation', family)

        print(f"[i] Run ID: {run_id}")
        print(f"[i] Artifacts directory: {run_dir}")

        try:
            # Initialize components
            pattern_registry = PatternRegistry(family_config_path)
            workspaces_root = self.script_dir / "workspaces"
            workspace = WorkspaceManager(workspaces_root, family_config)

            # Setup workspace
            print("[*] Setting up .NET workspace...")
            if not workspace.setup_workspace():
                print("[!] Failed to setup workspace")
                return 1
            print("[OK] Workspace ready")

            # Initialize Ollama if enabled
            ollama = None
            if use_ollama:
                print("[*] Checking Ollama...")
                ollama = OllamaClient()
                if ollama.is_available():
                    model = ollama.select_model()
                    print(f"[OK] Using Ollama model: {model}")
                else:
                    print("[!] Ollama not available, skipping LLM fixes")
                    ollama = None

            # Create orchestrator
            orchestrator = ValidationOrchestrator(
                self.db, self.telemetry, pattern_registry,
                workspace, ollama, family_config
            )

            # Get unverified snippets
            snippets = self.db.get_snippets_by_status(family, 'unverified')

            if max_snippets:
                snippets = snippets[:max_snippets]
                print(f"[i] Limiting to {max_snippets} snippets")

            print(f"[i] Found {len(snippets)} unverified snippets")

            # Validate snippets
            verified_count = 0
            needs_fix_count = 0
            error_count = 0

            for idx, (snippet, page) in enumerate(snippets, 1):
                print(f"\n[{idx}/{len(snippets)}] Validating snippet {snippet.snippet_id} from {page.relative_path}")

                try:
                    result = orchestrator.validate_snippet(snippet.snippet_id, run_id, use_ollama)

                    if result['status'] == 'verified':
                        verified_count += 1
                        print(f"  [OK] Verified - {result.get('message', '')}")
                    elif result['status'] == 'needs-fix':
                        needs_fix_count += 1
                        print(f"  [!] Needs fix - {result.get('message', '')}")
                    else:
                        error_count += 1
                        print(f"  [X] Error - {result.get('message', '')}")

                except Exception as e:
                    error_count += 1
                    print(f"  [X] Error: {e}")

            # Update run
            self.db.update_run(
                run_id,
                snippets_processed=len(snippets)
            )

            # Complete run
            self.db.complete_run(run_id, 'completed')
            self.telemetry.finish_run('completed')

            # Print summary
            print("\n[OK] Validation completed")
            print(f"[i] Snippets processed: {len(snippets)}")
            print(f"[i] Verified: {verified_count}")
            print(f"[i] Needs fix: {needs_fix_count}")
            print(f"[i] Errors: {error_count}")

            # Generate report
            self.generate_validation_report(family, run_dir, run_id)

            return 0

        except Exception as e:
            print(f"[!] Validation failed: {e}")
            import traceback
            traceback.print_exc()
            self.db.complete_run(run_id, 'failed', str(e))
            self.telemetry.finish_run('failed', str(e))
            return 1

    def generate_validation_report(self, family: str, run_dir: Path, run_id: int):
        """Generate validation report."""
        print("[*] Generating validation report...")

        try:
            stats = self.db.get_family_statistics(family)
            validation_summary = self.db.get_validation_summary(run_id)

            report = {
                "family": family,
                "run_id": run_id,
                "generated_at": datetime.utcnow().isoformat(),
                "statistics": stats,
                "validation_summary": validation_summary
            }

            # Save JSON report
            report_path = run_dir / "validation_report.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)

            print(f"[OK] Report saved to: {report_path}")

            # Print summary
            print("\n=== Validation Summary ===")
            print(f"Total snippets: {stats.get('total_snippets', 0)}")
            print(f"Verified: {stats.get('verified', 0)}")
            print(f"Needs fix: {stats.get('needs_fix', 0)}")
            print(f"Unverified: {stats.get('unverified', 0)}")

        except Exception as e:
            print(f"[!] Failed to generate report: {e}")

    def patch(self, family: str, dry_run: bool = False, gist_mode: str = 'inline-on-change', content_root: str = None):
        """Patch verified snippets back into original files."""
        print(f"[*] Starting patching for family: {family}")

        if dry_run:
            print("[i] DRY RUN MODE - No files will be modified")

        print(f"[i] Gist mode: {gist_mode}")

        # Determine content root
        if content_root:
            repo_root = Path(content_root)
            print(f"[i] Using custom content root: {repo_root}")
        else:
            repo_root = self.repo_root
            print(f"[i] Using default content root: {repo_root}")

        # Check family config exists
        family_config_path = self.config_dir / f"{family}.json"
        if not family_config_path.exists():
            print(f"[!] Family config not found: {family_config_path}")
            return 1

        # Load family config
        with open(family_config_path, 'r', encoding='utf-8') as f:
            family_config = json.load(f)

        # Check if upload modes require env vars
        gist_publisher = None
        if gist_mode in ['upload-on-change', 'upload-always']:
            import os
            # Read env vars
            gist_owner = os.environ.get('GIST_PUBLISH_OWNER')
            gist_token = os.environ.get('GIST_PUBLISH_TOKEN')
            gist_public = os.environ.get('GIST_PUBLISH_PUBLIC', 'true').lower() == 'true'

            if not gist_owner or not gist_token:
                print("[!] Error: upload gist modes require GIST_PUBLISH_OWNER and GIST_PUBLISH_TOKEN env vars")
                return 1

            # Log (redact token)
            token_redacted = "..." + gist_token[-4:] if len(gist_token) >= 4 else "***"
            print(f"[i] Gist publishing enabled: owner={gist_owner}, token={token_redacted}, public={gist_public}")

            # Create publisher
            from gist_publisher import GistPublisher
            gist_publisher = GistPublisher(gist_owner, gist_token, self.db, gist_public)

        # Create patching service WITH gist_publisher
        patcher = PatchingService(self.db, repo_root, gist_publisher)

        try:
            # Patch all verified snippets
            results = patcher.patch_verified_snippets(family, dry_run, gist_mode)

            print(f"\n[OK] Patching completed")
            print(f"[i] Total snippets: {results['total_snippets']}")
            print(f"[i] Patches applied: {results['patches_applied']}")
            print(f"[i] Files modified: {results['files_modified']}")
            print(f"[i] Gists unchanged: {results['gists_unchanged']}")
            print(f"[i] Gists inlined: {results['gists_inlined']}")
            print(f"[i] Errors: {results['errors']}")

            # Show details for each patch
            if results['patches']:
                print("\n=== Patch Details ===")
                for patch in results['patches']:
                    status = "[OK]" if patch.success else "[!]"
                    print(f"{status} Snippet {patch.snippet_id} in {patch.file_path}: {patch.message}")

            return 0

        except Exception as e:
            print(f"[!] Patching failed: {e}")
            import traceback
            traceback.print_exc()
            return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Aspose Example Review System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # init-db command
    subparsers.add_parser('init-db', help='Initialize database')

    # discover command
    discover_parser = subparsers.add_parser('discover', help='Discover code snippets')
    discover_parser.add_argument('--family', required=True, help='Product family (e.g., zip)')
    discover_parser.add_argument('--max-pages', type=int, help='Maximum pages to process')
    discover_parser.add_argument('--content-root', help='Content root directory (default: repository root)')

    # validate command
    validate_parser = subparsers.add_parser('validate', help='Validate code snippets')
    validate_parser.add_argument('--family', required=True, help='Product family (e.g., zip)')
    validate_parser.add_argument('--max-snippets', type=int, help='Maximum snippets to validate')
    validate_parser.add_argument('--no-ollama', action='store_true', help='Disable Ollama LLM fixes')
    validate_parser.add_argument('--content-root', help='Content root directory (default: repository root)')

    # db-status command
    status_parser = subparsers.add_parser('db-status', help='Show database status')
    status_parser.add_argument('--family', help='Product family')

    # check-ollama command
    subparsers.add_parser('check-ollama', help='Check Ollama availability')

    # patch command
    patch_parser = subparsers.add_parser('patch', help='Patch verified snippets into original files')
    patch_parser.add_argument('--family', required=True, help='Product family (e.g., zip)')
    patch_parser.add_argument('--dry-run', action='store_true', help='Dry run mode (don\'t modify files)')
    patch_parser.add_argument(
        '--gist-mode',
        choices=['preserve', 'inline-on-change', 'inline-always', 'upload-on-change', 'upload-always'],
        default='inline-on-change',
        help='How to handle gist snippets: preserve (keep shortcode), inline-on-change (replace if changed), '
             'inline-always (always replace), upload-on-change (publish new gist if changed), '
             'upload-always (always publish new gist)'
    )
    patch_parser.add_argument('--content-root', help='Content root directory (default: repository root)')

    # Parse args
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Create CLI instance
    cli = CLI()

    # Execute command
    if args.command == 'init-db':
        return cli.init_db()
    elif args.command == 'discover':
        return cli.discover(args.family, args.max_pages, getattr(args, 'content_root', None))
    elif args.command == 'validate':
        use_ollama = not args.no_ollama
        return cli.validate(args.family, args.max_snippets, use_ollama, getattr(args, 'content_root', None))
    elif args.command == 'db-status':
        return cli.db_status(args.family)
    elif args.command == 'check-ollama':
        return cli.check_ollama()
    elif args.command == 'patch':
        return cli.patch(args.family, args.dry_run, args.gist_mode, getattr(args, 'content_root', None))
    else:
        print(f"[!] Unknown command: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
