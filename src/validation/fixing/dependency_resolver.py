"""
Automatic NuGet dependency resolution service.

Analyzes C# code to extract using statements, maps namespaces to NuGet packages,
and dynamically updates .csproj files to install required dependencies.
"""

import re
import sqlite3
import subprocess
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


@dataclass
class DependencyResolution:
    """Result of resolving a single namespace."""
    namespace: str
    package_name: Optional[str]
    package_version: Optional[str]
    status: str  # 'resolved', 'bcl', 'unknown'
    source: str  # 'database', 'heuristic', 'bcl', 'unknown'
    confidence: float


class NamespaceToPackageMapper:
    """Maps C# namespaces to NuGet packages using database and heuristics."""

    def __init__(self, db_conn: sqlite3.Connection):
        self.db_conn = db_conn

    def map_namespace(self, namespace: str) -> DependencyResolution:
        """
        Map a single namespace to its package requirement.

        Args:
            namespace: C# namespace (e.g., 'System.Net.Http')

        Returns:
            DependencyResolution with package info or status
        """
        # Query database first
        cursor = self.db_conn.execute("""
            SELECT package_name, package_version, source, confidence
            FROM namespace_to_package
            WHERE namespace = ?
            ORDER BY confidence DESC
            LIMIT 1
        """, (namespace,))

        row = cursor.fetchone()

        if row:
            package_name, package_version, source, confidence = row

            # BCL namespace (no package needed)
            if source == 'bcl' or not package_name:
                return DependencyResolution(
                    namespace=namespace,
                    package_name=None,
                    package_version=None,
                    status='bcl',
                    source='database',
                    confidence=confidence
                )

            # External package
            return DependencyResolution(
                namespace=namespace,
                package_name=package_name,
                package_version=package_version,
                status='resolved',
                source='database',
                confidence=confidence
            )

        # Not in database - try heuristics
        heuristic_result = self._apply_heuristics(namespace)
        if heuristic_result:
            return heuristic_result

        # Unknown namespace
        return DependencyResolution(
            namespace=namespace,
            package_name=None,
            package_version=None,
            status='unknown',
            source='unknown',
            confidence=0.0
        )

    def _apply_heuristics(self, namespace: str) -> Optional[DependencyResolution]:
        """
        Apply heuristic rules for common namespace patterns.

        Heuristics:
        1. Microsoft.* → Often package name matches namespace
        2. System.* → Check if it's BCL or external
        3. Aspose.* → Primary Aspose package for that product
        """
        # Heuristic 1: Microsoft packages often match namespace
        if namespace.startswith('Microsoft.'):
            return DependencyResolution(
                namespace=namespace,
                package_name=namespace.split('.')[0] + '.' + namespace.split('.')[1],
                package_version=None,  # Use latest
                status='resolved',
                source='heuristic',
                confidence=0.5
            )

        # Heuristic 2: Aspose packages
        if namespace.startswith('Aspose.'):
            product = namespace.split('.')[1]  # E.g., Aspose.Pdf → Pdf
            return DependencyResolution(
                namespace=namespace,
                package_name=f'Aspose.{product}',
                package_version=None,
                status='resolved',
                source='heuristic',
                confidence=0.7
            )

        return None


class DependencyResolver:
    """
    Resolves missing dependencies by analyzing code and updating .csproj files.
    """

    def __init__(self, db_conn: sqlite3.Connection, workspace_dir: Path,
                 telemetry=None):
        """
        Initialize dependency resolver.

        Args:
            db_conn: SQLite database connection
            workspace_dir: Path to validator workspace (contains .csproj)
            telemetry: Optional telemetry service
        """
        self.db_conn = db_conn
        self.workspace_dir = Path(workspace_dir)
        self.telemetry = telemetry
        self.mapper = NamespaceToPackageMapper(db_conn)

        self.csproj_path = self.workspace_dir / "Validator.csproj"
        if not self.csproj_path.exists():
            raise FileNotFoundError(f".csproj not found: {self.csproj_path}")

    def analyze_and_resolve(self, snippet_id: int, code: str,
                           run_id: Optional[int] = None) -> Tuple[bool, List[DependencyResolution]]:
        """
        Analyze code, resolve dependencies, and update .csproj if needed.

        Args:
            snippet_id: Database snippet ID
            code: C# source code
            run_id: Optional run ID for tracking

        Returns:
            (success, list of resolutions)
        """
        # Extract using statements
        namespaces = self._extract_namespaces(code)

        if not namespaces:
            return True, []  # No dependencies needed

        # Map namespaces to packages
        resolutions = []
        packages_to_add = []

        for ns in namespaces:
            res = self.mapper.map_namespace(ns)
            resolutions.append(res)

            # Record resolution in database
            self._record_resolution(snippet_id, run_id, res)

            # Collect packages that need to be added
            if res.status == 'resolved' and res.package_name:
                packages_to_add.append((res.package_name, res.package_version))

            # Log telemetry
            if self.telemetry:
                self.telemetry.increment_metric(f'dependency_resolution_{res.status}')

        # Update .csproj if needed
        if packages_to_add:
            success = self._update_csproj_and_restore(packages_to_add)

            if self.telemetry:
                if success:
                    self.telemetry.increment_metric('dependency_csproj_updated')
                else:
                    self.telemetry.increment_metric('dependency_csproj_update_failed')

            return success, resolutions

        return True, resolutions

    def _extract_namespaces(self, code: str) -> List[str]:
        """
        Extract using statements from C# code.

        Returns:
            List of namespace strings (e.g., ['System.IO', 'Newtonsoft.Json'])
        """
        # Pattern: using [static] <namespace>;
        # Exclude: using <alias> = <namespace>;
        pattern = r'^\s*using\s+(?!static\s)([a-zA-Z_][\w\.]*)\s*;'

        matches = re.findall(pattern, code, re.MULTILINE)

        # Filter out alias declarations (contain '=')
        namespaces = [m for m in matches if '=' not in code[max(0, code.find(m) - 50):code.find(m) + len(m) + 50]]

        return list(set(namespaces))  # Deduplicate

    def _update_csproj_and_restore(self, packages: List[Tuple[str, Optional[str]]]) -> bool:
        """
        Update .csproj with new packages and run dotnet restore.

        Args:
            packages: List of (package_name, version) tuples

        Returns:
            True if successful, False otherwise
        """
        try:
            # Parse XML
            tree = ET.parse(self.csproj_path)
            root = tree.getroot()

            # Find or create ItemGroup for PackageReference
            item_group = root.find(".//ItemGroup[PackageReference]")
            if item_group is None:
                # Create new ItemGroup
                item_group = ET.SubElement(root, "ItemGroup")

            # Get existing package references (case-insensitive for NuGet package IDs)
            existing_packages = {
                ref.get('Include').lower(): (ref.get('Include'), ref.get('Version'))
                for ref in item_group.findall('PackageReference')
                if ref.get('Include')
            }

            # Add missing packages
            added_count = 0
            for package_name, package_version in packages:
                # Case-insensitive check (NuGet package IDs are case-insensitive)
                if package_name.lower() not in existing_packages:
                    # Add new PackageReference
                    pkg_ref = ET.SubElement(item_group, 'PackageReference')
                    pkg_ref.set('Include', package_name)

                    if package_version:
                        pkg_ref.set('Version', package_version)

                    added_count += 1

                    if self.telemetry:
                        self.telemetry.log_event(
                            'dependency_package_added',
                            'info',
                            f'Added package {package_name} v{package_version or "latest"}',
                            details={'package': package_name, 'version': package_version or 'latest'}
                        )

            if added_count == 0:
                return True  # No packages to add

            # Write updated .csproj
            tree.write(self.csproj_path, encoding='utf-8', xml_declaration=True)

            # Run dotnet restore
            return self._restore_packages()

        except Exception as e:
            if self.telemetry:
                self.telemetry.log_event(
                    'dependency_csproj_update_error',
                    'error',
                    f'Failed to update .csproj: {str(e)}',
                    details={'error': str(e)}
                )
            return False

    def _restore_packages(self) -> bool:
        """
        Run dotnet restore to install new packages.

        Returns:
            True if successful, False otherwise
        """
        try:
            result = subprocess.run(
                ['dotnet', 'restore', str(self.csproj_path)],
                capture_output=True,
                text=True,
                timeout=300,  # Increased from 120s to 300s for Azure packages
                cwd=str(self.workspace_dir)
            )

            if result.returncode == 0:
                if self.telemetry:
                    self.telemetry.log_event(
                        'dependency_restore_success',
                        'info',
                        'Successfully restored NuGet packages',
                        details={'stdout': result.stdout[:500]}
                    )
                return True
            else:
                if self.telemetry:
                    self.telemetry.log_event(
                        'dependency_restore_failed',
                        'warning',
                        f'Failed to restore packages: {result.stderr[:100]}',
                        details={'stderr': result.stderr[:500]}
                    )
                return False

        except subprocess.TimeoutExpired:
            if self.telemetry:
                self.telemetry.log_event(
                    'dependency_restore_timeout',
                    'warning',
                    'Package restore timed out after 300 seconds',
                    details={'timeout': 300}
                )
            return False
        except FileNotFoundError:
            if self.telemetry:
                self.telemetry.log_event(
                    'dependency_dotnet_not_found',
                    'error',
                    'dotnet CLI not found in PATH',
                    details={'message': 'dotnet CLI not found in PATH'}
                )
            return False

    def _record_resolution(self, snippet_id: int, run_id: Optional[int],
                          resolution: DependencyResolution):
        """Record dependency resolution in database."""
        try:
            self.db_conn.execute("""
                INSERT INTO dependency_resolutions
                (snippet_id, run_id, namespace, package_name, package_version,
                 resolution_status, resolution_source, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snippet_id,
                run_id,
                resolution.namespace,
                resolution.package_name,
                resolution.package_version,
                resolution.status,
                resolution.source,
                resolution.confidence
            ))
            self.db_conn.commit()

        except sqlite3.Error as e:
            if self.telemetry:
                self.telemetry.log_event(
                    'dependency_record_error',
                    'warning',
                    f'Failed to record dependency resolution: {str(e)}',
                    details={'error': str(e)}
                )

    def get_resolution_summary(self, run_id: Optional[int] = None) -> Dict:
        """
        Get summary statistics of dependency resolutions.

        Args:
            run_id: Optional run ID to filter by

        Returns:
            Dictionary with resolution statistics
        """
        query = """
            SELECT
                resolution_status,
                resolution_source,
                COUNT(*) as count,
                COUNT(DISTINCT snippet_id) as snippet_count
            FROM dependency_resolutions
        """

        if run_id:
            query += " WHERE run_id = ?"
            params = (run_id,)
        else:
            params = ()

        query += " GROUP BY resolution_status, resolution_source"

        cursor = self.db_conn.execute(query, params)
        rows = cursor.fetchall()

        summary = {
            'by_status': {},
            'by_source': {},
            'total_resolutions': 0,
            'total_snippets': 0
        }

        for status, source, count, snippet_count in rows:
            summary['by_status'][status] = summary['by_status'].get(status, 0) + count
            summary['by_source'][source] = summary['by_source'].get(source, 0) + count
            summary['total_resolutions'] += count
            summary['total_snippets'] = max(summary['total_snippets'], snippet_count)

        return summary
