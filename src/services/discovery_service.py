"""
Discovery Service for Example Reviewer Pipeline.
Implements Phase A: Discovery and Extraction.
"""

import re
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Generator
from glob import glob
import fnmatch

from ..core.models import ExampleRecord, ExampleStatus, SourceType, Location, GistInfo
from ..core.database import Database
from ..core.config import FamilyConfig

logger = logging.getLogger(__name__)


# Regex patterns for code extraction
FENCE_PATTERN = re.compile(
    r'^```(\w*)\s*\n(.*?)^```',
    re.MULTILINE | re.DOTALL
)

GIST_SHORTCODE_PATTERN = re.compile(
    r'\{\{<\s*gist\s+([^\s]+)\s+([^\s]+)(?:\s+["\']?([^"\'>\s]+)["\']?)?\s*>\}\}',
    re.IGNORECASE
)

GIST_SCRIPT_PATTERN = re.compile(
    r'<script\s+src=["\']https://gist\.github\.com/([^/]+)/([^.]+)\.js(?:\?file=([^"\']+))?["\']',
    re.IGNORECASE
)

# Languages we want to validate (primarily C#)
VALIDATABLE_LANGUAGES = {'cs', 'csharp', 'c#'}


class DiscoveryService:
    """
    Service for discovering and extracting code examples from markdown files.
    Implements the A_discovery_extraction phase from the spec.
    """
    
    def __init__(
        self,
        db: Database,
        content_roots: Optional[List[str]] = None,
    ):
        """
        Initialize discovery service.
        
        Args:
            db: Database instance
            content_roots: List of content root directories to scan
        """
        self.db = db
        self.content_roots = content_roots or []
    
    def discover_family(
        self,
        family: str,
        family_config: FamilyConfig,
        max_files: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Discover all code examples for a family.
        
        Args:
            family: Family identifier
            family_config: Family configuration
            max_files: Maximum files to process (for testing)
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'files_found': 0,
            'files_processed': 0,
            'examples_found': 0,
            'inline_examples': 0,
            'gist_examples': 0,
            'errors': 0,
        }
        
        # Get files to process
        files = self._find_markdown_files(family_config)
        stats['files_found'] = len(files)
        
        if max_files:
            files = files[:max_files]
        
        logger.info(f"Processing {len(files)} files for family {family}")
        
        for file_path in files:
            try:
                examples = self._process_file(file_path, family)
                
                for example in examples:
                    self.db.save_example(example)
                    stats['examples_found'] += 1
                    
                    if example.source_type == SourceType.INLINE:
                        stats['inline_examples'] += 1
                    else:
                        stats['gist_examples'] += 1
                
                stats['files_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                stats['errors'] += 1
        
        return stats
    
    def _find_markdown_files(self, family_config: FamilyConfig) -> List[str]:
        """Find all markdown files matching family patterns."""
        files = []
        
        # Use content roots from config or instance
        content_roots = family_config.content_roots or self.content_roots
        
        for root in content_roots:
            root_path = Path(root)
            if not root_path.exists():
                logger.warning(f"Content root does not exist: {root}")
                continue
            
            # If patterns defined, use them
            if family_config.content_pattern:
                for site, pattern in family_config.content_pattern.items():
                    full_pattern = str(root_path / pattern)
                    matched = glob(full_pattern, recursive=True)
                    files.extend(matched)
            else:
                # Default: find all .md files
                files.extend(str(p) for p in root_path.rglob("*.md"))
        
        return sorted(set(files))
    
    def _process_file(self, file_path: str, family: str) -> List[ExampleRecord]:
        """
        Process a single markdown file and extract code examples.
        
        Args:
            file_path: Path to markdown file
            family: Family identifier
            
        Returns:
            List of extracted ExampleRecord objects
        """
        examples = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract inline code examples
        inline_examples = self._extract_inline_examples(content, file_path, family)
        examples.extend(inline_examples)
        
        # Extract gist examples
        gist_examples = self._extract_gist_examples(content, file_path, family)
        examples.extend(gist_examples)
        
        return examples
    
    def _extract_inline_examples(
        self,
        content: str,
        file_path: str,
        family: str
    ) -> List[ExampleRecord]:
        """Extract inline fenced code blocks."""
        examples = []
        lines = content.split('\n')
        
        block_index = 0
        in_code_block = False
        code_start_line = 0
        code_language = ''
        code_lines = []
        
        for i, line in enumerate(lines):
            if line.startswith('```') and not in_code_block:
                # Start of code block
                in_code_block = True
                code_start_line = i + 1
                code_language = line[3:].strip().lower()
                code_lines = []
                
            elif line.startswith('```') and in_code_block:
                # End of code block
                in_code_block = False
                code_content = '\n'.join(code_lines)
                
                # Only include validatable languages
                if code_language in VALIDATABLE_LANGUAGES and code_content.strip():
                    example = ExampleRecord(
                        family=family,
                        file_path=file_path,
                        source_type=SourceType.INLINE,
                        language=code_language,
                        location=Location(
                            block_index=block_index,
                            start_line=code_start_line,
                            end_line=i + 1,
                        ),
                        original_code=code_content,
                        status=ExampleStatus.DISCOVERED,
                    )
                    # Generate ID is called in model_post_init
                    examples.append(example)
                
                block_index += 1
                
            elif in_code_block:
                code_lines.append(line)
        
        return examples
    
    def _extract_gist_examples(
        self,
        content: str,
        file_path: str,
        family: str
    ) -> List[ExampleRecord]:
        """Extract gist shortcode references."""
        examples = []
        lines = content.split('\n')
        
        # Hugo shortcode pattern: {{< gist owner id "filename" >}}
        for i, line in enumerate(lines):
            for match in GIST_SHORTCODE_PATTERN.finditer(line):
                owner = match.group(1)
                gist_id = match.group(2)
                filename = match.group(3) or ""
                
                # Generate example ID from gist reference
                ref_str = f"{owner}/{gist_id}/{filename}"
                example_id = hashlib.sha256(
                    f"{file_path}:{ref_str}".encode()
                ).hexdigest()[:16]
                
                example = ExampleRecord(
                    example_id=example_id,
                    family=family,
                    file_path=file_path,
                    source_type=SourceType.GIST,
                    language='csharp',  # Assume C# for now
                    location=Location(
                        block_index=-1,  # Not applicable for gists
                        start_line=i + 1,
                        end_line=i + 1,
                    ),
                    gist=GistInfo(
                        owner=owner,
                        gist_id=gist_id,
                        filename=filename,
                    ),
                    original_code="",  # Will be fetched later
                    status=ExampleStatus.DISCOVERED,
                )
                examples.append(example)
        
        return examples
    
    def discover_directory(
        self,
        directory: str,
        family: str,
        recursive: bool = True,
    ) -> Dict[str, Any]:
        """
        Discover examples from a directory (for directory mode scan).
        
        Args:
            directory: Directory path
            family: Family identifier
            recursive: Whether to scan recursively
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'files_found': 0,
            'files_processed': 0,
            'examples_found': 0,
            'errors': 0,
        }
        
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.error(f"Directory does not exist: {directory}")
            return stats
        
        if recursive:
            files = list(dir_path.rglob("*.md"))
        else:
            files = list(dir_path.glob("*.md"))
        
        stats['files_found'] = len(files)
        
        for file_path in files:
            try:
                examples = self._process_file(str(file_path), family)
                
                for example in examples:
                    self.db.save_example(example)
                    stats['examples_found'] += 1
                
                stats['files_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                stats['errors'] += 1
        
        return stats


class GistResolver:
    """
    Resolves gist content from GitHub Gist API.
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize gist resolver.
        
        Args:
            token: GitHub personal access token (optional)
        """
        self.token = token
        self._cache: Dict[str, str] = {}
    
    def resolve_gist(
        self,
        owner: str,
        gist_id: str,
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Fetch gist content from GitHub.
        
        Args:
            owner: Gist owner
            gist_id: Gist ID
            filename: Specific file in the gist
            
        Returns:
            Gist content or None if not found
        """
        cache_key = f"{owner}/{gist_id}/{filename or ''}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            import urllib.request
            import json
            
            url = f"https://api.github.com/gists/{gist_id}"
            headers = {"Accept": "application/vnd.github.v3+json"}
            
            if self.token:
                headers["Authorization"] = f"token {self.token}"
            
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            files = data.get('files', {})
            
            if filename and filename in files:
                content = files[filename].get('content', '')
            elif files:
                # Return first file if no specific filename
                first_file = next(iter(files.values()))
                content = first_file.get('content', '')
            else:
                content = None
            
            self._cache[cache_key] = content
            return content
            
        except Exception as e:
            logger.error(f"Failed to fetch gist {gist_id}: {e}")
            return None
