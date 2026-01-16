#!/usr/bin/env python3
"""Create encrypted archive samples with known password for testing."""

import zipfile
import os
from pathlib import Path

def create_encrypted_zip(output_path: str, password: str):
    """Create a simple encrypted ZIP file with known password."""
    test_data_dir = Path("test-data/zip")
    test_data_dir.mkdir(parents=True, exist_ok=True)

    # Create test content file if it doesn't exist
    test_file = test_data_dir / "test_content.txt"
    if not test_file.exists():
        test_file.write_text("This is test content for encrypted archives.\n")

    # Create encrypted ZIP
    zip_path = test_data_dir / output_path
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(test_file, arcname="test_content.txt")
        zipf.setpassword(password.encode('utf-8'))

    print(f"Created encrypted ZIP: {zip_path} with password: {password}")

if __name__ == "__main__":
    # Create encrypted.zip with password "password"
    create_encrypted_zip("encrypted_password.zip", "password")

    print("✅ Encrypted sample files created!")
    print("Password for all files: 'password'")
