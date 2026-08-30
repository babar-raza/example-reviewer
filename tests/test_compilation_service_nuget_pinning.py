"""Tests for TC-EPIC3-01: pin NuGet versions + locked-mode restore.

Covers CompilationService._write_project()'s CI/production-mode enforcement
(restore_mode='locked' requires a real pinned version, never silently
substitutes "*"), the now-configurable System.Drawing.Common auto-added
package version, and _run_build()'s --locked-mode wiring. See
reports/investigation/20260829_124758_production_readiness/taskcards/TC-EPIC3-01.md.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.config import FamilyConfig, NuGetConfig, NuGetPackage
from src.services.compilation_service import CompilationService, NuGetVersionPinRequiredError


def _make_service(tmp_path) -> CompilationService:
    return CompilationService(
        db=MagicMock(), family="zip", registry=None,
        workspace_dir=tmp_path / "workspace", artifacts_dir=tmp_path / "artifacts",
    )


def _read_csproj(work_dir: Path) -> str:
    return (work_dir / "Compilation.csproj").read_text(encoding="utf-8")


class TestFloatingModeBackwardCompatibility:
    def test_pinned_version_written_verbatim(self, tmp_path):
        service = _make_service(tmp_path)
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        family_config = FamilyConfig(
            family="zip",
            nuget_config=NuGetConfig(primary_package=NuGetPackage(name="Aspose.Zip", version="26.8.0")),
        )
        service._write_project(work_dir, family_config)
        csproj = _read_csproj(work_dir)
        assert 'Include="Aspose.Zip" Version="26.8.0"' in csproj
        assert 'Version="*"' not in csproj

    def test_missing_version_falls_back_to_wildcard_in_floating_mode(self, tmp_path):
        """Backward compatibility: dev/exploration mode (the default,
        restore_mode='floating') keeps today's fallback-to-"*" behavior."""
        service = _make_service(tmp_path)
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        family_config = FamilyConfig(
            family="zip",
            nuget_config=NuGetConfig(primary_package=NuGetPackage(name="Aspose.Zip")),
        )
        service._write_project(work_dir, family_config)
        csproj = _read_csproj(work_dir)
        assert 'Include="Aspose.Zip" Version="*"' in csproj

    def test_no_lock_file_property_in_floating_mode(self, tmp_path):
        service = _make_service(tmp_path)
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        family_config = FamilyConfig(
            family="zip",
            nuget_config=NuGetConfig(primary_package=NuGetPackage(name="Aspose.Zip", version="26.8.0")),
        )
        service._write_project(work_dir, family_config)
        csproj = _read_csproj(work_dir)
        assert "RestorePackagesWithLockFile" not in csproj


class TestLockedModeEnforcement:
    def test_missing_primary_version_raises_in_locked_mode(self, tmp_path):
        """The core negative control: a CI/production-mode (restore_mode=
        'locked') compile with no pinned version MUST fail loudly, not
        silently degrade to Version="*"."""
        service = _make_service(tmp_path)
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        family_config = FamilyConfig(
            family="zip",
            nuget_config=NuGetConfig(
                primary_package=NuGetPackage(name="Aspose.Zip"), restore_mode="locked",
            ),
        )
        with pytest.raises(NuGetVersionPinRequiredError, match="Aspose.Zip"):
            service._write_project(work_dir, family_config)
        assert not (work_dir / "Compilation.csproj").exists()

    def test_missing_additional_package_version_raises_in_locked_mode(self, tmp_path):
        service = _make_service(tmp_path)
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        family_config = FamilyConfig(
            family="zip",
            nuget_config=NuGetConfig(
                primary_package=NuGetPackage(name="Aspose.Zip", version="26.8.0"),
                additional_packages=[NuGetPackage(name="Newtonsoft.Json")],
                restore_mode="locked",
            ),
        )
        with pytest.raises(NuGetVersionPinRequiredError, match="Newtonsoft.Json"):
            service._write_project(work_dir, family_config)

    def test_pinned_versions_succeed_in_locked_mode_and_add_lock_file_property(self, tmp_path):
        service = _make_service(tmp_path)
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        family_config = FamilyConfig(
            family="zip",
            nuget_config=NuGetConfig(
                primary_package=NuGetPackage(name="Aspose.Zip", version="26.8.0"), restore_mode="locked",
            ),
        )
        service._write_project(work_dir, family_config)
        csproj = _read_csproj(work_dir)
        assert 'Include="Aspose.Zip" Version="26.8.0"' in csproj
        assert "<RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>" in csproj

    def test_run_build_adds_locked_mode_flag_to_restore_command(self, tmp_path):
        service = _make_service(tmp_path)
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        family_config = FamilyConfig(
            family="zip",
            nuget_config=NuGetConfig(
                primary_package=NuGetPackage(name="Aspose.Zip", version="26.8.0"), restore_mode="locked",
            ),
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            service._run_build(work_dir, family_config)

        restore_call = mock_run.call_args_list[0]
        restore_cmd = restore_call.args[0]
        assert "--locked-mode" in restore_cmd

    def test_run_build_omits_locked_mode_flag_in_floating_mode(self, tmp_path):
        service = _make_service(tmp_path)
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        family_config = FamilyConfig(
            family="zip",
            nuget_config=NuGetConfig(primary_package=NuGetPackage(name="Aspose.Zip", version="26.8.0")),
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            service._run_build(work_dir, family_config)

        restore_call = mock_run.call_args_list[0]
        restore_cmd = restore_call.args[0]
        assert "--locked-mode" not in restore_cmd


class TestSystemDrawingCommonVersion:
    def test_uses_configured_drawing_common_version(self, tmp_path):
        service = _make_service(tmp_path)
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        family_config = FamilyConfig(
            family="zip",
            nuget_config=NuGetConfig(
                primary_package=NuGetPackage(name="Aspose.Zip", version="26.8.0"),
                drawing_common_version="8.0.30",
            ),
        )
        service._write_project(work_dir, family_config, wrapped_code="using System.Drawing;")
        csproj = _read_csproj(work_dir)
        assert 'Include="System.Drawing.Common" Version="8.0.30"' in csproj
        assert 'Version="8.*"' not in csproj

    def test_default_drawing_common_version_when_no_nuget_config(self, tmp_path):
        """Fallback default (matches NuGetConfig.drawing_common_version's own
        schema default) when a family has no nuget_config at all."""
        service = _make_service(tmp_path)
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        family_config = FamilyConfig(family="zip", nuget_config=None)
        service._write_project(work_dir, family_config, wrapped_code="using System.Drawing;")
        csproj = _read_csproj(work_dir)
        assert 'Include="System.Drawing.Common" Version="8.0.30"' in csproj


class TestAllFamilyConfigsPinned:
    """Closeout criterion: all 17 family configs have a pinned
    primary_package.version available for CI/production mode."""

    FAMILIES = [
        "barcode", "cad", "cells", "email", "html", "imaging", "medical", "ocr",
        "page", "pdf", "psd", "slides", "smoke", "tasks", "tex", "words", "zip",
    ]

    @pytest.mark.parametrize("family", FAMILIES)
    def test_family_has_pinned_primary_package_version(self, family):
        from src.core.config import ConfigurationManager

        cm = ConfigurationManager(Path("config/families"))
        family_config = cm.load_family_config(family)
        assert family_config.nuget_config is not None, f"{family} has no nuget_config"
        assert family_config.nuget_config.primary_package.version, (
            f"{family}'s primary_package has no pinned version"
        )

    @pytest.mark.parametrize("family", FAMILIES)
    def test_family_would_pass_locked_mode_write_project(self, family, tmp_path):
        """Every family's pinned config must actually satisfy locked-mode's
        enforcement (not just exist, but be usable end-to-end)."""
        from src.core.config import ConfigurationManager

        cm = ConfigurationManager(Path("config/families"))
        family_config = cm.load_family_config(family)
        locked_config = family_config.model_copy(
            update={"nuget_config": family_config.nuget_config.model_copy(update={"restore_mode": "locked"})}
        )
        service = _make_service(tmp_path)
        work_dir = tmp_path / f"work_{family}"
        work_dir.mkdir()
        service._write_project(work_dir, locked_config)  # must not raise
        assert (work_dir / "Compilation.csproj").exists()


@pytest.mark.integration
class TestLockedModeRealDotnetBehavior:
    """Real dotnet/network integration tests (excluded from the default
    hermetic suite -- run with `pytest --integration`).

    Empirically established --locked-mode's actual behavior (evidence:
    taskcards/evidence/TC-EPIC3-01/locked_mode_e2e_zip.log), which differs
    from what its name suggests and from this taskcard's own stated
    assumption ("a stale/missing packages.lock.json MUST fail the restore"):
    --locked-mode fails loudly (NU1004) when an EXISTING lock file is STALE
    (inconsistent with the current PackageReference), but silently CREATES
    one when none exists yet -- a missing lock file does NOT fail the
    restore. See _run_build()'s comment for what this means for this
    pipeline's ephemeral-per-example work_dir architecture.
    """

    def test_stale_lock_file_fails_restore(self, tmp_path):
        import subprocess

        work_dir = tmp_path / "stale_lock_test"
        work_dir.mkdir()
        csproj = work_dir / "Compilation.csproj"
        csproj.write_text(
            '<Project Sdk="Microsoft.NET.Sdk">\n'
            "  <PropertyGroup>\n"
            "    <TargetFramework>net8.0</TargetFramework>\n"
            "    <OutputType>Exe</OutputType>\n"
            "    <RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>\n"
            "  </PropertyGroup>\n"
            "  <ItemGroup>\n"
            '    <PackageReference Include="Newtonsoft.Json" Version="13.0.4" />\n'
            "  </ItemGroup>\n"
            "</Project>\n"
        )
        restore_1 = subprocess.run(
            ["dotnet", "restore", "--verbosity", "minimal"], cwd=work_dir,
            capture_output=True, text=True, timeout=120,
        )
        assert restore_1.returncode == 0
        assert (work_dir / "packages.lock.json").exists()

        # Change the pinned version -- lock file is now stale/inconsistent.
        csproj.write_text(csproj.read_text().replace("13.0.4", "13.0.3"))

        restore_2 = subprocess.run(
            ["dotnet", "restore", "--verbosity", "minimal", "--locked-mode"], cwd=work_dir,
            capture_output=True, text=True, timeout=120,
        )
        assert restore_2.returncode != 0
        assert "NU1004" in restore_2.stdout

    def test_missing_lock_file_does_not_fail_restore(self, tmp_path):
        """The corrected finding: --locked-mode with NO lock file present at
        all succeeds and creates one, rather than failing."""
        import subprocess

        work_dir = tmp_path / "missing_lock_test"
        work_dir.mkdir()
        (work_dir / "Compilation.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk">\n'
            "  <PropertyGroup>\n"
            "    <TargetFramework>net8.0</TargetFramework>\n"
            "    <OutputType>Exe</OutputType>\n"
            "    <RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>\n"
            "  </PropertyGroup>\n"
            "  <ItemGroup>\n"
            '    <PackageReference Include="Newtonsoft.Json" Version="13.0.4" />\n'
            "  </ItemGroup>\n"
            "</Project>\n"
        )
        assert not (work_dir / "packages.lock.json").exists()

        result = subprocess.run(
            ["dotnet", "restore", "--verbosity", "minimal", "--locked-mode"], cwd=work_dir,
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0
        assert (work_dir / "packages.lock.json").exists()

    def test_zip_family_locked_mode_end_to_end(self, tmp_path):
        """The pilot-family Exit Gate requirement: locked-mode restore works
        end-to-end for zip using this service's real _write_project()/
        _run_build() (not hand-written project files)."""
        from src.core.config import ConfigurationManager

        cm = ConfigurationManager(Path("config/families"))
        zip_config = cm.load_family_config("zip")
        locked_config = zip_config.model_copy(
            update={"nuget_config": zip_config.nuget_config.model_copy(update={"restore_mode": "locked"})}
        )
        service = _make_service(tmp_path)
        work_dir = tmp_path / "zip_e2e"
        work_dir.mkdir()
        service._write_project(work_dir, locked_config)
        # A minimal valid entry point -- _run_build compiles whatever .cs
        # files are in work_dir; this test isolates the NuGet/restore
        # infrastructure, not the pipeline's own code-wrapping logic.
        (work_dir / "Program.cs").write_text(
            "using Aspose.Zip;\nSystem.Console.WriteLine(typeof(Archive).FullName);\n"
        )

        result = service._run_build(work_dir, locked_config)
        assert result.success, f"Build failed: {result.errors}"
        assert (work_dir / "packages.lock.json").exists()
