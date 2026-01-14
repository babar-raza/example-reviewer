"""
Aspose.ZIP Example Page Scanner
Scans all Aspose.ZIP pages and catalogs code examples
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class CodeExample:
    """Represents a code example found in documentation"""
    language: str
    code: str
    line_start: int
    line_end: int
    has_stream_disposal: bool = False
    has_async_methods: bool = False
    has_deflate_with_params: bool = False
    has_archive_create_entry: bool = False

@dataclass
class PageInfo:
    """Information about a documentation page"""
    file_path: str
    relative_path: str
    site: str  # blog, docs, kb, reference, products
    has_examples: bool
    examples: List[CodeExample]
    gist_urls: List[str]

class AsposeZipPageScanner:
    """Scans Aspose.ZIP pages for code examples"""

    def __init__(self, content_root: str):
        self.content_root = Path(content_root)
        self.pages: List[PageInfo] = []

    def find_all_pages(self) -> List[str]:
        """Find all English Aspose.ZIP pages"""
        pages = []

        # Blog posts (all index.md in zip folder are English)
        blog_dir = self.content_root / "blog.aspose.net" / "zip"
        if blog_dir.exists():
            for md_file in blog_dir.rglob("index.md"):
                pages.append(str(md_file))

        # Documentation (en folder)
        docs_dir = self.content_root / "docs.aspose.net" / "zip" / "en"
        if docs_dir.exists():
            for md_file in docs_dir.rglob("*.md"):
                pages.append(str(md_file))

        # Knowledge Base (en folder)
        kb_dir = self.content_root / "kb.aspose.net" / "zip" / "en"
        if kb_dir.exists():
            for md_file in kb_dir.rglob("*.md"):
                pages.append(str(md_file))

        # Products pages (en folder)
        products_dir = self.content_root / "products.aspose.net" / "zip"
        if products_dir.exists():
            for md_file in products_dir.rglob("*.md"):
                if "/en/" in str(md_file) or md_file.name == "_index.md":
                    pages.append(str(md_file))

        # Reference pages (en folder)
        ref_dir = self.content_root / "reference.aspose.net" / "zip" / "en"
        if ref_dir.exists():
            for md_file in ref_dir.rglob("*.md"):
                pages.append(str(md_file))

        return sorted(pages)

    def extract_code_blocks(self, content: str) -> List[CodeExample]:
        """Extract code blocks from markdown content"""
        examples = []

        # Pattern for fenced code blocks
        pattern = r'```(\w+)?\n(.*?)```'

        lines = content.split('\n')
        line_num = 0

        for match in re.finditer(pattern, content, re.DOTALL):
            language = match.group(1) or 'unknown'
            code = match.group(2)

            # Only interested in C# code
            if language.lower() not in ['csharp', 'cs', 'c#']:
                continue

            # Find line numbers
            start_pos = match.start()
            lines_before = content[:start_pos].count('\n')
            lines_in_code = code.count('\n')

            # Analyze code for issues
            has_stream_disposal = self._check_stream_disposal_issue(code)
            has_async_methods = self._check_async_methods(code)
            has_deflate_with_params = self._check_deflate_with_params(code)
            has_archive_create_entry = 'CreateEntry' in code

            example = CodeExample(
                language=language,
                code=code.strip(),
                line_start=lines_before + 1,
                line_end=lines_before + lines_in_code + 1,
                has_stream_disposal=has_stream_disposal,
                has_async_methods=has_async_methods,
                has_deflate_with_params=has_deflate_with_params,
                has_archive_create_entry=has_archive_create_entry
            )
            examples.append(example)

        return examples

    def _check_stream_disposal_issue(self, code: str) -> bool:
        """Check if code has the stream disposal timing issue"""
        # Look for pattern where using statement for stream is closed before Save
        # Pattern: using (var stream...) { ... CreateEntry(..., stream) } ... Save(...)

        # Simple heuristic: if CreateEntry is inside a using block and Save is outside
        has_create_entry = 'CreateEntry' in code
        has_save = '.Save(' in code or '.SaveAsync(' in code

        if not (has_create_entry and has_save):
            return False

        # Check if there's a using statement with MemoryStream or FileStream
        # followed by CreateEntry, and then closing brace before Save
        pattern = r'using\s*\([^)]*Stream[^)]*\)\s*\{[^}]*CreateEntry[^}]*\}\s*[^{]*\.Save'
        if re.search(pattern, code, re.DOTALL):
            return True

        return False

    def _check_async_methods(self, code: str) -> bool:
        """Check for non-existent async methods"""
        async_patterns = [
            'SaveAsync',
            'CreateEntryAsync',
            'ExtractAsync',
            'await.*Archive'
        ]

        for pattern in async_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return True
        return False

    def _check_deflate_with_params(self, code: str) -> bool:
        """Check for DeflateCompressionSettings with parameters"""
        # DeflateCompressionSettings doesn't accept parameters
        pattern = r'DeflateCompressionSettings\s*\([^)]+\)'
        return bool(re.search(pattern, code))

    def extract_gist_urls(self, content: str) -> List[str]:
        """Extract GitHub Gist URLs from content"""
        gist_pattern = r'https?://gist\.github\.com/[^\s\)"\']+'
        return re.findall(gist_pattern, content)

    def scan_page(self, file_path: str) -> PageInfo:
        """Scan a single page for code examples"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            examples = self.extract_code_blocks(content)
            gist_urls = self.extract_gist_urls(content)

            # Determine site
            rel_path = os.path.relpath(file_path, self.content_root)
            site = rel_path.split(os.sep)[0]

            return PageInfo(
                file_path=file_path,
                relative_path=rel_path,
                site=site,
                has_examples=len(examples) > 0 or len(gist_urls) > 0,
                examples=examples,
                gist_urls=gist_urls
            )
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
            return None

    def scan_all(self) -> None:
        """Scan all Aspose.ZIP pages"""
        print("Finding all Aspose.ZIP pages...")
        all_pages = self.find_all_pages()
        print(f"Found {len(all_pages)} pages")

        print("\nScanning pages for code examples...")
        for page_path in all_pages:
            page_info = self.scan_page(page_path)
            if page_info:
                self.pages.append(page_info)
                if page_info.has_examples:
                    print(f"  [+] {page_info.relative_path} - {len(page_info.examples)} examples")

    def get_pages_with_examples(self) -> List[PageInfo]:
        """Get only pages that have code examples"""
        return [p for p in self.pages if p.has_examples]

    def get_pages_with_issues(self) -> List[PageInfo]:
        """Get pages with potential issues mentioned in the email"""
        pages_with_issues = []

        for page in self.pages:
            has_issue = False
            for example in page.examples:
                if (example.has_stream_disposal or
                    example.has_async_methods or
                    example.has_deflate_with_params):
                    has_issue = True
                    break

            if has_issue:
                pages_with_issues.append(page)

        return pages_with_issues

    def save_catalog(self, output_path: str) -> None:
        """Save catalog of pages to JSON"""
        catalog = {
            'total_pages': len(self.pages),
            'pages_with_examples': len(self.get_pages_with_examples()),
            'pages_with_issues': len(self.get_pages_with_issues()),
            'pages': []
        }

        for page in self.pages:
            if page.has_examples:
                page_dict = {
                    'file_path': page.file_path,
                    'relative_path': page.relative_path,
                    'site': page.site,
                    'example_count': len(page.examples),
                    'gist_count': len(page.gist_urls),
                    'examples': []
                }

                for example in page.examples:
                    example_dict = {
                        'language': example.language,
                        'line_start': example.line_start,
                        'line_end': example.line_end,
                        'has_stream_disposal_issue': example.has_stream_disposal,
                        'has_async_methods': example.has_async_methods,
                        'has_deflate_with_params': example.has_deflate_with_params,
                        'code_preview': example.code[:200] + '...' if len(example.code) > 200 else example.code
                    }
                    page_dict['examples'].append(example_dict)

                page_dict['gist_urls'] = page.gist_urls
                catalog['pages'].append(page_dict)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)

        print(f"\nCatalog saved to {output_path}")

    def print_summary(self) -> None:
        """Print summary of scan results"""
        print("\n" + "="*80)
        print("SCAN SUMMARY")
        print("="*80)
        print(f"Total pages scanned: {len(self.pages)}")
        print(f"Pages with examples: {len(self.get_pages_with_examples())}")
        print(f"Pages with potential issues: {len(self.get_pages_with_issues())}")

        # Count issues
        stream_issues = 0
        async_issues = 0
        deflate_issues = 0

        for page in self.pages:
            for example in page.examples:
                if example.has_stream_disposal:
                    stream_issues += 1
                if example.has_async_methods:
                    async_issues += 1
                if example.has_deflate_with_params:
                    deflate_issues += 1

        print(f"\nPotential Issues Found:")
        print(f"  - Stream disposal timing: {stream_issues} examples")
        print(f"  - Async method hallucinations: {async_issues} examples")
        print(f"  - DeflateCompressionSettings with params: {deflate_issues} examples")
        print("="*80)


def main():
    """Main entry point"""
    script_dir = Path(__file__).parent.parent.parent.parent
    content_root = script_dir / "content"

    scanner = AsposeZipPageScanner(str(content_root))
    scanner.scan_all()
    scanner.print_summary()

    # Save catalog
    output_dir = Path(__file__).parent.parent / "reports"
    output_dir.mkdir(exist_ok=True, parents=True)

    catalog_path = output_dir / "page_catalog.json"
    scanner.save_catalog(str(catalog_path))

    # Save pages with issues to separate file
    issues_path = output_dir / "pages_with_issues.json"
    pages_with_issues = scanner.get_pages_with_issues()

    with open(issues_path, 'w', encoding='utf-8') as f:
        json.dump([{
            'file_path': p.file_path,
            'relative_path': p.relative_path,
            'site': p.site,
            'example_count': len(p.examples)
        } for p in pages_with_issues], f, indent=2)

    print(f"\nPages with issues saved to {issues_path}")


if __name__ == '__main__':
    main()
