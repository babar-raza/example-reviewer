"""
Setup wizard for example-reviewer.

Guides a new user through:
1. Checking prerequisites (Python, .NET SDK)
2. Installing Python dependencies
3. Configuring a product family
4. Scaffolding / updating the .NET build host (test-examples/)
5. Generating the API catalog
6. Verifying the setup

Usage:
    python scripts/setup/setup_wizard.py
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Ensure stdout handles utf-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run(cmd, **kwargs):
    """Run a subprocess command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        **kwargs
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def ok(msg):
    print(f"  [OK] {msg}")


def info(msg):
    print(f"  [i]  {msg}")


def warn(msg):
    print(f"  [!]  {msg}")


def fail(msg):
    print(f"  [X]  {msg}")


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check_prerequisites():
    section("Step 1: Check Prerequisites")

    all_ok = True

    # Python version
    major, minor = sys.version_info.major, sys.version_info.minor
    if major >= 3 and minor >= 10:
        ok(f"Python {major}.{minor} detected (3.10+ required)")
    else:
        fail(f"Python {major}.{minor} detected — need 3.10+. Please upgrade.")
        all_ok = False

    # .NET SDK
    code, stdout, stderr = run(["dotnet", "--version"])
    if code == 0:
        ok(f".NET SDK {stdout} detected")
    else:
        fail(".NET SDK not found. Install from https://dotnet.microsoft.com/download")
        all_ok = False

    # test-examples/ is scaffolded in Step 4; just confirm dotnet is reachable here
    info("test-examples/ will be scaffolded automatically in Step 4")

    return all_ok


def install_dependencies():
    section("Step 2: Install Python Dependencies")

    venv_python = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = PROJECT_ROOT / "venv" / "bin" / "python"

    if not venv_python.exists():
        info("No venv/ found. Creating one...")
        code, _, stderr = run([sys.executable, "-m", "venv", "venv"], cwd=str(PROJECT_ROOT))
        if code != 0:
            fail(f"Could not create venv: {stderr}")
            return False
        ok("Created venv/")

    requirements = PROJECT_ROOT / "requirements.txt"
    if requirements.exists():
        info("Installing requirements.txt into venv...")
        code, stdout, stderr = run(
            [str(venv_python), "-m", "pip", "install", "-r", str(requirements), "--quiet"],
            cwd=str(PROJECT_ROOT)
        )
        if code == 0:
            ok("Dependencies installed")
        else:
            fail(f"pip install failed:\n{stderr[:400]}")
            return False
    else:
        warn("requirements.txt not found — skipping pip install")

    return True


def list_families():
    """Return list of available family names from config/families/."""
    families_dir = PROJECT_ROOT / "config" / "families"
    if not families_dir.exists():
        return []
    return sorted(
        p.stem for p in families_dir.glob("*.json")
        if p.stem not in ("global",)
    )


def select_family():
    section("Step 3: Select a Product Family to Configure")

    families = list_families()
    if not families:
        warn("No family configs found in config/families/")
        info("Create a config file there first. See config/README.md for structure.")
        return None

    print("\n  Available families:")
    for i, name in enumerate(families, 1):
        print(f"    {i}. {name}")

    while True:
        choice = input("\n  Enter family number (or name): ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(families):
                return families[idx]
        elif choice in families:
            return choice
        print("  Invalid choice, try again.")


def configure_content_roots(family):
    section(f"Step 4: Configure Content Roots for '{family}'")

    config_path = PROJECT_ROOT / "config" / "families" / f"{family}.json"
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    current_roots = config.get("content_roots", [])
    if current_roots:
        info("Current content_roots:")
        for root in current_roots:
            exists = Path(root).exists()
            status = "exists" if exists else "NOT FOUND"
            print(f"    {root} [{status}]")

        choice = input("\n  Content roots look correct? [y/n]: ").strip().lower()
        if choice == 'y':
            ok("Keeping existing content_roots")
            return True

    print("\n  Enter paths to markdown content directories (one per line).")
    print("  Press Enter with empty line when done.")
    new_roots = []
    while True:
        path = input("  Path: ").strip()
        if not path:
            break
        p = Path(path)
        if p.exists():
            new_roots.append(str(p))
            ok(f"Added: {path}")
        else:
            warn(f"Path does not exist: {path}")
            add_anyway = input("  Add anyway? [y/n]: ").strip().lower()
            if add_anyway == 'y':
                new_roots.append(str(p))

    if new_roots:
        config["content_roots"] = new_roots
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        ok(f"Saved {len(new_roots)} content root(s) to {config_path.name}")
        return True
    else:
        warn("No content roots configured. You can edit config/families/{family}.json manually.")
        return False


def scaffold_test_examples(family):
    """
    Step 4: Ensure test-examples/ exists and is up-to-date.

    - If missing, scaffold from scripts/setup/templates/.
    - If the selected family's NuGet package is not yet referenced in the
      .csproj, add it (so dotnet restore pulls it into the NuGet cache,
      which CatalogTypes() needs for dynamic reflection).
    - Run dotnet restore + dotnet build to keep the binary current.
    """
    section("Step 4: .NET Build Host (test-examples/)")

    templates_dir = Path(__file__).parent / "templates"
    test_examples = PROJECT_ROOT / "test-examples"
    csproj_path = test_examples / "AsposeZipValidator.csproj"
    program_cs_path = test_examples / "Program.cs"

    # ── 1. Read family config to get the NuGet package ──────────────────────
    config_path = PROJECT_ROOT / "config" / "families" / f"{family}.json"
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    primary_pkg = config.get("nuget_config", {}).get("primary_package", {})
    pkg_name = primary_pkg.get("name", "")
    pkg_version = primary_pkg.get("pinned_version", "") or primary_pkg.get("version", "") or "*"

    # ── 2. Scaffold if test-examples/ or any required file is missing ────────
    test_examples.mkdir(parents=True, exist_ok=True)
    scaffolded = False

    for src, dst in [(templates_dir / "AsposeZipValidator.csproj", csproj_path),
                     (templates_dir / "Program.cs", program_cs_path)]:
        if not dst.exists():
            if not src.exists():
                warn(f"Template not found: {src}")
                warn("Cannot scaffold test-examples/ automatically.")
                return False
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            ok(f"Created test-examples/{dst.name} from template")
            scaffolded = True
        else:
            ok(f"test-examples/{dst.name} already exists")

    # ── 3. Ensure the selected family's package is in the .csproj ───────────
    csproj_text = csproj_path.read_text(encoding="utf-8")
    pkg_already_present = bool(
        re.search(rf'PackageReference\s+Include="{re.escape(pkg_name)}"',
                  csproj_text, re.IGNORECASE)
    )

    if pkg_name and not pkg_already_present:
        new_ref = f'    <PackageReference Include="{pkg_name}" Version="{pkg_version}" />'
        # Insert immediately before the end marker so the file stays clean
        csproj_text = csproj_text.replace(
            "    <!-- FAMILY-PACKAGES-END -->",
            f"{new_ref}\n    <!-- FAMILY-PACKAGES-END -->"
        )
        csproj_path.write_text(csproj_text, encoding="utf-8")
        ok(f"Added {pkg_name} {pkg_version} to AsposeZipValidator.csproj")
        scaffolded = True
    elif pkg_name:
        ok(f"{pkg_name} already referenced in .csproj")

    # ── 4. Build (always after scaffold/edit; skip if binary is current) ─────
    bin_dir = test_examples / "bin"
    needs_build = scaffolded or not bin_dir.exists()

    if needs_build:
        info("Running dotnet restore...")
        code, _, stderr = run(["dotnet", "restore", str(csproj_path)],
                              cwd=str(test_examples))
        if code != 0:
            warn(f"dotnet restore failed: {stderr[:300]}")
            info("You may need to fix network access or NuGet feed settings.")
            return False
        ok("dotnet restore succeeded")

        info("Building .NET build host (dotnet build)...")
        code, _, stderr = run(
            ["dotnet", "build", str(csproj_path), "--no-restore", "--nologo", "-v", "q"],
            cwd=str(test_examples)
        )
        if code == 0:
            ok("Build host compiled successfully")
        else:
            warn(f"dotnet build failed:\n{stderr[:400]}")
            return False
    else:
        ok(".NET build host binary is current — skipping rebuild")

    return True


def generate_catalog(family):
    section(f"Step 5: Generate API Catalog for '{family}'")

    config_path = PROJECT_ROOT / "config" / "families" / f"{family}.json"
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    catalog_section = config.get("api_catalog", {})
    # Field is "path", not "catalog_path"
    catalog_rel_path = catalog_section.get("path", "")
    catalog_abs_path = PROJECT_ROOT / catalog_rel_path if catalog_rel_path else None

    if catalog_abs_path and catalog_abs_path.exists():
        ok(f"API catalog already exists: {catalog_rel_path}")
        regen = input("  Regenerate? [y/n]: ").strip().lower()
        if regen != 'y':
            return True

    nuget_config = config.get("nuget_config", {})
    primary_pkg = nuget_config.get("primary_package", {})
    pkg_name = primary_pkg.get("name", "")
    # Use explicit pinned_version if present; otherwise omit and let NuGet resolve latest stable
    pkg_version = primary_pkg.get("pinned_version", "") or primary_pkg.get("version", "")
    # Namespace prefix defaults to the package name (e.g. Aspose.Zip -> Aspose.Zip)
    namespace_prefix = primary_pkg.get("namespace_prefix", pkg_name)

    if not pkg_name:
        warn("No nuget_config.primary_package.name found in family config.")
        info("Skipping catalog generation. Run scripts/setup/extract_assembly_catalog.py manually.")
        return False

    if not catalog_abs_path:
        warn("No api_catalog.path configured in family JSON.")
        info("Skipping catalog generation.")
        return False

    extract_script = PROJECT_ROOT / "scripts" / "setup" / "extract_assembly_catalog.py"
    if not extract_script.exists():
        warn(f"extract_assembly_catalog.py not found at {extract_script}")
        return False

    info(f"Generating catalog for {pkg_name} {pkg_version or '(latest stable)'}...")
    info("This downloads the NuGet package and runs .NET reflection — may take 30-60 seconds.")

    cmd = [sys.executable, str(extract_script), pkg_name]
    if pkg_version:
        cmd += [pkg_version]
    cmd += [namespace_prefix, "--full"]

    code, stdout, stderr = run(cmd, cwd=str(PROJECT_ROOT))

    if code != 0:
        warn(f"Catalog generation failed:\n{stderr[:400]}")
        info(f"You can run it manually:")
        info(f"  python scripts/setup/extract_assembly_catalog.py {pkg_name} [version] {namespace_prefix} --full")
        info(f"  Then save the output to: {catalog_rel_path}")
        return False

    # The script writes JSON to stdout — save it to the configured catalog path
    if not stdout.strip():
        warn("Catalog script produced no output.")
        return False

    catalog_abs_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_abs_path.write_text(stdout, encoding="utf-8")
    ok(f"Catalog saved to {catalog_rel_path}")
    return True


def verify_setup(family):
    section(f"Step 6: Verify Setup for '{family}'")

    # Try running list-families
    code, stdout, stderr = run(
        [sys.executable, "-m", "src.cli.main", "list-families"],
        cwd=str(PROJECT_ROOT)
    )
    if code == 0:
        ok("CLI works: list-families succeeded")
    else:
        warn(f"CLI list-families failed: {stderr[:300]}")

    # Try running status
    code, stdout, stderr = run(
        [sys.executable, "-m", "src.cli.main", "status", "--family", family],
        cwd=str(PROJECT_ROOT)
    )
    if code == 0:
        ok(f"CLI works: status --family {family} succeeded")
        if stdout:
            print()
            for line in stdout.splitlines()[:10]:
                print(f"    {line}")
    else:
        warn(f"status command failed: {stderr[:300]}")


def print_next_steps(family):
    section("Setup Complete!")
    print(f"""
  You're ready to run the pipeline for family: {family}

  Basic commands:
    # Full pipeline (discover, compile, fix, verify, commit):
    python -m src.cli.main run --family {family}

    # Check status:
    python -m src.cli.main status --family {family}

    # Dry run (no markdown writes):
    python -m src.cli.main run --family {family} --dry-run

    # Download missing test data:
    python -m src.cli.main backfill --family {family}

  Documentation:
    docs/overview.md   - Pipeline overview
    docs/pipeline.md   - Phase-by-phase guide
    docs/ops-runbook.md - Day-to-day operations

  Run tests:
    pytest tests/ -v --timeout=120
""")


def main():
    print("\n  Example Reviewer - Setup Wizard")
    print("  Guides you through first-time configuration.\n")

    # Step 1: Prerequisites
    prereqs_ok = check_prerequisites()
    if not prereqs_ok:
        print("\n  Please fix prerequisites above before continuing.")
        sys.exit(1)

    # Step 2: Dependencies
    deps_ok = install_dependencies()
    if not deps_ok:
        print("\n  Dependency installation failed. See errors above.")
        sys.exit(1)

    # Step 3: Select family
    family = select_family()
    if not family:
        print("\n  No family selected. Exiting.")
        sys.exit(0)

    # Step 4: Scaffold / update .NET build host
    build_host_ok = scaffold_test_examples(family)
    if not build_host_ok:
        print("\n  .NET build host setup failed.")
        print("  Resolve the errors above, then re-run the wizard or build manually:")
        print("    dotnet build test-examples/AsposeZipValidator.csproj")
        sys.exit(1)

    # Step 5 (renumbered): Configure content roots
    configure_content_roots(family)

    # Step 6 (renumbered): Generate API catalog
    generate_catalog(family)

    # Step 7 (renumbered): Verify
    verify_setup(family)

    # Done
    print_next_steps(family)


if __name__ == "__main__":
    main()
