"""
Create sample.zip and manifest.json for ZIP runtime validation tests.
"""
import json
import hashlib
import zipfile
from pathlib import Path

def compute_sha256(file_path):
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def get_file_size(file_path):
    """Get file size in bytes."""
    return Path(file_path).stat().st_size

# Create sample.zip
zip_path = Path(__file__).parent / 'sample.zip'
sample_dir = Path(__file__).parent / 'sample_dir'

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for file in sample_dir.rglob('*'):
        if file.is_file():
            arcname = file.relative_to(sample_dir)
            zf.write(file, arcname)

print(f"Created {zip_path}")

# Build manifest
manifest = {
    "description": "Test data for ZIP runtime validation",
    "files": []
}

# Add sample.zip to manifest
manifest["files"].append({
    "name": "sample.zip",
    "type": "archive",
    "sha256": compute_sha256(zip_path),
    "size_bytes": get_file_size(zip_path),
    "description": "ZIP archive containing sample_dir contents"
})

# Add sample_dir files to manifest
for file in sorted(sample_dir.rglob('*')):
    if file.is_file():
        rel_path = file.relative_to(sample_dir.parent)
        manifest["files"].append({
            "name": str(rel_path).replace('\\', '/'),
            "type": "text",
            "sha256": compute_sha256(file),
            "size_bytes": get_file_size(file),
            "description": f"Sample text file"
        })

# Write manifest
manifest_path = Path(__file__).parent / 'manifest.json'
with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2)

print(f"Created {manifest_path}")
print(f"\nManifest contents:")
print(json.dumps(manifest, indent=2))
