"""
Specifically review and fix the in-memory ZIP blog post
This is the page mentioned in the email with critical issues
"""

import re
from pathlib import Path
from .example_fixer import AsposeZipExampleFixer

def fix_inmemory_blog():
    """Fix the in-memory ZIP blog post"""

    script_dir = Path(__file__).parent.parent
    content_root = script_dir.parent.parent / "content"
    validator_path = script_dir / "test-examples"

    blog_path = content_root / "blog.aspose.net" / "zip" / "csharp-zip-file-in-memory-aspose-zip" / "index.md"

    print("="*80)
    print("REVIEWING: In-Memory ZIP Blog Post")
    print("="*80)
    print(f"File: {blog_path}")
    print()

    # Read the file
    with open(blog_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print("Issues mentioned in email:")
    print("1. DeflateCompressionSettings does NOT accept parameters")
    print("2. SaveAsync does NOT exist (hallucination)")
    print("3. Stream disposal timing issue")
    print("4. Should use CreateEntries for directory compression")
    print()

    # Create fixer
    fixer = AsposeZipExampleFixer(str(validator_path))

    # Find all code blocks
    code_blocks = re.findall(r'```csharp\n(.*?)```', content, re.DOTALL)

    print(f"Found {len(code_blocks)} C# code blocks")
    print()

    issues_found = {
        'deflate_with_params': [],
        'save_async': [],
        'stream_disposal': [],
        'directory_iteration': []
    }

    # Analyze each code block
    for idx, code in enumerate(code_blocks, 1):
        print(f"Code Block {idx}:")
        print("-" * 40)

        # Check for DeflateCompressionSettings with parameters
        if re.search(r'DeflateCompressionSettings\s*\([^)]+\)', code):
            issues_found['deflate_with_params'].append(idx)
            print("  [X] DeflateCompressionSettings() with parameters (INCORRECT)")

        # Check for SaveAsync
        if 'SaveAsync' in code:
            issues_found['save_async'].append(idx)
            print("  [X] SaveAsync() method (DOES NOT EXIST)")

        # Check for stream disposal timing issue
        if re.search(r'using\s*\([^)]*Stream[^)]*\)\s*\{[^}]*CreateEntry', code, re.DOTALL):
            # Check if Save is called after the using block
            if 'Save(' in code:
                issues_found['stream_disposal'].append(idx)
                print("  [!]  Potential stream disposal timing issue")

        # Check for directory iteration
        if 'Directory.GetFiles' in code or 'GetFiles' in code:
            issues_found['directory_iteration'].append(idx)
            print("  [i]  Manual directory iteration (could use CreateEntries)")

        # Check if block is clean
        if idx not in (issues_found['deflate_with_params'] +
                      issues_found['save_async'] +
                      issues_found['stream_disposal'] +
                      issues_found['directory_iteration']):
            print("  [OK] No issues detected")

        print()

    # Print summary
    print("="*80)
    print("ISSUES SUMMARY")
    print("="*80)
    print(f"DeflateCompressionSettings with params: {len(issues_found['deflate_with_params'])} blocks")
    if issues_found['deflate_with_params']:
        print(f"  Blocks: {issues_found['deflate_with_params']}")

    print(f"SaveAsync (hallucination): {len(issues_found['save_async'])} blocks")
    if issues_found['save_async']:
        print(f"  Blocks: {issues_found['save_async']}")

    print(f"Potential stream disposal issues: {len(issues_found['stream_disposal'])} blocks")
    if issues_found['stream_disposal']:
        print(f"  Blocks: {issues_found['stream_disposal']}")

    print(f"Manual directory iteration: {len(issues_found['directory_iteration'])} blocks")
    if issues_found['directory_iteration']:
        print(f"  Blocks: {issues_found['directory_iteration']}")

    print()

    # Now generate fixed version
    print("="*80)
    print("GENERATING FIXED VERSION")
    print("="*80)

    fixed_content = content

    # Fix 1: Remove parameters from DeflateCompressionSettings
    print("Fix 1: Removing parameters from DeflateCompressionSettings...")
    fixed_content = re.sub(
        r'new DeflateCompressionSettings\s*\([^)]+\)',
        'new DeflateCompressionSettings()',
        fixed_content
    )
    print("  [OK] Fixed")

    # Fix 2: Replace SaveAsync with Save
    print("Fix 2: Replacing SaveAsync with Save...")
    if 'SaveAsync' in fixed_content:
        fixed_content = fixed_content.replace('await archive.SaveAsync(', 'archive.Save(')
        fixed_content = fixed_content.replace('archive.SaveAsync(', 'archive.Save(')
        fixed_content = fixed_content.replace('SaveAsync', 'Save')
        print("  [OK] Fixed")
    else:
        print("  (No SaveAsync found)")

    # Fix 3: Add comment about stream disposal
    print("Fix 3: Adding notes about stream disposal timing...")
    # Find sections with using statements and CreateEntry
    fixed_content = re.sub(
        r'(using \([^)]*\bStream[^)]*\)[^{]*\{[^}]*CreateEntry[^}]*\})',
        r'// Note: Ensure streams remain valid until after archive.Save() is called\n\1',
        fixed_content,
        flags=re.DOTALL
    )

    # Fix 4: Add note about CreateEntries
    print("Fix 4: Adding note about CreateEntries method...")
    if 'Directory.GetFiles' in fixed_content or 'GetFiles' in fixed_content:
        # Add a note after directory compression examples
        note = """

**Note:** For compressing entire directories, you can use the `CreateEntries` method:

```csharp
using var archive = new Archive();
// Compress entire directory with one method call
archive.CreateEntries("path/to/directory", includeRootDirectory: false);
archive.Save("output.zip");
```

This is more efficient than manually iterating through files.

"""
        # Insert after the directory compression section
        if '## Add an entire folder tree' in fixed_content:
            fixed_content = fixed_content.replace(
                '---\n\n## ASP.NET Core:',
                f'{note}\n---\n\n## ASP.NET Core:'
            )

    print("  [OK] Added")

    # Save fixed version
    fixed_path = blog_path.parent / "index.md.fixed"
    with open(fixed_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)

    print()
    print(f"Fixed version saved to: {fixed_path}")
    print()
    print("NEXT STEPS:")
    print("1. Review the fixed version manually")
    print("2. Test the code examples")
    print("3. If satisfied, replace the original with: mv index.md.fixed index.md")
    print()


if __name__ == '__main__':
    fix_inmemory_blog()
