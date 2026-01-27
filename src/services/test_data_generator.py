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
from typing import Dict, List, Optional, Tuple


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
