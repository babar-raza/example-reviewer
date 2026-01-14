"""
Aspose.ZIP Example Review Orchestrator
Systematically reviews, fixes, and validates all code examples
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from .example_fixer import AsposeZipExampleFixer, ValidationResult, FixApplied

@dataclass
class ExampleReviewRecord:
    """Record of reviewing a single example"""
    page_path: str
    example_index: int
    example_line_start: int
    example_line_end: int
    original_code: str
    fixed_code: str
    validation_passed: bool
    fixes_applied: List[Dict]
    errors: List[str]
    reviewed_at: str
    needs_manual_review: bool = False
    notes: str = ""

class ReviewOrchestrator:
    """Orchestrates the systematic review of all examples"""

    def __init__(self, content_root: str, validator_path: str, catalog_path: str):
        self.content_root = Path(content_root)
        self.validator_path = Path(validator_path)
        self.catalog_path = Path(catalog_path)
        self.fixer = AsposeZipExampleFixer(str(validator_path))
        self.review_records: List[ExampleReviewRecord] = []

    def load_catalog(self) -> Dict:
        """Load the page catalog"""
        with open(self.catalog_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def extract_code_from_page(self, file_path: str, line_start: int, line_end: int) -> str:
        """Extract code snippet from a markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Adjust for 1-based indexing
            start_idx = max(0, line_start - 1)
            end_idx = min(len(lines), line_end)

            code_lines = lines[start_idx:end_idx]

            # Remove markdown code fence if present
            code_text = ''.join(code_lines)

            # Remove opening fence (```csharp, ```cs, etc.)
            code_text = re.sub(r'^```\w*\n', '', code_text)

            # Remove closing fence
            code_text = re.sub(r'\n```$', '', code_text)

            return code_text.strip()

        except Exception as e:
            print(f"Error extracting code from {file_path}: {e}")
            return ""

    def review_example(self, page_path: str, example_info: Dict) -> ExampleReviewRecord:
        """Review a single code example"""
        # Extract code
        code = self.extract_code_from_page(
            page_path,
            example_info['line_start'],
            example_info['line_end']
        )

        if not code:
            return ExampleReviewRecord(
                page_path=page_path,
                example_index=0,
                example_line_start=example_info['line_start'],
                example_line_end=example_info['line_end'],
                original_code="",
                fixed_code="",
                validation_passed=False,
                fixes_applied=[],
                errors=["Failed to extract code"],
                reviewed_at=datetime.now().isoformat(),
                needs_manual_review=True,
                notes="Code extraction failed"
            )

        # Fix and validate
        result = self.fixer.fix_and_validate_example(code)

        # Determine if manual review is needed
        needs_manual_review = False
        notes = []

        # Check for stream disposal warnings
        for fix in result.fixes_applied:
            if fix.fix_type == 'stream_disposal':
                needs_manual_review = True
                notes.append("Stream disposal timing needs manual verification")

        # Check if validation failed even after fixes
        if not result.success and len(result.fixes_applied) > 0:
            needs_manual_review = True
            notes.append("Failed to compile even after applying fixes")

        # Convert fixes to dict for JSON serialization
        fixes_dict = [asdict(fix) for fix in result.fixes_applied]

        return ExampleReviewRecord(
            page_path=page_path,
            example_index=0,
            example_line_start=example_info['line_start'],
            example_line_end=example_info['line_end'],
            original_code=result.original_code,
            fixed_code=result.fixed_code,
            validation_passed=result.success,
            fixes_applied=fixes_dict,
            errors=result.error_messages,
            reviewed_at=datetime.now().isoformat(),
            needs_manual_review=needs_manual_review,
            notes="; ".join(notes)
        )

    def update_page_with_fixed_code(self, page_path: str, record: ExampleReviewRecord) -> bool:
        """Update the markdown file with fixed code"""
        try:
            # Only update if validation passed and fixes were applied
            if not record.validation_passed or not record.fixes_applied:
                return False

            # Read the file
            with open(page_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = f.readlines()

            # Find and replace the code block
            # This is simplified - in production, you'd want more sophisticated replacement
            original_block = self.extract_code_from_page(
                page_path,
                record.example_line_start,
                record.example_line_end
            )

            if original_block and original_block in content:
                # Replace with fixed code
                updated_content = content.replace(original_block, record.fixed_code)

                # Write back
                with open(page_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)

                return True

            return False

        except Exception as e:
            print(f"Error updating {page_path}: {e}")
            return False

    def review_all_pages(self, max_pages: int = None, update_files: bool = False) -> None:
        """Review all pages in the catalog"""
        catalog = self.load_catalog()
        pages = catalog['pages']

        if max_pages:
            pages = pages[:max_pages]

        print(f"Reviewing {len(pages)} pages...")
        print()

        total_examples = 0
        examples_fixed = 0
        examples_validated = 0
        examples_need_manual_review = 0
        pages_updated = 0

        for page_idx, page in enumerate(pages, 1):
            page_path = page['file_path']
            relative_path = page['relative_path']

            print(f"[{page_idx}/{len(pages)}] {relative_path}")

            for example_idx, example in enumerate(page['examples'], 1):
                total_examples += 1

                # Review the example
                record = self.review_example(page_path, example)
                record.example_index = example_idx
                self.review_records.append(record)

                # Track stats
                if len(record.fixes_applied) > 0:
                    examples_fixed += 1

                if record.validation_passed:
                    examples_validated += 1

                if record.needs_manual_review:
                    examples_need_manual_review += 1

                # Print status
                status = "[PASS]" if record.validation_passed else "[FAIL]"
                fixes_str = f" ({len(record.fixes_applied)} fixes)" if record.fixes_applied else ""
                manual_str = " [MANUAL REVIEW]" if record.needs_manual_review else ""

                print(f"  Example {example_idx}: {status}{fixes_str}{manual_str}")

                # Update file if requested and validation passed
                if update_files and record.validation_passed and record.fixes_applied:
                    if self.update_page_with_fixed_code(page_path, record):
                        pages_updated += 1
                        print(f"    → Updated in file")

            print()

        # Print summary
        print("=" * 80)
        print("REVIEW SUMMARY")
        print("=" * 80)
        print(f"Total pages reviewed: {len(pages)}")
        print(f"Total examples reviewed: {total_examples}")
        print(f"Examples with fixes applied: {examples_fixed}")
        print(f"Examples validated successfully: {examples_validated}")
        print(f"Examples needing manual review: {examples_need_manual_review}")
        if update_files:
            print(f"Pages updated: {pages_updated}")
        print()

        # Print fix statistics
        fix_stats = self.fixer.get_fix_stats()
        print("Fix Statistics:")
        for key, value in fix_stats.items():
            print(f"  {key}: {value}")
        print("=" * 80)

    def save_review_report(self, output_path: str) -> None:
        """Save comprehensive review report"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_examples_reviewed': len(self.review_records),
            'examples_validated': sum(1 for r in self.review_records if r.validation_passed),
            'examples_with_fixes': sum(1 for r in self.review_records if r.fixes_applied),
            'examples_need_manual_review': sum(1 for r in self.review_records if r.needs_manual_review),
            'fix_statistics': self.fixer.get_fix_stats(),
            'records': [asdict(r) for r in self.review_records]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\nReview report saved to: {output_path}")

    def save_manual_review_list(self, output_path: str) -> None:
        """Save list of examples that need manual review"""
        manual_review = [
            {
                'page': r.page_path,
                'example_index': r.example_index,
                'line_start': r.example_line_start,
                'line_end': r.example_line_end,
                'notes': r.notes,
                'fixes_applied': r.fixes_applied,
                'errors': r.errors
            }
            for r in self.review_records
            if r.needs_manual_review
        ]

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(manual_review, f, indent=2, ensure_ascii=False)

        print(f"Manual review list saved to: {output_path}")


def main():
    """Main entry point"""
    script_dir = Path(__file__).parent.parent
    content_root = script_dir.parent.parent / "content"
    validator_path = script_dir / "test-examples"
    catalog_path = script_dir / "reports" / "page_catalog.json"
    reports_dir = script_dir / "reports"

    # Create orchestrator
    orchestrator = ReviewOrchestrator(
        content_root=str(content_root),
        validator_path=str(validator_path),
        catalog_path=str(catalog_path)
    )

    # Review all pages (set max_pages for testing, None for all)
    # Set update_files=True to actually update the markdown files
    orchestrator.review_all_pages(max_pages=5, update_files=False)

    # Save reports
    report_path = reports_dir / f"review_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    orchestrator.save_review_report(str(report_path))

    manual_review_path = reports_dir / "manual_review_needed.json"
    orchestrator.save_manual_review_list(str(manual_review_path))

    print("\nReview complete!")


if __name__ == '__main__':
    main()
