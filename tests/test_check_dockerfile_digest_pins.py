"""Tests for TC-EPIC3-02: Dockerfile digest-pin regression guard.

See reports/investigation/20260829_124758_production_readiness/taskcards/TC-EPIC3-02.md.
"""

from pathlib import Path

from scripts.validation.check_dockerfile_digest_pins import check, main


class TestCheck:
    def test_real_dockerfile_is_clean(self):
        """The actual repo Dockerfile must pass -- this is the taskcard's
        own closeout proof."""
        assert check(Path("Dockerfile")) == []

    def test_flags_from_line_without_digest(self, tmp_path):
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("FROM python:3.12-slim-bookworm\n")
        violations = check(dockerfile)
        assert len(violations) == 1
        assert "python:3.12-slim-bookworm" in violations[0]

    def test_passes_from_line_with_digest(self, tmp_path):
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text(
            "FROM python:3.12-slim-bookworm@sha256:"
            + "0" * 64 + "\n"
        )
        assert check(dockerfile) == []

    def test_flags_stale_truncated_digest(self, tmp_path):
        """A truncated/malformed digest (not a valid 64-hex-char sha256) must
        still be flagged, not accepted as 'has an @ so it's fine'."""
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("FROM python:3.12-slim-bookworm@sha256:deadbeef\n")
        violations = check(dockerfile)
        assert len(violations) == 1

    def test_skips_stage_reference_from_lines(self, tmp_path):
        """`FROM <stage-name>` (a later multi-stage build referencing an
        earlier stage, not a registry image) has nothing to pin -- must not
        be flagged."""
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text(
            "FROM python:3.12-slim-bookworm@sha256:" + "0" * 64 + " AS base\n"
            "FROM base\n"
        )
        assert check(dockerfile) == []

    def test_flags_multiple_unpinned_from_lines(self, tmp_path):
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text(
            "FROM mcr.microsoft.com/dotnet/sdk:8.0-bookworm-slim AS dotnet-sdk\n"
            "FROM python:3.12-slim-bookworm\n"
        )
        assert len(check(dockerfile)) == 2


class TestMain:
    def test_main_exits_zero_on_clean_dockerfile(self):
        assert main(["Dockerfile"]) == 0

    def test_main_exits_nonzero_on_violation(self, tmp_path):
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("FROM python:3.12-slim-bookworm\n")
        assert main([str(dockerfile)]) == 1

    def test_main_exits_nonzero_for_missing_file(self, tmp_path):
        assert main([str(tmp_path / "does_not_exist")]) == 1
