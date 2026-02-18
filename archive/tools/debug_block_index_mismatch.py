#!/usr/bin/env python3
"""
Debug Block Index Mismatch Tool.

This tool diagnoses block index mismatches between extraction and md_update
by showing exactly how both systems parse the same markdown file.

Usage:
    python debug_block_index_mismatch.py --db-path <DB> --example-id <ID> --out <json>
    python debug_block_index_mismatch.py --db-path <DB> --run-id <RUN_ID> --example-id <ID> --out <json>
"""

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional


def compute_signature(code: str) -> str:
    """Compute SHA256 signature of normalized code (matches discovery/markdown services)."""
    normalized = code.strip().replace('\r\n', '\n')
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def parse_fenced_blocks(content: str) -> List[Dict[str, Any]]:
    """
    Parse all fenced code blocks (matches markdown_service._parse_fenced_blocks).

    Returns blocks with metadata:
    - index_all_fences: 0-based index among ALL fenced blocks
    - start_line: 1-based line number of opening fence
    - end_line: 1-based line number of closing fence
    - language: language tag from fence
    - content: code content (without fences)
    - signature: SHA256 hash of normalized content
    """
    lines = content.split('\n')
    blocks = []
    block_index = 0
    in_block = False
    block_start_line = 0
    block_language = ''
    block_content_lines = []

    for i, line in enumerate(lines):
        if line.startswith('```') and not in_block:
            # Start of code block
            in_block = True
            block_start_line = i + 1  # 1-based
            block_language = line[3:].strip().lower()
            block_content_lines = []

        elif line.startswith('```') and in_block:
            # End of code block
            in_block = False
            block_content = '\n'.join(block_content_lines)

            blocks.append({
                'index_all_fences': block_index,
                'start_line': block_start_line,
                'end_line': i + 1,  # 1-based
                'language': block_language,
                'content': block_content,
                'signature': compute_signature(block_content),
                'content_preview': block_content[:200] + ('...' if len(block_content) > 200 else ''),
            })

            block_index += 1

        elif in_block:
            block_content_lines.append(line)

    return blocks


def parse_csharp_blocks_only(content: str) -> List[Dict[str, Any]]:
    """
    Parse only C# fenced code blocks (for comparison).

    Returns blocks with metadata including index among C# blocks only.
    """
    all_blocks = parse_fenced_blocks(content)
    csharp_blocks = []
    csharp_index = 0

    for block in all_blocks:
        if block['language'] in ['csharp', 'c#', 'cs']:
            block_with_csharp_index = block.copy()
            block_with_csharp_index['index_csharp_only'] = csharp_index
            csharp_blocks.append(block_with_csharp_index)
            csharp_index += 1

    return csharp_blocks


def get_example_from_db(
    db_path: str,
    example_id: str,
    run_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Query database for example metadata."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query example_records for canonical metadata
    query = """
        SELECT
            er.example_id,
            er.file_path,
            er.location_block_index,
            er.location_start_line,
            er.location_end_line,
            er.language,
            er.original_code,
            er.code_block_signature,
            er.extraction_warning,
            er.app_context
        FROM example_records er
        WHERE er.example_id = ?
    """

    cursor.execute(query, (example_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    example = dict(row)

    # If run_id provided, also get run-scoped state
    if run_id:
        run_query = """
            SELECT
                status,
                failure_reason,
                verified_code
            FROM example_run_state
            WHERE example_id = ? AND run_id = ?
        """
        cursor.execute(run_query, (example_id, run_id))
        run_row = cursor.fetchone()
        if run_row:
            example.update(dict(run_row))

    conn.close()
    return example


def diagnose_block_index_mismatch(
    db_path: str,
    example_id: str,
    run_id: Optional[str] = None,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Diagnose block index mismatch for a specific example.

    Returns diagnostic report with:
    - Stored metadata (block_index, signature, etc.)
    - Parse results (all blocks with indices and signatures)
    - Analysis (signature matches, index matches, etc.)
    """
    # Get example from database
    example = get_example_from_db(db_path, example_id, run_id)

    if not example:
        return {
            'error': f'Example {example_id} not found in database',
            'db_path': db_path,
            'example_id': example_id,
        }

    # Read the markdown file
    file_path = example['file_path']

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return {
            'error': f'Failed to read file: {e}',
            'db_path': db_path,
            'example_id': example_id,
            'file_path': file_path,
        }

    # Parse all fenced blocks
    all_blocks = parse_fenced_blocks(content)
    csharp_blocks = parse_csharp_blocks_only(content)

    # Find signature matches
    stored_signature = example.get('code_block_signature')
    signature_matches = []

    if stored_signature:
        for block in all_blocks:
            if block['signature'] == stored_signature:
                signature_matches.append({
                    'index_all_fences': block['index_all_fences'],
                    'start_line': block['start_line'],
                    'end_line': block['end_line'],
                    'language': block['language'],
                })

    # Build diagnostic report
    report = {
        'db_path': db_path,
        'example_id': example_id,
        'run_id': run_id,
        'file_path': file_path,
        'stored_metadata': {
            'block_index': example['location_block_index'],
            'start_line': example['location_start_line'],
            'end_line': example['location_end_line'],
            'language': example['language'],
            'signature': stored_signature,
            'signature_short': stored_signature[:16] + '...' if stored_signature else None,
            'extraction_warning': example.get('extraction_warning'),
            'app_context': example.get('app_context'),
        },
        'parse_results': {
            'total_blocks': len(all_blocks),
            'csharp_blocks': len(csharp_blocks),
            'all_blocks': all_blocks,
        },
        'analysis': {
            'signature_matches': signature_matches,
            'signature_match_count': len(signature_matches),
            'stored_index_in_range': (
                0 <= example['location_block_index'] < len(all_blocks)
            ),
        },
    }

    # Check if stored index points to correct signature
    stored_index = example['location_block_index']
    if 0 <= stored_index < len(all_blocks):
        block_at_stored_index = all_blocks[stored_index]
        report['analysis']['block_at_stored_index'] = {
            'language': block_at_stored_index['language'],
            'signature': block_at_stored_index['signature'],
            'signature_short': block_at_stored_index['signature'][:16] + '...',
            'signature_matches': (
                block_at_stored_index['signature'] == stored_signature
                if stored_signature else None
            ),
            'start_line': block_at_stored_index['start_line'],
            'end_line': block_at_stored_index['end_line'],
            'content_preview': block_at_stored_index['content_preview'],
        }
    else:
        report['analysis']['block_at_stored_index'] = None

    # Determine diagnosis
    if not stored_signature:
        diagnosis = 'NO_SIGNATURE: Example has no code_block_signature (legacy or pre-migration)'
    elif len(signature_matches) == 0:
        diagnosis = 'SIGNATURE_NOT_FOUND: Stored signature not found in any block (file may have changed)'
    elif len(signature_matches) > 1:
        diagnosis = 'DUPLICATE_SIGNATURE: Multiple blocks match signature (ambiguous targeting)'
    elif len(signature_matches) == 1:
        match = signature_matches[0]
        if match['index_all_fences'] == stored_index:
            diagnosis = 'OK: Signature found at expected index'
        else:
            diagnosis = f'MISMATCH: Signature found at index {match["index_all_fences"]} but stored index is {stored_index}'
    else:
        diagnosis = 'UNKNOWN'

    report['diagnosis'] = diagnosis

    # Save to file if output_path provided
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"Diagnostic report saved to: {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description='Diagnose block index mismatches between extraction and md_update'
    )
    parser.add_argument(
        '--db-path',
        required=True,
        help='Path to SQLite database'
    )
    parser.add_argument(
        '--example-id',
        required=True,
        help='Example ID to diagnose'
    )
    parser.add_argument(
        '--run-id',
        help='Optional run ID (for run-scoped state)'
    )
    parser.add_argument(
        '--out',
        required=True,
        help='Path to output diagnostic JSON'
    )

    args = parser.parse_args()

    # Validate inputs
    if not Path(args.db_path).exists():
        print(f"Error: Database not found at {args.db_path}", file=sys.stderr)
        sys.exit(1)

    # Run diagnostic
    try:
        report = diagnose_block_index_mismatch(
            args.db_path,
            args.example_id,
            args.run_id,
            args.out
        )

        # Print summary
        print("\n" + "="*80)
        print("Block Index Mismatch Diagnostic")
        print("="*80)
        print(f"Example ID: {report['example_id']}")
        print(f"File: {report.get('file_path', 'N/A')}")

        if 'error' in report:
            print(f"\nERROR: {report['error']}")
            sys.exit(1)

        print(f"\nStored Metadata:")
        stored = report['stored_metadata']
        print(f"  Block Index: {stored['block_index']}")
        print(f"  Start Line: {stored['start_line']}")
        print(f"  Language: {stored['language']}")
        print(f"  Signature: {stored['signature_short']}")
        if stored['extraction_warning']:
            print(f"  Warning: {stored['extraction_warning']}")

        print(f"\nParse Results:")
        parse = report['parse_results']
        print(f"  Total Blocks: {parse['total_blocks']}")
        print(f"  C# Blocks: {parse['csharp_blocks']}")

        print(f"\nAnalysis:")
        analysis = report['analysis']
        print(f"  Signature Matches: {analysis['signature_match_count']}")
        if analysis['signature_matches']:
            for match in analysis['signature_matches']:
                print(f"    - Block {match['index_all_fences']} (lines {match['start_line']}-{match['end_line']})")

        if analysis['block_at_stored_index']:
            block_info = analysis['block_at_stored_index']
            print(f"\n  Block at Stored Index {stored['block_index']}:")
            print(f"    Language: {block_info['language']}")
            print(f"    Signature Matches: {block_info['signature_matches']}")
            print(f"    Lines: {block_info['start_line']}-{block_info['end_line']}")

        print(f"\nDIAGNOSIS: {report['diagnosis']}")
        print("="*80)

        # Exit with error code if mismatch detected
        if 'MISMATCH' in report['diagnosis'] or 'ERROR' in report['diagnosis']:
            sys.exit(1)

    except Exception as e:
        print(f"Error during diagnosis: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
