"""Check the contents of the LLM exploration zip."""
import zipfile
import os

zip_path = 'llm-exploration-clean.zip'

with zipfile.ZipFile(zip_path, 'r') as z:
    files = z.namelist()
    print(f"Total files: {len(files)}")
    print(f"Zip size: {os.path.getsize(zip_path) / 1024:.1f} KB\n")

    # Top-level files
    print("Top-level files:")
    top_level = [f for f in files if '/' not in f and '\\' not in f]
    for f in sorted(top_level):
        print(f"  {f}")

    # Directories
    print("\nDirectories included:")
    dirs = set()
    for f in files:
        if '/' in f:
            dirs.add(f.split('/')[0])
        elif '\\' in f:
            dirs.add(f.split('\\')[0])
    for d in sorted(dirs):
        count = len([f for f in files if f.startswith(d)])
        print(f"  {d}/ ({count} files)")
