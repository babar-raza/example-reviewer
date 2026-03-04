#!/usr/bin/env python3
"""
Complete setup script for all Aspose families.
Creates/updates configs, generates API catalogs, sets up test data directories.
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

FAMILY_DEFINITIONS = {
    "imaging": {
        "display_name": "Aspose.Imaging for .NET",
        "repo_url": "https://github.com/aspose-imaging/Aspose.Imaging-for-.NET",
        "package_name": "Aspose.Imaging",
        "root_namespace": "Aspose.Imaging",
        "default_usings": [
            "System", "System.IO", "System.Text",
            "Aspose.Imaging",
            "Aspose.Imaging.FileFormats",
            "Aspose.Imaging.ImageOptions",
            "Aspose.Imaging.Sources"
        ],
        "required_files": ["sample.png", "sample.jpg", "sample.bmp", "sample.gif", "sample.tiff"],
        "content_volume": 9233
    },
    "slides": {
        "display_name": "Aspose.Slides for .NET",
        "repo_url": "https://github.com/aspose-slides/Aspose.Slides-for-.NET",
        "package_name": "Aspose.Slides.NET",
        "root_namespace": "Aspose.Slides",
        "default_usings": [
            "System", "System.IO", "System.Text",
            "Aspose.Slides",
            "Aspose.Slides.Export",
            "Aspose.Slides.Charts",
            "Aspose.Slides.Animation"
        ],
        "required_files": ["presentation.pptx", "sample.pptx", "template.pptx"],
        "content_volume": 5736
    },
    "email": {
        "display_name": "Aspose.Email for .NET",
        "repo_url": "https://github.com/aspose-email/Aspose.Email-for-.NET",
        "package_name": "Aspose.Email",
        "root_namespace": "Aspose.Email",
        "default_usings": [
            "System", "System.IO", "System.Text",
            "Aspose.Email",
            "Aspose.Email.Clients",
            "Aspose.Email.Clients.Smtp",
            "Aspose.Email.Mail"
        ],
        "required_files": ["sample.msg", "sample.eml", "sample.mbox"],
        "content_volume": 621
    },
    "tex": {
        "display_name": "Aspose.TeX for .NET",
        "repo_url": "https://github.com/aspose-tex/Aspose.TeX-for-.NET",
        "package_name": "Aspose.TeX",
        "root_namespace": "Aspose.TeX",
        "default_usings": [
            "System", "System.IO", "System.Text",
            "Aspose.TeX",
            "Aspose.TeX.IO",
            "Aspose.TeX.Presentation"
        ],
        "required_files": ["sample.tex", "hello-world.tex"],
        "content_volume": 2317
    },
    "cad": {
        "display_name": "Aspose.CAD for .NET",
        "repo_url": "https://github.com/aspose-cad/Aspose.CAD-for-.NET",
        "package_name": "Aspose.CAD",
        "root_namespace": "Aspose.CAD",
        "default_usings": [
            "System", "System.IO", "System.Text",
            "Aspose.CAD",
            "Aspose.CAD.FileFormats",
            "Aspose.CAD.ImageOptions"
        ],
        "required_files": ["sample.dwg", "sample.dxf", "sample.dwf"],
        "content_volume": 559
    },
    "html": {
        "display_name": "Aspose.HTML for .NET",
        "repo_url": "https://github.com/aspose-html/Aspose.HTML-for-.NET",
        "package_name": "Aspose.HTML",
        "root_namespace": "Aspose.Html",
        "default_usings": [
            "System", "System.IO", "System.Text",
            "Aspose.Html",
            "Aspose.Html.Dom",
            "Aspose.Html.Rendering"
        ],
        "required_files": ["sample.html", "index.html", "document.html"],
        "content_volume": 860
    },
    "page": {
        "display_name": "Aspose.Page for .NET",
        "repo_url": "https://github.com/aspose-page/Aspose.Page-for-.NET",
        "package_name": "Aspose.Page",
        "root_namespace": "Aspose.Page",
        "default_usings": [
            "System", "System.IO", "System.Text",
            "Aspose.Page",
            "Aspose.Page.EPS",
            "Aspose.Page.XPS"
        ],
        "required_files": ["sample.eps", "sample.xps", "sample.ps"],
        "content_volume": 821
    },
    "tasks": {
        "display_name": "Aspose.Tasks for .NET",
        "repo_url": "https://github.com/aspose-tasks/Aspose.Tasks-for-.NET",
        "package_name": "Aspose.Tasks",
        "root_namespace": "Aspose.Tasks",
        "default_usings": [
            "System", "System.IO", "System.Text",
            "Aspose.Tasks",
            "Aspose.Tasks.Saving",
            "Aspose.Tasks.Visualization"
        ],
        "required_files": ["sample.mpp", "project.mpp", "template.mpt"],
        "content_volume": 638
    },
    "medical": {
        "display_name": "Aspose.Medical for .NET",
        "repo_url": None,  # No repo available
        "package_name": "Aspose.Medical",
        "root_namespace": "Aspose.Medical",
        "default_usings": [
            "System", "System.IO", "System.Text",
            "Aspose.Medical"
        ],
        "required_files": [],
        "content_volume": 1295
    }
}


def create_complete_config(family: str, definition: Dict[str, Any]) -> Dict[str, Any]:
    """Generate complete family configuration."""

    config = {
        "family": family,
        "display_name": definition["display_name"],
        "auto_commit": True,
        "commit_message_template": f"fix({family}): apply {{patch_count}} patches\n\n{{file_list}}\n\nSnippets: {{snippet_ids}}",
        "content_roots": [
            f"D:/onedrive/Documents/GitHub/aspose.net/content/blog.aspose.net/{family}",
            f"D:/onedrive/Documents/GitHub/aspose.net/content/docs.aspose.net/{family}/en",
            f"D:/onedrive/Documents/GitHub/aspose.net/content/kb.aspose.net/{family}/en"
        ],
        "content_pattern": {
            "blog": "**/index.md",
            "docs": "**/*.md",
            "kb": "**/*.md"
        },
        "file_exclude_patterns": [
            "index\\.[a-z]{2}\\.md$",
            "index\\.[a-z]{2}-[a-z]{2}\\.md$",
            "[/\\\\](ar|bg|ca|cs|da|de|el|es|fa|fi|fr|he|hi|hr|hu|id|it|ja|ko|lt|lv|ms|nl|no|pl|pt|ro|ru|sk|sr|sv|th|tr|uk|vi|zh)[/\\\\]"
        ],
        "nuget_config": {
            "primary_package": {
                "name": definition["package_name"],
                "version_strategy": "latest_stable"
            },
            "additional_packages": [],
            "target_frameworks": ["net8.0"]
        },
        "code_defaults": {
            "default_usings": definition["default_usings"]
        },
        "namespace_policy": {
            "mode": "whitelist",
            "allowed_namespaces": [
                definition["root_namespace"],
                f"{definition['root_namespace']}.*",
                "System",
                "System.*",
                "System.IO",
                "System.Text",
                "System.Drawing",
                "System.Collections.Generic",
                "System.Linq"
            ],
            "blacklist": []
        },
        "patterns": [],
        "non_existent_apis": [],
        "api_patterns": {},
        "runtime_validation": {
            "enabled": True,
            "mode": "lenient",
            "timeout_seconds": 30,
            "required_files": definition["required_files"],
            "required_dirs": [],
            "file_aliases": {},
            "expected_outputs": [],
            "env": {}
        },
        "test_data": {
            "local_path": f"artifacts/backfill/{family}/test-data",
            "download_if_missing": False,
            "inventory_path": f"artifacts/backfill/{family}/test-data-inventory.json"
        },
        "gist": {
            "enabled": True,
            "pat_env_var": "GITHUB_PAT"
        },
        "discovery_patterns": {
            "fence_patterns": ["^```(\\w+|c#)\\s*\\n(.*?)^```"],
            "validatable_languages": ["cs", "csharp", "c#", "C#"],
            "normalize_to_canonical": True,
            "regex_timeout_seconds": 5.0,
            "context_extraction": {
                "enabled": True,
                "max_paragraphs": 3,
                "include_file_header": True
            },
            "gist_extraction": {
                "enabled": True,
                "allowed_owners": ["aspose-com-gists", f"aspose-{family}"],
                "blocked_owners": []
            }
        },
        "context_enforcement": {
            "enabled": True
        },
        "fixture_passwords": {
            "default": "p@s$"
        },
        "api_catalog": {
            "enabled": True,
            "storage_type": "json",
            "path": f"config/families/{family}_api_catalog.json",
            "lazy_loading": False
        },
        "fixture_resolver": {
            "enabled": True,
            "max_generations_per_run": 50,
            "registry_path": f"artifacts/backfill/{family}/fixture-registry.json"
        },
        "learned_patterns": {
            "enabled": True,
            "min_confidence": 0.6,
            "max_patterns_per_error": 3,
            "require_approval": True,
            "feedback_tracking": True,
            "retire_threshold": 0.3,
            "retire_min_applications": 10
        },
        "persistent_fix": {
            "enabled": True,
            "max_iterations": 10,
            "iterations_per_model": 3,
            "max_time_seconds": 300,
            "enable_immediate_patching": True,
            "enable_context_inference": True
        },
        "dependency_resolution": {
            "enabled": True,
            "confidence_threshold": 0.7
        }
    }

    # Add example_repo if URL exists
    if definition["repo_url"]:
        config["example_repo"] = {
            "url": definition["repo_url"],
            "examples_path": "Examples",
            "test_data_path": "Data",
            "ref": "master"
        }

    return config


def main():
    """Setup all families."""

    project_root = Path(__file__).parent.parent.parent
    config_dir = project_root / "config" / "families"

    print("=" * 80)
    print("ASPOSE FAMILY COMPLETE SETUP")
    print("=" * 80)
    print()

    families_created = []
    families_updated = []

    for family, definition in FAMILY_DEFINITIONS.items():
        config_path = config_dir / f"{family}.json"

        print(f"[*] {family.upper()}: {definition['display_name']}")
        print(f"    Content Volume: {definition['content_volume']:,} files")
        print(f"    Repo: {definition['repo_url'] or 'NONE (tolerating missing)'}")

        # Generate complete config
        complete_config = create_complete_config(family, definition)

        # Write config
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(complete_config, f, indent=2, ensure_ascii=False)

        if config_path.exists():
            families_updated.append(family)
            print(f"    [OK] Config updated: {config_path}")
        else:
            families_created.append(family)
            print(f"    [OK] Config created: {config_path}")

        # Create test data directory
        test_data_dir = project_root / "artifacts" / "backfill" / family / "test-data"
        test_data_dir.mkdir(parents=True, exist_ok=True)
        print(f"    [OK] Test data dir: {test_data_dir}")

        print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"[OK] Configs created: {len(families_created)}")
    print(f"[OK] Configs updated: {len(families_updated)}")
    print(f"[OK] Total families ready: {len(FAMILY_DEFINITIONS)}")
    print()
    print("NEXT STEPS:")
    print("1. Generate API catalogs: python scripts/setup/batch_generate_catalogs_v2.py")
    print("2. Run preflight checks: python scripts/ops/batch_preflight.py")
    print("=" * 80)


if __name__ == "__main__":
    main()
