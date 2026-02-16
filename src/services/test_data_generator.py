"""
Test Data Generator Service

Generates deterministic test data files for runtime validation.
All generated files use fixed timestamps, sorted file lists, and store compression
to ensure reproducibility (same input → same SHA256).

Key Features:
- Fixed timestamps: os.utime(path, (0, 0)) for all files
- Store compression: zip -0 (no compression variance)
- Sorted file lists: deterministic archive ordering
- Embedded content: Canterbury Corpus snippets (no random data)
"""

import base64
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Canterbury Corpus snippets for compression testing
CANTERBURY_CORPUS = {
    "alice29.txt": """ALICE'S ADVENTURES IN WONDERLAND

Lewis Carroll

CHAPTER I.  Down the Rabbit-Hole

Alice was beginning to get very tired of sitting by her sister
on the bank, and of having nothing to do:  once or twice she had
peeped into the book her sister was reading, but it had no
pictures or conversations in it, 'and what is the use of a book,'
thought Alice 'without pictures or conversation?'

So she was considering in her own mind (as well as she could,
for the hot day made her feel very sleepy and stupid), whether
the pleasure of making a daisy-chain would be worth the trouble
of getting up and picking the daisies, when suddenly a White
Rabbit with pink eyes ran close by her.
""",
    "asyoulik.txt": """AS YOU LIKE IT

by William Shakespeare

DRAMATIS PERSONAE

DUKE SENIOR living in banishment.
DUKE FREDERICK  his brother, an usurper of his dominions.

AMIENS  |
        |  lords attending on the banished duke.
JAQUES  |

LE BEAU  a courtier attending upon Frederick.

CHARLES  wrestler to Frederick.

OLIVER  |
        |
JAQUES  |  sons of Sir Rowland de Boys.
        |
ORLANDO |
""",
    "plrabn12.txt": """Paradise Lost by John Milton

Book I

Of Man's first disobedience, and the fruit
Of that forbidden tree whose mortal taste
Brought death into the World, and all our woe,
With loss of Eden, till one greater Man
Restore us, and regain the blissful Seat,
Sing, Heavenly Muse, that, on the secret top
Of Oreb, or of Sinai, didst inspire
That shepherd who first taught the chosen seed
In the beginning how the Heav'ns and Earth
Rose out of Chaos: or if Sion hill
Delight thee more, and Siloa's brook that flow'd
Fast by the oracle of God, I thence
Invoke thy aid to my adventurous song,
That with no middle flight intends to soar
Above th' Aonian mount, while it pursues
Things unattempted yet in prose or rhyme.
""",
    "lcet10.txt": """The Importance of Being Earnest
by Oscar Wilde

THE PERSONS IN THE PLAY

John Worthing, J.P.
Algernon Moncrieff
Rev. Canon Chasuble, D.D.
Merriman, Butler
Lane, Manservant
Lady Bracknell
Hon. Gwendolen Fairfax
Cecily Cardew
Miss Prism, Governess

THE SCENES OF THE PLAY

ACT I.  Algernon Moncrieff's Flat in Half-Moon Street, W.
ACT II. The Garden at the Manor House, Woolton.
ACT III.  Drawing-Room at the Manor House, Woolton.
""",
}


def _fix_timestamp(path: Path) -> None:
    """Set file modification time to 1980-01-01 00:00:00 for determinism.

    Note: Using 1980 instead of epoch (1970) because ZIP format doesn't support
    timestamps before 1980. This is still deterministic."""
    # 1980-01-01 00:00:00 UTC = 315532800 seconds since epoch
    timestamp = 315532800
    os.utime(path, (timestamp, timestamp))


def _check_tool_available(tool: str) -> bool:
    """Check if a CLI tool is available in PATH."""
    return shutil.which(tool) is not None


def generate_corpus_text(filename: str, destination: Path) -> bool:
    """
    Generate Canterbury Corpus text file with fixed content.

    Args:
        filename: Name of the corpus file (alice29.txt, asyoulik.txt, etc.)
        destination: Full path to output file

    Returns:
        True if successful, False otherwise
    """
    try:
        content = CANTERBURY_CORPUS.get(filename)
        if not content:
            # Fallback for unknown files
            content = f"Sample text content for {filename}\n" * 10

        destination.write_text(content, encoding="utf-8")
        _fix_timestamp(destination)
        return True
    except Exception as e:
        print(f"Failed to generate {filename}: {e}")
        return False


def generate_placeholder_text(destination: Path, content: str = "Sample text content\n") -> bool:
    """
    Generate simple placeholder text file.

    Args:
        destination: Full path to output file
        content: Text content to write

    Returns:
        True if successful, False otherwise
    """
    try:
        destination.write_text(content * 10, encoding="utf-8")
        _fix_timestamp(destination)
        return True
    except Exception as e:
        print(f"Failed to generate placeholder text: {e}")
        return False


def generate_empty_zip(destination: Path, use_tool: bool = False) -> bool:
    """
    Generate empty ZIP archive with store compression (deterministic).

    Args:
        destination: Full path to output ZIP file
        use_tool: If True, try zip CLI tool first; if False, use Python zipfile

    Returns:
        True if successful, False otherwise
    """
    try:
        # Use Python zipfile module with store compression (more reliable on Windows)
        import zipfile

        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_file = destination.parent / "_temp_placeholder.txt"
        temp_file.write_text("placeholder\n")
        _fix_timestamp(temp_file)

        with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_STORED) as zf:
            zf.write(temp_file, arcname="placeholder.txt")

        temp_file.unlink()
        _fix_timestamp(destination)
        return True

    except Exception as e:
        print(f"Failed to generate ZIP {destination.name}: {e}")
        return False


def generate_password_protected_zip(destination: Path, password: str = "p@s$") -> bool:
    """
    Generate password-protected ZIP archive.

    Note: Python's standard zipfile module cannot create encrypted ZIPs.
    This function tries pyminizip if available, otherwise creates unencrypted ZIP.

    Args:
        destination: Full path to output ZIP file
        password: Password for encryption

    Returns:
        True if successful, False otherwise
    """
    try:
        # Try pyminizip if available
        try:
            import pyminizip

            destination.parent.mkdir(parents=True, exist_ok=True)
            temp_file = destination.parent / "_temp_placeholder.txt"
            temp_file.write_text("placeholder\n")
            _fix_timestamp(temp_file)

            # pyminizip.compress(src, src_prefix, dst, password, compress_level)
            pyminizip.compress(
                str(temp_file),
                "placeholder.txt",
                str(destination),
                password,
                0  # compress level 0 = store (no compression)
            )

            temp_file.unlink()
            _fix_timestamp(destination)
            return True

        except ImportError:
            # Fallback: Create unencrypted ZIP as placeholder
            # (better than completely failing)
            print(f"Warning: pyminizip not available, creating unencrypted {destination.name}")
            return generate_empty_zip(destination)

    except Exception as e:
        print(f"Failed to generate password-protected ZIP {destination.name}: {e}")
        return False


def generate_nested_zip(destination: Path) -> bool:
    """
    Generate nested ZIP archive (outer.zip containing inner.zip).

    Args:
        destination: Full path to output ZIP file (outer.zip)

    Returns:
        True if successful, False otherwise
    """
    try:
        import zipfile

        destination.parent.mkdir(parents=True, exist_ok=True)

        # Create inner.zip first
        inner_zip = destination.parent / "inner.zip"
        if not generate_empty_zip(inner_zip):
            return False

        # Create outer.zip containing inner.zip
        with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_STORED) as zf:
            zf.write(inner_zip, arcname="inner.zip")

        inner_zip.unlink()
        _fix_timestamp(destination)
        return True

    except Exception as e:
        print(f"Failed to generate nested ZIP {destination.name}: {e}")
        return False


def generate_gzip(destination: Path, source_content: str = "Sample content for gzip compression\n") -> bool:
    """
    Generate gzip archive with no timestamp (deterministic).

    Args:
        destination: Full path to output .gz file
        source_content: Content to compress

    Returns:
        True if successful, False otherwise
    """
    try:
        # Use Python gzip module
        import gzip

        destination.parent.mkdir(parents=True, exist_ok=True)

        # Create gzip file with explicit no-timestamp mode
        # Write directly without mtime parameter for compatibility
        with gzip.GzipFile(filename=str(destination), mode='wb', mtime=0) as f:
            f.write(source_content.encode('utf-8'))

        _fix_timestamp(destination)
        return True

    except Exception as e:
        print(f"Failed to generate gzip {destination.name}: {e}")
        return False


def generate_7z_archive(destination: Path) -> bool:
    """
    Generate 7z archive using py7zr (pure Python) or 7z CLI.

    Task 2: Deterministically generate archive.7z even without 7z CLI.

    Args:
        destination: Full path to output .7z file

    Returns:
        True if successful, False otherwise
    """
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Try py7zr first (pure Python, no CLI dependency)
        try:
            import py7zr

            temp_file = destination.parent / "_temp_placeholder.txt"
            temp_file.write_text("placeholder\n")
            _fix_timestamp(temp_file)

            # Create 7z archive with LZMA2 compression (deterministic)
            with py7zr.SevenZipFile(destination, 'w') as archive:
                archive.write(temp_file, arcname="placeholder.txt")

            temp_file.unlink()
            _fix_timestamp(destination)
            print(f"Generated {destination.name} using py7zr")
            return True

        except ImportError:
            # Fallback to 7z CLI
            if _check_tool_available("7z"):
                temp_file = destination.parent / "_temp_placeholder.txt"
                temp_file.write_text("placeholder\n")
                _fix_timestamp(temp_file)

                # 7z a -mx0 (store compression for determinism)
                result = subprocess.run(
                    ["7z", "a", "-mx0", str(destination), str(temp_file)],
                    capture_output=True,
                    text=True,
                    cwd=destination.parent,
                )

                temp_file.unlink()

                if result.returncode != 0:
                    print(f"7z command failed: {result.stderr}")
                    return False

                _fix_timestamp(destination)
                return True
            else:
                print(f"Warning: Neither py7zr nor 7z CLI available, skipping {destination.name}")
                return False

    except Exception as e:
        print(f"Failed to generate 7z {destination.name}: {e}")
        return False


def generate_sample_directory(destination: Path) -> bool:
    """
    Generate sample_dir with nested structure for directory operations testing.

    Structure:
        sample_dir/
        ├── alice29.txt (Canterbury Corpus)
        ├── data.txt
        ├── file1.txt
        ├── file2.txt
        ├── readme.txt
        ├── image.png (1x1 transparent PNG)
        └── subfolder/
            └── nested.txt

    Args:
        destination: Full path to output directory

    Returns:
        True if successful, False otherwise
    """
    try:
        destination.mkdir(parents=True, exist_ok=True)

        # Create root files
        (destination / "alice29.txt").write_text(CANTERBURY_CORPUS["alice29.txt"])
        (destination / "data.txt").write_text("Data file content\n" * 5)
        (destination / "file1.txt").write_text("File 1 content\n")
        (destination / "file2.txt").write_text("File 2 content\n")
        (destination / "readme.txt").write_text("README\nSample directory for testing\n")

        # Create 1x1 transparent PNG (smallest valid PNG)
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        (destination / "image.png").write_bytes(png_data)

        # Create subdirectory
        subfolder = destination / "subfolder"
        subfolder.mkdir(exist_ok=True)
        (subfolder / "nested.txt").write_text("Nested file content\n")

        # Fix timestamps for all files (recursive)
        for file in destination.rglob("*"):
            if file.is_file():
                _fix_timestamp(file)

        # Fix directory timestamps
        _fix_timestamp(subfolder)
        _fix_timestamp(destination)

        return True

    except Exception as e:
        print(f"Failed to generate sample_dir: {e}")
        return False


def generate_file(filename: str, destination_dir: Path, verbose: bool = False) -> Tuple[bool, str]:
    """
    Generate a single test data file based on filename and type.

    Args:
        filename: Name of file to generate (sample.zip, alice29.txt, etc.)
        destination_dir: Directory to create file in
        verbose: Print verbose output

    Returns:
        Tuple of (success: bool, message: str)
    """
    destination = destination_dir / filename

    if verbose:
        print(f"Generating {filename}...")

    # Determine generation strategy based on filename
    if filename == "sample.zip" or filename == "archive.zip" or filename == "flatten.zip":
        success = generate_empty_zip(destination)
        return (success, f"Generated {filename}" if success else f"Failed to generate {filename}")

    elif filename == "outer.zip":
        success = generate_nested_zip(destination)
        return (success, f"Generated nested {filename}" if success else f"Failed to generate {filename}")

    elif filename == "different_password.zip" or filename == "encrypted_password.zip":
        success = generate_password_protected_zip(destination, password="p@s$")
        return (success, f"Generated password-protected {filename}" if success else f"Failed to generate {filename}")

    elif filename == "archive.7z":
        success = generate_7z_archive(destination)
        return (success, f"Generated {filename}" if success else f"7z tool not available, skipped {filename}")

    elif filename == "archive.gz" or filename == "sample.gz":
        success = generate_gzip(destination)
        return (success, f"Generated {filename}" if success else f"Failed to generate {filename}")

    elif filename == "alice29.txt" or filename == "asyoulik.txt" or filename == "plrabn12.txt" or filename == "lcet10.txt":
        success = generate_corpus_text(filename, destination)
        return (success, f"Generated corpus {filename}" if success else f"Failed to generate {filename}")

    elif filename == "sample.txt":
        success = generate_placeholder_text(destination, content="This is a sample text file for testing.\n")
        return (success, f"Generated {filename}" if success else f"Failed to generate {filename}")

    elif filename == "sample_dir":
        success = generate_sample_directory(destination)
        return (success, f"Generated directory {filename}/" if success else f"Failed to generate {filename}/")

    elif filename.startswith("data") and filename.endswith(".bin"):
        # Binary data files for 7z per-entry encryption examples
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            content = f"Binary test data for {filename}\n".encode() * 100
            destination.write_bytes(content)
            _fix_timestamp(destination)
            return (True, f"Generated binary {filename}")
        except Exception as e:
            return (False, f"Failed to generate {filename}: {e}")

    elif filename == "encrypted.rar" or filename == "plrabn12.rar":
        # RAR files cannot be generated locally - backfill only
        return (False, f"RAR file {filename} requires backfill (cannot generate locally)")

    else:
        # Unknown file type - generate placeholder text
        success = generate_placeholder_text(destination, content=f"Placeholder for {filename}\n")
        return (success, f"Generated placeholder {filename}" if success else f"Failed to generate {filename}")


def generate_all_zip_family(destination_dir: Path, verbose: bool = False) -> Dict[str, bool]:
    """
    Generate all 17 required test data files for ZIP family.

    Args:
        destination_dir: Directory to create files in (test-data/zip/)
        verbose: Print verbose output

    Returns:
        Dict mapping filename -> success (True/False)
    """
    destination_dir.mkdir(parents=True, exist_ok=True)

    required_files = [
        "sample.zip",
        "archive.zip",
        "outer.zip",
        "flatten.zip",
        "different_password.zip",
        "encrypted_password.zip",
        "encrypted.rar",  # Backfill-only
        "plrabn12.rar",  # Backfill-only
        "archive.7z",
        "archive.gz",
        "sample.gz",
        "alice29.txt",
        "sample.txt",
        "asyoulik.txt",
        "plrabn12.txt",
        "lcet10.txt",
        "sample_dir",
    ]

    results = {}

    for filename in sorted(required_files):  # Sorted for determinism
        success, message = generate_file(filename, destination_dir, verbose=verbose)
        results[filename] = success

        if verbose:
            status = "OK" if success else "FAIL"
            print(f"  [{status}] {message}")

    return results


# ---------------------------------------------------------------------------
# Multi-family file generators (for FixtureResolverService)
# ---------------------------------------------------------------------------

# Minimal valid PNG: 1x1 transparent pixel (67 bytes)
_MINIMAL_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIABQAB"
    "Nl7BcQAAAABJRU5ErkJggg=="
)

# Minimal valid JPEG: 1x1 white pixel
_MINIMAL_JPEG_BYTES = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoH"
    "BwYIDAoMCwsKCwsNCxAODxMOCgsQFBESExoSEhQYGRkaIR8fIhwcJB4c/2wBDAME"
    "AwMEBQQFBQQFBwYFBgcOCggICg4TDhAOEBMUExATExMYFBQUGBQTExoaGhMaJCQk"
    "JCQkJCQkJCQkJCQkJCT/wAARCAABAAEDASIAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACf"
    "/EABQQAQAAAAAAAAAAAAAAAAAAAAD/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/8QAFBEBAAAA"
    "AAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAB//2Q=="
)

# Minimal valid BMP: 1x1 white pixel (58 bytes)
_MINIMAL_BMP_BYTES = (
    b'BM:\x00\x00\x00\x00\x00\x00\x006\x00\x00\x00(\x00\x00\x00'
    b'\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00'
    b'\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\xff\xff\xff\x00'
)

# Hint-based canonical selection for .docx files
_DOCX_HINT_MAP = {
    "template": "Blank.docx",
    "blank": "Blank.docx",
    "empty": "Blank.docx",
    "new": "Blank.docx",
    "table": "Tables.docx",
    "bookmark": "Bookmarks.docx",
    "comment": "Comments.docx",
}


def _select_canonical_docx(filename: str, test_data_dir: Path) -> Optional[Path]:
    """Select the best canonical .docx based on filename hints."""
    name_lower = Path(filename).stem.lower()

    # Check hints
    for hint, canonical in _DOCX_HINT_MAP.items():
        if hint in name_lower:
            candidate = test_data_dir / canonical
            if candidate.exists():
                return candidate

    # Default: Document.docx (richest content) -> Blank.docx (fallback)
    for fallback in ("Document.docx", "Blank.docx"):
        candidate = test_data_dir / fallback
        if candidate.exists():
            return candidate

    # Last resort: any .docx in test-data
    for f in test_data_dir.rglob("*.docx"):
        if f.is_file():
            return f

    return None


def _generate_docx_from_canonical(dest: Path, test_data_dir: Path) -> Tuple[bool, str]:
    """Generate a .docx by copying the best canonical source."""
    canonical = _select_canonical_docx(dest.name, test_data_dir)
    if canonical:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(canonical, dest)
        return (True, f"Generated {dest.name} from canonical {canonical.name}")
    return (False, f"No canonical .docx found in test-data for {dest.name}")


def _generate_doc_from_canonical(dest: Path, test_data_dir: Path) -> Tuple[bool, str]:
    """Generate a .doc by copying canonical source."""
    for name in ("Document.doc", "Blank.doc"):
        candidate = test_data_dir / name
        if candidate.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate, dest)
            return (True, f"Generated {dest.name} from canonical {candidate.name}")
    # Try any .doc
    for f in test_data_dir.rglob("*.doc"):
        if f.is_file() and f.suffix.lower() == ".doc":
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            return (True, f"Generated {dest.name} from {f.name}")
    return (False, f"No canonical .doc found in test-data for {dest.name}")


def _generate_pdf_from_canonical(dest: Path, test_data_dir: Path) -> Tuple[bool, str]:
    """Generate a .pdf by copying canonical source."""
    for f in test_data_dir.rglob("*.pdf"):
        if f.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            return (True, f"Generated {dest.name} from canonical {f.name}")
    # Minimal valid PDF
    minimal_pdf = (
        b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj "
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(minimal_pdf)
    return (True, f"Generated minimal PDF {dest.name}")


def _generate_html(dest: Path) -> Tuple[bool, str]:
    """Generate a minimal valid HTML file."""
    content = (
        "<!DOCTYPE html>\n<html>\n<head><title>Sample</title></head>\n"
        "<body>\n<h1>Sample Document</h1>\n<p>This is a sample HTML document for testing.</p>\n"
        "<table><tr><th>Name</th><th>Value</th></tr>"
        "<tr><td>Item1</td><td>100</td></tr></table>\n"
        "</body>\n</html>\n"
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return (True, f"Generated HTML {dest.name}")


def _generate_text(dest: Path) -> Tuple[bool, str]:
    """Generate a text file with sample content."""
    # Reuse Canterbury corpus snippet
    content = CANTERBURY_CORPUS.get("alice29.txt", "Sample text content for testing.\n")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return (True, f"Generated text {dest.name}")


def _generate_png(dest: Path) -> Tuple[bool, str]:
    """Generate a minimal valid 1x1 PNG."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(_MINIMAL_PNG_BYTES)
    return (True, f"Generated minimal PNG {dest.name}")


def _generate_jpeg(dest: Path) -> Tuple[bool, str]:
    """Generate a minimal valid JPEG."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(_MINIMAL_JPEG_BYTES)
    return (True, f"Generated minimal JPEG {dest.name}")


def _generate_bmp(dest: Path) -> Tuple[bool, str]:
    """Generate a minimal valid 1x1 BMP."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(_MINIMAL_BMP_BYTES)
    return (True, f"Generated minimal BMP {dest.name}")


def _generate_csv(dest: Path) -> Tuple[bool, str]:
    """Generate a minimal CSV file."""
    content = "Name,Value,Category\nItem1,100,A\nItem2,200,B\nItem3,300,C\n"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return (True, f"Generated CSV {dest.name}")


def _generate_xml(dest: Path) -> Tuple[bool, str]:
    """Generate a minimal valid XML file."""
    content = '<?xml version="1.0" encoding="utf-8"?>\n<root>\n  <item id="1">Sample</item>\n  <item id="2">Data</item>\n</root>\n'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return (True, f"Generated XML {dest.name}")


def _generate_rtf(dest: Path) -> Tuple[bool, str]:
    """Generate a minimal valid RTF file."""
    content = r"{\rtf1\ansi{\fonttbl\f0 Calibri;}{\pard Sample RTF document for testing.\par}}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="ascii")
    return (True, f"Generated RTF {dest.name}")


def _generate_odt_from_canonical(dest: Path, test_data_dir: Path) -> Tuple[bool, str]:
    """Generate a .odt by copying canonical source."""
    for f in test_data_dir.rglob("*.odt"):
        if f.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            return (True, f"Generated {dest.name} from canonical {f.name}")
    return (False, f"No canonical .odt found in test-data for {dest.name}")


def _copy_canonical_by_ext(dest: Path, test_data_dir: Path, ext: str) -> Tuple[bool, str]:
    """Copy first available file with matching extension from test-data (recursive)."""
    for f in test_data_dir.rglob(f"*{ext}"):
        if f.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            return (True, f"Generated {dest.name} from canonical {f.name}")
    return (False, f"No canonical {ext} found in test-data for {dest.name}")


# Extension-to-generator dispatch table
_FAMILY_GENERATORS: Dict[str, Any] = {
    # Document formats (copy canonical)
    ".docx": lambda dest, td, _: _generate_docx_from_canonical(dest, td),
    ".doc": lambda dest, td, _: _generate_doc_from_canonical(dest, td),
    ".pdf": lambda dest, td, _: _generate_pdf_from_canonical(dest, td),
    ".odt": lambda dest, td, _: _generate_odt_from_canonical(dest, td),
    # Text formats (generate)
    ".html": lambda dest, td, _: _generate_html(dest),
    ".htm": lambda dest, td, _: _generate_html(dest),
    ".txt": lambda dest, td, _: _generate_text(dest),
    ".csv": lambda dest, td, _: _generate_csv(dest),
    ".xml": lambda dest, td, _: _generate_xml(dest),
    ".rtf": lambda dest, td, _: _generate_rtf(dest),
    # Image formats (minimal valid bytes)
    ".png": lambda dest, td, _: _generate_png(dest),
    ".jpg": lambda dest, td, _: _generate_jpeg(dest),
    ".jpeg": lambda dest, td, _: _generate_jpeg(dest),
    ".bmp": lambda dest, td, _: _generate_bmp(dest),
    ".gif": lambda dest, td, _: _generate_png(dest),  # PNG as fallback for GIF
    ".tiff": lambda dest, td, _: _generate_bmp(dest),  # BMP as fallback for TIFF
    ".tif": lambda dest, td, _: _generate_bmp(dest),
    ".svg": lambda dest, td, _: _generate_svg(dest),
    # Image/design formats (copy from canonical in test-data)
    ".psd": lambda dest, td, _: _copy_canonical_by_ext(dest, td, ".psd"),
    ".psb": lambda dest, td, _: _copy_canonical_by_ext(dest, td, ".psb"),
    ".ai": lambda dest, td, _: _copy_canonical_by_ext(dest, td, ".ai"),
    ".dicom": lambda dest, td, _: _copy_canonical_by_ext(dest, td, ".dicom"),
    ".dcm": lambda dest, td, _: _copy_canonical_by_ext(dest, td, ".dcm"),
    ".djvu": lambda dest, td, _: _copy_canonical_by_ext(dest, td, ".djvu"),
    ".webp": lambda dest, td, _: _copy_canonical_by_ext(dest, td, ".webp"),
    ".emf": lambda dest, td, _: _copy_canonical_by_ext(dest, td, ".emf"),
    ".wmf": lambda dest, td, _: _copy_canonical_by_ext(dest, td, ".wmf"),
    ".dng": lambda dest, td, _: _copy_canonical_by_ext(dest, td, ".dng"),
    ".j2k": lambda dest, td, _: _copy_canonical_by_ext(dest, td, ".j2k"),
    ".jp2": lambda dest, td, _: _copy_canonical_by_ext(dest, td, ".jp2"),
}


def _generate_svg(dest: Path) -> Tuple[bool, str]:
    """Generate a minimal valid SVG file."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>\n',
        encoding="utf-8",
    )
    return (True, f"Generated minimal SVG {dest.name}")


def generate_file_for_family(
    filename: str,
    dest: Path,
    test_data_dir: Path,
    family: str,
) -> Tuple[bool, str]:
    """
    Generate a fixture file for any family, using existing test-data
    as canonical sources when possible.

    Priority:
    1. Extension-specific generator (copy canonical or create minimal valid file)
    2. Copy any same-extension file from test-data
    3. Generate placeholder text

    Args:
        filename: Target filename (e.g. "ReportTemplate.docx")
        dest: Full destination path for the generated file
        test_data_dir: Directory containing existing test data (for canonical sources)
        family: Product family identifier (e.g. "zip", "words")

    Returns:
        (success, message) tuple
    """
    ext = dest.suffix.lower()

    # Try extension-specific generator
    generator = _FAMILY_GENERATORS.get(ext)
    if generator:
        try:
            return generator(dest, test_data_dir, family)
        except Exception as e:
            # Fall through to generic handling
            pass

    # Try copying any same-extension file from test-data
    if ext:
        for f in test_data_dir.rglob(f"*{ext}"):
            if f.is_file():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                return (True, f"Generated {filename} by copying {f.name}")

    # Last resort: placeholder text (only for text-like extensions)
    text_like = {".txt", ".csv", ".xml", ".html", ".htm", ".rtf", ".json", ".md", ".log"}
    if ext in text_like or not ext:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f"Placeholder content for {filename}\n", encoding="utf-8")
        return (True, f"Generated placeholder {filename}")

    return (False, f"Cannot generate {filename}: unsupported extension '{ext}'")


if __name__ == "__main__":
    # CLI interface for testing
    import argparse

    parser = argparse.ArgumentParser(description="Generate deterministic test data files")
    parser.add_argument("--output-dir", default="test-data/zip", help="Output directory")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    results = generate_all_zip_family(output_dir, verbose=args.verbose)

    # Summary
    total = len(results)
    success_count = sum(1 for v in results.values() if v)

    print(f"\nGeneration Summary:")
    print(f"  Total: {total}")
    print(f"  Success: {success_count}")
    print(f"  Failed: {total - success_count}")

    if success_count < total:
        print(f"\nFailed files:")
        for filename, success in results.items():
            if not success:
                print(f"  - {filename}")
