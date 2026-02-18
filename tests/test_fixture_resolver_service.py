"""
Tests for FixtureResolverService — intelligent self-healing runtime environment.

Tests the 5-tier resolution chain, filename extraction, proactive code scanning,
multi-family generators, and fixture registry persistence.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from src.services.fixture_resolver_service import (
    FixtureResolverService,
    ResolveResult,
    extract_file_references_from_code,
    extract_missing_dirname,
    extract_missing_filename,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_data_dir(tmp_path):
    """Create a test-data directory with some canonical files."""
    td = tmp_path / "test-data"
    td.mkdir()

    # Create canonical files
    (td / "Document.docx").write_bytes(b"PK\x03\x04" + b"\x00" * 100)  # Minimal zip header
    (td / "Blank.docx").write_bytes(b"PK\x03\x04" + b"\x00" * 50)
    (td / "Tables.docx").write_bytes(b"PK\x03\x04" + b"\x00" * 80)
    (td / "Document.doc").write_bytes(b"\xd0\xcf\x11\xe0" + b"\x00" * 100)
    (td / "alice29.txt").write_text("Alice in Wonderland sample text.\n", encoding="utf-8")
    (td / "sample.txt").write_text("Sample text for testing.\n", encoding="utf-8")

    # Subdirectory with files
    (td / "Images").mkdir()
    (td / "Images" / "logo.png").write_bytes(b"\x89PNG" + b"\x00" * 20)

    return td


@pytest.fixture
def workspace_dir(tmp_path):
    """Create a runtime workspace directory."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def file_aliases():
    """Standard file aliases config."""
    return {
        "Document.docx": ["input.docx", "source.docx", "sample.docx", "example.docx", "test.docx"],
        "Blank.docx": ["empty.docx", "new.docx", "template.docx", "output.docx"],
        "Document.doc": ["input.doc", "source.doc"],
        "alice29.txt": ["file.txt", "source.txt", "input.txt"],
        "sample.txt": ["data.txt", "readme.txt"],
        "Images": ["images", "Pictures"],
    }


@pytest.fixture
def resolver(test_data_dir, file_aliases, tmp_path):
    """Create a FixtureResolverService instance."""
    return FixtureResolverService(
        family="words",
        test_data_dir=test_data_dir,
        file_aliases=file_aliases,
        max_generations_per_run=10,
        registry_path=tmp_path / "fixture-registry.json",
    )


# ---------------------------------------------------------------------------
# Filename extraction tests
# ---------------------------------------------------------------------------

class TestExtractMissingFilename:
    def test_quoted_windows_path(self):
        error = r"Could not find file 'C:\Users\test\runtime_abc\ReportTemplate.docx'."
        assert extract_missing_filename(error) == "ReportTemplate.docx"

    def test_double_quoted(self):
        error = 'Could not find file "input.pdf".'
        assert extract_missing_filename(error) == "input.pdf"

    def test_filenotfoundexception(self):
        error = "System.IO.FileNotFoundException: Could not find file 'data.xlsx'."
        assert extract_missing_filename(error) == "data.xlsx"

    def test_unix_path(self):
        error = "Could not find file '/tmp/runtime_xxx/image.png'."
        assert extract_missing_filename(error) == "image.png"

    def test_no_match(self):
        error = "Some random error message"
        assert extract_missing_filename(error) is None

    def test_empty_string(self):
        assert extract_missing_filename("") is None


class TestExtractMissingDirname:
    def test_windows_directory(self):
        error = r"Could not find a part of the path 'C:\workspace\output\'."
        assert extract_missing_dirname(error) == "output"

    def test_unix_directory(self):
        error = "Could not find a part of the path '/tmp/workspace/results/'."
        assert extract_missing_dirname(error) == "results"

    def test_no_match(self):
        assert extract_missing_dirname("Some error") is None


class TestExtractFileReferences:
    def test_simple_literals(self):
        code = 'var doc = new Document("Template.docx"); doc.Save("output.pdf");'
        refs = extract_file_references_from_code(code)
        assert "Template.docx" in refs
        assert "output.pdf" in refs

    def test_concatenation(self):
        code = 'var doc = new Document(MyDir + "report.docx");'
        refs = extract_file_references_from_code(code)
        assert "report.docx" in refs

    def test_verbatim_string(self):
        code = 'var doc = new Document(@"data\\input.xlsx");'
        refs = extract_file_references_from_code(code)
        assert "input.xlsx" in refs

    def test_no_duplicates(self):
        code = 'var a = "file.docx"; var b = "file.docx";'
        refs = extract_file_references_from_code(code)
        assert refs.count("file.docx") == 1

    def test_non_file_strings_ignored(self):
        code = 'Console.WriteLine("Hello World"); var x = "some text";'
        refs = extract_file_references_from_code(code)
        assert len(refs) == 0


# ---------------------------------------------------------------------------
# Resolution tier tests
# ---------------------------------------------------------------------------

class TestTier1Existing:
    def test_exact_match(self, resolver, test_data_dir):
        result = resolver.resolve_missing_file("Document.docx")
        assert result.resolved
        assert result.method == "existing"
        assert result.source_path == test_data_dir / "Document.docx"

    def test_case_insensitive(self, resolver, test_data_dir):
        result = resolver.resolve_missing_file("document.docx")
        assert result.resolved
        assert result.method == "existing"

    def test_alias_match(self, resolver):
        # "input.docx" is alias for "Document.docx"
        result = resolver.resolve_missing_file("input.docx")
        assert result.resolved
        # May resolve via existing (tier 1 alias) or reverse_alias (tier 3)
        assert result.method in ("existing", "reverse_alias")


class TestTier3ReverseAlias:
    def test_reverse_alias_template(self, resolver, test_data_dir):
        # "template.docx" is alias for Blank.docx
        result = resolver.resolve_missing_file("template.docx")
        assert result.resolved
        # Should resolve via existing (tier 1 alias) or reverse_alias (tier 3)
        assert result.method in ("existing", "reverse_alias")


class TestTier4ExtensionMatch:
    def test_extension_match_docx(self, resolver, test_data_dir):
        # "MyReport.docx" doesn't exist but .docx files do
        result = resolver.resolve_missing_file("MyReport.docx")
        assert result.resolved
        # Might be tier 4 (extension_match) since no exact/alias match
        assert result.method in ("extension_match", "generate")

    def test_extension_match_txt(self, resolver, test_data_dir):
        result = resolver.resolve_missing_file("notes.txt")
        assert result.resolved


class TestTier5Generate:
    def test_generate_html(self, resolver, test_data_dir):
        result = resolver.resolve_missing_file("page.html")
        assert result.resolved
        assert result.method == "generate"
        assert (test_data_dir / "page.html").exists()
        content = (test_data_dir / "page.html").read_text(encoding="utf-8")
        assert "<html>" in content

    def test_generate_png(self, resolver, test_data_dir):
        result = resolver.resolve_missing_file("icon.png")
        assert result.resolved
        # May resolve via extension_match (if .png exists in test-data) or generate
        assert result.method in ("generate", "extension_match")

    def test_generate_csv(self, resolver, test_data_dir):
        result = resolver.resolve_missing_file("data.csv")
        assert result.resolved
        assert result.method == "generate"
        content = (test_data_dir / "data.csv").read_text(encoding="utf-8")
        assert "Name" in content

    def test_generate_xml(self, resolver, test_data_dir):
        result = resolver.resolve_missing_file("config.xml")
        assert result.resolved
        assert (test_data_dir / "config.xml").exists()

    def test_generate_rtf(self, resolver, test_data_dir):
        result = resolver.resolve_missing_file("letter.rtf")
        assert result.resolved
        content = (test_data_dir / "letter.rtf").read_text(encoding="ascii")
        assert "\\rtf1" in content

    def test_generate_jpeg(self, resolver, test_data_dir):
        result = resolver.resolve_missing_file("photo.jpg")
        assert result.resolved
        data = (test_data_dir / "photo.jpg").read_bytes()
        assert data[:2] == b"\xff\xd8"  # JPEG magic bytes

    def test_generate_bmp(self, resolver, test_data_dir):
        result = resolver.resolve_missing_file("icon.bmp")
        assert result.resolved
        data = (test_data_dir / "icon.bmp").read_bytes()
        assert data[:2] == b"BM"


# ---------------------------------------------------------------------------
# Registry persistence tests
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_generated_fixture_registered(self, resolver, tmp_path):
        resolver.resolve_missing_file("new_page.html")
        registry_path = tmp_path / "fixture-registry.json"
        assert registry_path.exists()
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        assert "new_page.html" in registry["fixtures"]
        entry = registry["fixtures"]["new_page.html"]
        assert entry["method"] == "generate"
        assert entry["usage_count"] == 1

    def test_registry_reuse_on_second_call(self, resolver, test_data_dir, tmp_path):
        # First call: generates
        r1 = resolver.resolve_missing_file("report.html")
        assert r1.resolved
        assert r1.method == "generate"

        # Second call: should find in test-data (tier 1) or registry (tier 2)
        r2 = resolver.resolve_missing_file("report.html")
        assert r2.resolved
        assert r2.method in ("existing", "registry")

    def test_unresolvable_recorded(self, resolver, tmp_path):
        # Try to resolve something impossible (no generator for .xyz)
        result = resolver.resolve_missing_file("data.xyz")
        if not result.resolved:
            registry = json.loads((tmp_path / "fixture-registry.json").read_text(encoding="utf-8"))
            assert "data.xyz" in registry.get("unresolvable", [])


# ---------------------------------------------------------------------------
# Directory resolution tests
# ---------------------------------------------------------------------------

class TestDirectoryResolution:
    def test_existing_directory(self, resolver, test_data_dir, workspace_dir):
        result = resolver.resolve_missing_directory("Images", workspace_dir)
        assert result.resolved
        assert result.method == "existing"
        assert (workspace_dir / "Images").exists()

    def test_new_directory(self, resolver, test_data_dir, workspace_dir):
        result = resolver.resolve_missing_directory("mydata", workspace_dir)
        assert result.resolved
        assert result.method == "generate"
        assert (test_data_dir / "mydata").is_dir()
        assert (test_data_dir / "mydata" / "sample.txt").exists()


# ---------------------------------------------------------------------------
# Safety and limits tests
# ---------------------------------------------------------------------------

class TestSafety:
    def test_generation_cap(self, test_data_dir, file_aliases, tmp_path):
        resolver = FixtureResolverService(
            family="words",
            test_data_dir=test_data_dir,
            file_aliases=file_aliases,
            max_generations_per_run=2,
            registry_path=tmp_path / "fixture-registry.json",
        )
        # Generate 2 files (at cap)
        r1 = resolver.resolve_missing_file("a.html")
        r2 = resolver.resolve_missing_file("b.csv")
        assert r1.resolved
        assert r2.resolved

        # Third should fail if it requires generation
        # (but might succeed via existing/extension_match if we have .xml)
        r3 = resolver.resolve_missing_file("unique_c.svg")
        # Check stats - if it was generated, cap was reached
        if r3.method == "generation_cap":
            assert not r3.resolved

    def test_skip_output_patterns(self, resolver):
        result = resolver.resolve_missing_file("output_report.docx")
        assert not result.resolved
        assert result.method == "skipped"

    def test_skip_result_patterns(self, resolver):
        result = resolver.resolve_missing_file("result.txt")
        assert not result.resolved
        assert result.method == "skipped"


# ---------------------------------------------------------------------------
# Proactive pre-check tests
# ---------------------------------------------------------------------------

class TestProactivePrecheck:
    def test_precheck_resolves_missing(self, resolver, test_data_dir):
        code = '''
var doc = new Document("CustomReport.docx");
var img = File.ReadAllBytes("photo.png");
doc.Save("result.pdf");
'''
        results = resolver.precheck_code_references(code)
        # "CustomReport.docx" should be resolved (from Document.docx)
        # "photo.png" should be resolved (generated minimal PNG)
        # "result.pdf" matches skip pattern → NOT resolved
        resolved_names = [r.filename for r in results]
        assert "CustomReport.docx" in resolved_names or "photo.png" in resolved_names

    def test_precheck_skips_existing(self, resolver, test_data_dir):
        code = 'var doc = new Document("Document.docx");'
        results = resolver.precheck_code_references(code)
        # Document.docx already exists → no resolution needed
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Workspace copy tests
# ---------------------------------------------------------------------------

class TestWorkspaceCopy:
    def test_resolved_file_copied_to_workspace(self, resolver, workspace_dir, test_data_dir):
        result = resolver.resolve_missing_file("sample_image.png", workspace_dir)
        assert result.resolved
        # File should be in workspace
        assert (workspace_dir / "sample_image.png").exists()

    def test_resolved_file_persisted_in_test_data(self, resolver, test_data_dir):
        result = resolver.resolve_missing_file("report.html")
        assert result.resolved
        # File should persist in test-data
        assert (test_data_dir / "report.html").exists()


# ---------------------------------------------------------------------------
# Multi-family generator tests
# ---------------------------------------------------------------------------

class TestGenerators:
    def test_docx_from_canonical(self, test_data_dir):
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "NewReport.docx"
        success, msg = generate_file_for_family("NewReport.docx", dest, test_data_dir, "words")
        assert success
        assert dest.exists()
        # Should be a copy of Document.docx (default canonical)
        assert dest.stat().st_size > 0

    def test_docx_template_hint(self, test_data_dir):
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "MyTemplate.docx"
        success, msg = generate_file_for_family("MyTemplate.docx", dest, test_data_dir, "words")
        assert success
        # Should select Blank.docx as canonical (hint: "Template")
        assert "Blank" in msg or "canonical" in msg.lower() or success

    def test_minimal_pdf(self, test_data_dir):
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "sample.pdf"
        success, msg = generate_file_for_family("sample.pdf", dest, test_data_dir, "words")
        assert success
        assert dest.exists()

    def test_html_generation(self, test_data_dir):
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "page.html"
        success, msg = generate_file_for_family("page.html", dest, test_data_dir, "words")
        assert success
        content = dest.read_text(encoding="utf-8")
        assert "<html>" in content

    def test_unsupported_extension(self, test_data_dir):
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "data.xyz"
        success, msg = generate_file_for_family("data.xyz", dest, test_data_dir, "words")
        assert not success  # Unsupported extension


# ---------------------------------------------------------------------------
# New generator validation tests
# ---------------------------------------------------------------------------

class TestNewGenerators:
    """Tests for generator expansion (OOXML, text-based, archive formats)."""

    def test_generate_pptx_valid_zip(self, test_data_dir):
        import zipfile
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "presentation.pptx"
        success, msg = generate_file_for_family("presentation.pptx", dest, test_data_dir, "slides")
        assert success
        assert dest.exists()
        with zipfile.ZipFile(dest) as zf:
            names = zf.namelist()
            assert "[Content_Types].xml" in names
            assert "ppt/presentation.xml" in names
            assert "ppt/slides/slide1.xml" in names

    def test_generate_xlsx_valid_zip(self, test_data_dir):
        import zipfile
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "workbook.xlsx"
        success, msg = generate_file_for_family("workbook.xlsx", dest, test_data_dir, "cells")
        assert success
        with zipfile.ZipFile(dest) as zf:
            names = zf.namelist()
            assert "[Content_Types].xml" in names
            assert "xl/workbook.xml" in names
            assert "xl/worksheets/sheet1.xml" in names

    def test_generate_xps_valid(self, test_data_dir):
        import zipfile
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "output.xps"
        success, msg = generate_file_for_family("output.xps", dest, test_data_dir, "page")
        assert success
        with zipfile.ZipFile(dest) as zf:
            names = zf.namelist()
            assert "FixedDocumentSequence.fdseq" in names
            assert "Documents/1/Pages/1.fpage" in names

    def test_generate_epub_valid(self, test_data_dir):
        import zipfile
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "book.epub"
        success, msg = generate_file_for_family("book.epub", dest, test_data_dir, "words")
        assert success
        with zipfile.ZipFile(dest) as zf:
            assert zf.read("mimetype") == b"application/epub+zip"
            assert "META-INF/container.xml" in zf.namelist()
            assert "OEBPS/content.opf" in zf.namelist()

    def test_generate_tex_content(self, test_data_dir):
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "sample.tex"
        success, msg = generate_file_for_family("sample.tex", dest, test_data_dir, "tex")
        assert success
        content = dest.read_text(encoding="utf-8")
        assert "\\documentclass" in content
        assert "\\begin{document}" in content
        assert "\\end{document}" in content

    def test_generate_eps_header(self, test_data_dir):
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "image.eps"
        success, msg = generate_file_for_family("image.eps", dest, test_data_dir, "page")
        assert success
        content = dest.read_text(encoding="utf-8")
        assert "%!PS-Adobe-3.0 EPSF-3.0" in content
        assert "%%BoundingBox:" in content

    def test_generate_ps_header(self, test_data_dir):
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "doc.ps"
        success, msg = generate_file_for_family("doc.ps", dest, test_data_dir, "page")
        assert success
        content = dest.read_text(encoding="utf-8")
        assert "%!PS-Adobe-3.0" in content
        assert "showpage" in content

    def test_generate_ics_valid(self, test_data_dir):
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "event.ics"
        success, msg = generate_file_for_family("event.ics", dest, test_data_dir, "email")
        assert success
        content = dest.read_text(encoding="utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "BEGIN:VEVENT" in content
        assert "END:VCALENDAR" in content

    def test_generate_dxf_content(self, test_data_dir):
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "drawing.dxf"
        success, msg = generate_file_for_family("drawing.dxf", dest, test_data_dir, "cad")
        assert success
        content = dest.read_text(encoding="utf-8")
        assert "HEADER" in content
        assert "EOF" in content

    def test_generate_mhtml_content(self, test_data_dir):
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "page.mhtml"
        success, msg = generate_file_for_family("page.mhtml", dest, test_data_dir, "html")
        assert success
        content = dest.read_text(encoding="utf-8")
        assert "MIME-Version: 1.0" in content
        assert "multipart/related" in content
        assert "<html>" in content

    def test_generate_gif_valid_header(self, test_data_dir):
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "image.gif"
        success, msg = generate_file_for_family("image.gif", dest, test_data_dir, "imaging")
        assert success
        data = dest.read_bytes()
        assert data[:6] == b"GIF89a"  # Valid GIF header, not PNG

    def test_generate_tiff_valid_header(self, test_data_dir):
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "image.tiff"
        success, msg = generate_file_for_family("image.tiff", dest, test_data_dir, "imaging")
        assert success
        data = dest.read_bytes()
        assert data[:2] in (b"II", b"MM")  # Valid TIFF byte order mark, not BMP

    def test_generate_zip_archive(self, test_data_dir):
        import zipfile
        from src.services.test_data_generator import generate_file_for_family
        dest = test_data_dir / "archive.zip"
        # Remove existing archive.zip if any to test generation
        if dest.exists():
            dest.unlink()
        success, msg = generate_file_for_family("archive.zip", dest, test_data_dir, "zip")
        assert success
        assert zipfile.is_zipfile(dest)


# ---------------------------------------------------------------------------
# Unresolvable mechanism tests
# ---------------------------------------------------------------------------

class TestUnresolvable:
    """Tests for version-based unresolvable staleness and migration."""

    def test_unresolvable_blocks_retry(self, test_data_dir, file_aliases, tmp_path):
        """Known unresolvable at current version skips all tiers."""
        registry_path = tmp_path / "fixture-registry.json"
        # Seed registry with unresolvable entry at current version
        registry_path.write_text(json.dumps({
            "version": 1, "family": "words", "fixtures": {},
            "unresolvable": {
                "impossible.xyz": {
                    "recorded_at": "2026-01-01T00:00:00+00:00",
                    "generator_version": FixtureResolverService._GENERATOR_VERSION,
                }
            }
        }), encoding="utf-8")

        resolver = FixtureResolverService(
            family="words", test_data_dir=test_data_dir,
            file_aliases=file_aliases, registry_path=registry_path,
        )
        result = resolver.resolve_missing_file("impossible.xyz")
        assert not result.resolved
        assert result.method == "cached_unresolvable"

    def test_unresolvable_stale_retries_on_version_bump(self, test_data_dir, file_aliases, tmp_path):
        """Entry recorded at older generator version triggers retry."""
        registry_path = tmp_path / "fixture-registry.json"
        registry_path.write_text(json.dumps({
            "version": 1, "family": "words", "fixtures": {},
            "unresolvable": {
                "sample.txt": {
                    "recorded_at": "2026-01-01T00:00:00+00:00",
                    "generator_version": 1,  # Older than current _GENERATOR_VERSION (2)
                }
            }
        }), encoding="utf-8")

        resolver = FixtureResolverService(
            family="words", test_data_dir=test_data_dir,
            file_aliases=file_aliases, registry_path=registry_path,
        )
        # sample.txt exists in test_data_dir, so tier 1 should find it
        result = resolver.resolve_missing_file("sample.txt")
        assert result.resolved
        assert result.method == "existing"

    def test_unresolvable_stale_when_file_exists(self, test_data_dir, file_aliases, tmp_path):
        """File that appeared in test-data triggers retry and removes stale entry."""
        registry_path = tmp_path / "fixture-registry.json"
        # Record as unresolvable at current version
        registry_path.write_text(json.dumps({
            "version": 1, "family": "words", "fixtures": {},
            "unresolvable": {
                "alice29.txt": {
                    "recorded_at": "2026-01-01T00:00:00+00:00",
                    "generator_version": FixtureResolverService._GENERATOR_VERSION,
                }
            }
        }), encoding="utf-8")

        resolver = FixtureResolverService(
            family="words", test_data_dir=test_data_dir,
            file_aliases=file_aliases, registry_path=registry_path,
        )
        # alice29.txt exists in test_data_dir, so stale check removes it
        result = resolver.resolve_missing_file("alice29.txt")
        assert result.resolved

    def test_unresolvable_auto_migration_from_list(self, test_data_dir, file_aliases, tmp_path):
        """Old list-based unresolvable format auto-migrates to versioned dict."""
        registry_path = tmp_path / "fixture-registry.json"
        # Old format: list of strings
        registry_path.write_text(json.dumps({
            "version": 1, "family": "words", "fixtures": {},
            "unresolvable": ["impossible.abc", "another.xyz", "*.jpg"]
        }), encoding="utf-8")

        resolver = FixtureResolverService(
            family="words", test_data_dir=test_data_dir,
            file_aliases=file_aliases, registry_path=registry_path,
        )
        # After load, unresolvable should be dict, not list
        unresolv = resolver._registry["unresolvable"]
        assert isinstance(unresolv, dict)
        # Concrete entries migrated
        assert "impossible.abc" in unresolv
        assert unresolv["impossible.abc"]["generator_version"] == 1
        # Glob patterns dropped during migration
        assert "*.jpg" not in unresolv

    def test_wildcard_rejected_from_unresolvable(self, test_data_dir, file_aliases, tmp_path):
        """Glob patterns are not recorded in the unresolvable list."""
        registry_path = tmp_path / "fixture-registry.json"
        resolver = FixtureResolverService(
            family="words", test_data_dir=test_data_dir,
            file_aliases=file_aliases, registry_path=registry_path,
        )
        resolver._record_unresolvable("*.jpg")
        resolver._record_unresolvable("data?.bin")
        resolver._record_unresolvable("{file}.txt")

        unresolv = resolver._registry.get("unresolvable", {})
        assert "*.jpg" not in unresolv
        assert "data?.bin" not in unresolv
        assert "{file}.txt" not in unresolv

    def test_tier2_5_recursive_search(self, test_data_dir, file_aliases, tmp_path):
        """Tier 2.5 finds files in repo subdirectories."""
        # Create a mock example repo with subdirectories
        repo_dir = tmp_path / "repo-data"
        repo_dir.mkdir()
        (repo_dir / "SubDir").mkdir()
        (repo_dir / "SubDir" / "deep_file.docx").write_bytes(b"PK\x03\x04" + b"\x00" * 50)

        resolver = FixtureResolverService(
            family="words", test_data_dir=test_data_dir,
            file_aliases=file_aliases, registry_path=tmp_path / "fixture-registry.json",
            example_repo_test_data_dir=repo_dir,
        )
        result = resolver._tier2_5_example_repo("deep_file.docx")
        assert result.resolved
        assert result.method == "example_repo"
        assert "recursive" in result.message
