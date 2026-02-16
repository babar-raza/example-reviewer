#!/usr/bin/env python3
"""Add DLL name mappings to family configs."""
import json
from pathlib import Path

MAPPINGS = {
    "imaging": {"package": "Aspose.Imaging", "dll": "Aspose.Imaging"},
    "slides": {"package": "Aspose.Slides.NET", "dll": "Aspose.Slides"},
    "email": {"package": "Aspose.Email", "dll": "Aspose.Email"},
    "tex": {"package": "Aspose.TeX", "dll": "Aspose.TeX"},
    "cad": {"package": "Aspose.CAD", "dll": "Aspose.CAD"},
    "html": {"package": "Aspose.HTML", "dll": "Aspose.HTML"},
    "page": {"package": "Aspose.Page", "dll": "Aspose.Page"},
    "tasks": {"package": "Aspose.Tasks", "dll": "Aspose.Tasks"},
    "medical": {"package": "Aspose.Medical", "dll": "Aspose.Medical"},
}

project_root = Path(__file__).parent.parent
config_dir = project_root / "config" / "families"

for family, mapping in MAPPINGS.items():
    config_path = config_dir / f"{family}.json"
    if not config_path.exists():
        continue

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Update nuget_config with dll_name
    config["nuget_config"]["primary_package"]["dll_name"] = mapping["dll"]

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"[OK] Updated {family}: {mapping['package']} -> {mapping['dll']}")

print("\nAll configs updated with DLL mappings!")
