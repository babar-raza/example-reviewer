"""
API Index Builder - Parses API reference markdown files and populates database.

This module extracts API signatures from markdown documentation and stores them
in the database for use by the LLM during code fixing.
"""

import os
import re
import glob
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from src.core.database import Database
from src.core.telemetry import TelemetryClient


@dataclass
class ApiMember:
    """Represents a single API member (constructor, method, property, etc.)"""
    member_type: str
    member_name: Optional[str]
    signature: str
    description: Optional[str] = None
    example_code: Optional[str] = None
    notes: Optional[str] = None
    is_static: bool = False
    is_readonly: bool = False
    return_type: Optional[str] = None
    parameters: Optional[str] = None  # JSON string


@dataclass
class ClassInfo:
    """Represents a parsed API class"""
    namespace: str
    class_name: str
    assembly_version: str
    members: List[ApiMember]
    class_description: Optional[str] = None
    class_notes: Optional[str] = None


class ApiIndexBuilder:
    """Builds API reference index from markdown documentation."""

    def __init__(self, db: Database, telemetry: TelemetryClient):
        self.db = db
        self.telemetry = telemetry

    def build_index_for_family(self, family: str, reference_root: str,
                              force_rebuild: bool = False) -> Dict[str, int]:
        """
        Parse all markdown files for a family and populate database.

        Args:
            family: Product family name (e.g., 'zip')
            reference_root: Path to reference.aspose.net directory
            force_rebuild: If True, delete existing entries and rebuild

        Returns:
            Dictionary with stats: {'classes': N, 'members': M, 'errors': E}
        """
        # Ensure database connection is established
        self.db.connect()

        stats = {'classes': 0, 'members': 0, 'errors': 0, 'skipped': 0}

        # Delete existing entries if force rebuild
        if force_rebuild:
            self.db._conn.execute("DELETE FROM api_reference WHERE family = ?", (family,))
            self.db._conn.commit()
            self.telemetry.log_event('api_index_rebuild', 'info',
                                   f'Cleared existing API index for family {family}',
                                   details={'family': family, 'action': 'cleared_existing'})

        # Find all API reference markdown files
        reference_path = os.path.join(reference_root, family, 'en')
        if not os.path.exists(reference_path):
            raise FileNotFoundError(f"API reference path not found: {reference_path}")

        md_files = glob.glob(os.path.join(reference_path, "Aspose*.md"))
        self.telemetry.log_event('api_index_build_start', 'info',
                               f'Starting API index build for {family} ({len(md_files)} files)',
                               details={'family': family, 'file_count': len(md_files)})

        # Parse each markdown file
        for i, file_path in enumerate(md_files, 1):
            try:
                class_info = self._parse_markdown_file(file_path)
                if class_info:
                    self._insert_class_info(family, class_info)
                    stats['classes'] += 1
                    stats['members'] += len(class_info.members)

                    if i % 20 == 0:
                        self.telemetry.log_event('api_index_progress', 'info',
                                               f'Progress: {i}/{len(md_files)} files processed',
                                               details={'processed': i, 'total': len(md_files)})
                else:
                    stats['skipped'] += 1
            except Exception as e:
                stats['errors'] += 1
                self.telemetry.log_event('api_parse_error', 'warning',
                                       f'Failed to parse {os.path.basename(file_path)}: {str(e)}',
                                       details={'file': os.path.basename(file_path), 'error': str(e)})

        self.db._conn.commit()
        self.telemetry.log_event('api_index_build_complete', 'info',
                               f'API index build complete for {family}',
                               details=stats)
        return stats

    def _parse_markdown_file(self, file_path: str) -> Optional[ClassInfo]:
        """Parse a single API reference markdown file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract YAML front matter
        yaml_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not yaml_match:
            return None

        # Extract namespace and assembly version
        namespace_match = re.search(r'Namespace:\s+\[([^\]]+)\]', content)
        assembly_match = re.search(r'Assembly:\s+([^\s]+)\s+\(([^)]+)\)', content)

        if not namespace_match or not assembly_match:
            return None

        namespace = namespace_match.group(1).replace(f'/{self._extract_family(file_path)}/', '')
        assembly_version = assembly_match.group(2)

        # Extract class name from file path
        class_name = Path(file_path).stem

        # Extract class description
        desc_match = re.search(r'Assembly:.*?\n\n(.+?)\n\n```csharp', content, re.DOTALL)
        class_description = desc_match.group(1).strip() if desc_match else None

        # Extract class declaration
        class_decl_match = re.search(r'```csharp\n(public (?:class|interface|enum|struct) .+?)\n```', content)
        if not class_decl_match:
            return None

        class_signature = class_decl_match.group(1)

        # Parse members
        members = []

        # Add class itself as a member
        members.append(ApiMember(
            member_type='class',
            member_name=class_name.split('.')[-1],
            signature=class_signature,
            description=class_description
        ))

        # Extract constructors
        members.extend(self._extract_constructors(content, class_name))

        # Extract methods
        members.extend(self._extract_methods(content))

        # Extract properties
        members.extend(self._extract_properties(content))

        # Extract remarks/notes
        notes_match = re.search(r'## Remarks\n\n(.+?)(?=\n##|$)', content, re.DOTALL)
        class_notes = notes_match.group(1).strip() if notes_match else None

        return ClassInfo(
            namespace=namespace,
            class_name=class_name,
            assembly_version=assembly_version,
            members=members,
            class_description=class_description,
            class_notes=class_notes
        )

    def _extract_family(self, file_path: str) -> str:
        """Extract family name from file path."""
        # Expected path: .../reference.aspose.net/{family}/en/...
        parts = Path(file_path).parts
        try:
            en_idx = parts.index('en')
            return parts[en_idx - 1]
        except (ValueError, IndexError):
            return 'unknown'

    def _extract_constructors(self, content: str, class_name: str) -> List[ApiMember]:
        """Extract constructor definitions from markdown."""
        constructors = []

        # Find ## Constructors section
        ctor_section = re.search(r'## Constructors\n\n(.+?)(?=\n## |$)', content, re.DOTALL)
        if not ctor_section:
            return constructors

        # Find individual constructor definitions
        # CORRECTED: Anchor tag is empty, text is AFTER </a>
        ctor_pattern = r'### <a[^>]*></a> (.+?)\n\n(.+?)\n\n```csharp\n(.+?)```'

        for match in re.finditer(ctor_pattern, ctor_section.group(1), re.DOTALL):
            ctor_name = match.group(1).strip()
            description = match.group(2).strip() if match.group(2) else None
            signature = match.group(3).strip()

            # Try to find example code for this constructor
            example = self._extract_example_after_match(ctor_section.group(1), match.end())

            # Try to find parameters section
            parameters = self._extract_parameters_after_match(ctor_section.group(1), match.end())

            constructors.append(ApiMember(
                member_type='constructor',
                member_name=ctor_name,
                signature=signature,
                description=description,
                example_code=example,
                parameters=parameters
            ))

        return constructors

    def _extract_methods(self, content: str) -> List[ApiMember]:
        """Extract method definitions from markdown."""
        methods = []

        # Find ## Methods section
        method_section = re.search(r'## Methods\n\n(.+?)(?=\n## |$)', content, re.DOTALL)
        if not method_section:
            return methods

        # Find individual method definitions
        # CORRECTED: Anchor tag is empty, text is AFTER </a>
        method_pattern = r'### <a[^>]*></a> (.+?)\n\n(.+?)\n\n```csharp\n(.+?)```'

        for match in re.finditer(method_pattern, method_section.group(1), re.DOTALL):
            method_name = match.group(1).strip()
            description = match.group(2).strip() if match.group(2) else None
            signature = match.group(3).strip()

            # Skip if this looks like a property (no parentheses in name)
            if '(' not in method_name and 'get;' not in signature and 'set;' not in signature:
                continue

            # Determine if static
            is_static = 'static ' in signature

            # Extract return type
            return_type_match = re.match(r'(?:public |private |protected |internal |static )+(\S+)\s+\w+\s*\(', signature)
            return_type = return_type_match.group(1) if return_type_match else None

            # Extract example
            example = self._extract_example_after_match(method_section.group(1), match.end())

            methods.append(ApiMember(
                member_type='method',
                member_name=method_name.split('(')[0],  # Remove parameter list
                signature=signature,
                description=description,
                is_static=is_static,
                return_type=return_type,
                example_code=example
            ))

        return methods

    def _extract_properties(self, content: str) -> List[ApiMember]:
        """Extract property definitions from markdown."""
        properties = []

        # Find ## Properties section
        prop_section = re.search(r'## Properties\n\n(.+?)(?=\n## |$)', content, re.DOTALL)
        if not prop_section:
            return properties

        # Find property entries
        # CORRECTED: Anchor tag is empty, text is AFTER </a>
        prop_pattern = r'### <a[^>]*></a> (.+?)\n\n(.+?)\n\n```csharp\n(.+?)```'

        for match in re.finditer(prop_pattern, prop_section.group(1), re.DOTALL):
            prop_name = match.group(1).strip()
            description = match.group(2).strip() if match.group(2) else None
            signature = match.group(3).strip()

            # Skip if this looks like a method
            if '(' in signature and ')' in signature and 'get;' not in signature:
                continue

            # Determine if readonly
            is_readonly = 'get;' in signature and 'set;' not in signature

            # Extract return type (property type)
            type_match = re.match(r'(?:public |private |protected |internal |static )*(\S+)\s+(\w+)\s*{', signature)
            return_type = type_match.group(1) if type_match else None

            properties.append(ApiMember(
                member_type='property',
                member_name=prop_name,
                signature=signature,
                description=description,
                is_readonly=is_readonly,
                return_type=return_type
            ))

        return properties

    def _extract_example_after_match(self, section_text: str, match_end: int) -> Optional[str]:
        """Extract example code that appears after a method/constructor definition."""
        # Look for #### Examples section
        remaining_text = section_text[match_end:]
        example_match = re.search(r'#### Examples\n\n.+?```csharp\n([^`]+)```', remaining_text, re.DOTALL)
        if example_match:
            return example_match.group(1).strip()
        return None

    def _extract_parameters_after_match(self, section_text: str, match_end: int) -> Optional[str]:
        """Extract parameter documentation that appears after a method/constructor definition."""
        # Look for #### Parameters section
        remaining_text = section_text[match_end:]
        param_match = re.search(r'#### Parameters\n\n(.+?)(?=\n####|\n###|$)', remaining_text, re.DOTALL)
        if not param_match:
            return None

        param_text = param_match.group(1).strip()
        params = []

        # Parse parameter entries (format: `paramName` [Type](link) description)
        param_pattern = r'`(\w+)`\s+\[([^\]]+)\]'
        for match in re.finditer(param_pattern, param_text):
            params.append({
                'name': match.group(1),
                'type': match.group(2)
            })

        return json.dumps(params) if params else None

    def _insert_class_info(self, family: str, class_info: ClassInfo):
        """Insert parsed class information into database."""
        for member in class_info.members:
            try:
                self.db._conn.execute("""
                    INSERT OR REPLACE INTO api_reference (
                        family, namespace, class_name, member_type, member_name,
                        signature, description, example_code, notes,
                        assembly_version, is_static, is_readonly, return_type, parameters
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    family,
                    class_info.namespace,
                    class_info.class_name,
                    member.member_type,
                    member.member_name,
                    member.signature,
                    member.description,
                    member.example_code,
                    member.notes if member.member_type == 'class' else class_info.class_notes,
                    class_info.assembly_version,
                    member.is_static,
                    member.is_readonly,
                    member.return_type,
                    member.parameters
                ))
            except Exception as e:
                self.telemetry.log_event('api_insert_error', 'warning',
                                       f'Failed to insert {class_info.class_name}.{member.member_name}',
                                       details={'class': class_info.class_name,
                                              'member': member.member_name,
                                              'error': str(e)})
