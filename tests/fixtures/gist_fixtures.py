"""Test fixtures for gist integration tests.

Provides sample data for testing gist parsing, fetching, and caching.
"""

# Gist shortcode formats discovered during HARD-001

# Mixed format (unquoted owner/ID, quoted filename) - ACTUAL Aspose format
MIXED_FORMAT_SHORTCODE = '{{< gist aspose-com-gists 78c04f45434d446c01e3543fdd084192 "GenerateAndDisplayBarcode_ASP.NET_MVC_Barcode.cs" >}}'

# Fully quoted format (legacy)
QUOTED_FORMAT_SHORTCODE = '{{< gist "aspose-com-gists" "78c04f45434d446c01e3543fdd084192" "GenerateAndDisplayBarcode_ASP.NET_MVC_Barcode.cs" >}}'

# Mixed format without filename
MIXED_NO_FILENAME = '{{< gist aspose-com-gists 78c04f45434d446c01e3543fdd084192 >}}'

# Quoted format without filename
QUOTED_NO_FILENAME = '{{< gist "aspose-com-gists" "78c04f45434d446c01e3543fdd084192" >}}'

# No space after {{<
COMPACT_MIXED = '{{<gist aspose-com-gists 78c04f45434d446c01e3543fdd084192 "Example.cs">}}'
COMPACT_QUOTED = '{{<gist "aspose-com-gists" "78c04f45434d446c01e3543fdd084192" "Example.cs">}}'

# Fully unquoted (edge case)
UNQUOTED_FORMAT = '{{< gist aspose-com-gists 78c04f45434d446c01e3543fdd084192 Example.cs >}}'

# Malformed shortcodes (should fail to parse)
MALFORMED_SHORTCODES = [
    '{{< gist >}}',  # No parameters
    '{{< gist "owner" >}}',  # Missing gist ID
    '{{< gist owner >}}',  # Only one parameter
    '{{< git owner id "file" >}}',  # Wrong shortcode name
    'gist owner id "file"',  # Missing Hugo syntax
]

# Real gist from HARD-001 (for integration tests)
REAL_GIST_OWNER = "aspose-com-gists"
REAL_GIST_ID = "78c04f45434d446c01e3543fdd084192"
REAL_GIST_FILE = "GenerateAndDisplayBarcode_ASP.NET_MVC_Barcode.cs"
REAL_GIST_DESCRIPTION = "Generate and Display Barcode Image in ASP.NET MVC"

# Expected parse results
EXPECTED_PARSE_RESULT = (REAL_GIST_OWNER, REAL_GIST_ID, REAL_GIST_FILE)
EXPECTED_PARSE_NO_FILE = (REAL_GIST_OWNER, REAL_GIST_ID, None)

# Mock gist API response (for unit tests without network)
MOCK_GIST_RESPONSE = {
    "id": REAL_GIST_ID,
    "description": REAL_GIST_DESCRIPTION,
    "created_at": "2022-04-04T16:41:08Z",
    "updated_at": "2022-04-04T16:41:08Z",
    "files": {
        REAL_GIST_FILE: {
            "filename": REAL_GIST_FILE,
            "type": "text/plain",
            "language": "C#",
            "raw_url": f"https://gist.githubusercontent.com/{REAL_GIST_OWNER}/{REAL_GIST_ID}/raw/Example.cs",
            "size": 203,
            "content": """// Barcode basic information
public class Barcode
{
    public string Text { get; set; }

    public BarcodeType BarcodeType { get; set; }

    public ImageType ImageType { get; set; }
}"""
        }
    }
}

# Mock gist with multiple files
MOCK_MULTI_FILE_GIST = {
    "id": "multifile123",
    "description": "Multi-file gist",
    "files": {
        "File1.cs": {
            "filename": "File1.cs",
            "language": "C#",
            "content": "// File 1"
        },
        "File2.cs": {
            "filename": "File2.cs",
            "language": "C#",
            "content": "// File 2"
        }
    }
}

# Mock 404 response
MOCK_404_GIST_ID = "notfound404"
