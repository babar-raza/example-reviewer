# Evidence: Snippets 139 & 140 Investigation

**Task**: T3
**Agent**: A (Discovery)
**Date**: 2026-01-12 14:10
**Status**: COMPLETE

---

## Snippet 139: ASP.NET Core Minimal API

### Original Code
```csharp
// File: Program.cs (minimal API)
using System.Text;
using Aspose.Zip;
using Aspose.Zip.Saving;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/download-zip", () =>
{
    using var buffer = new MemoryStream();
    var deflate = new DeflateCompressionSettings(CompressionLevel.Normal);
    var settings = new ArchiveEntrySettings(deflate);

    using (var archive = new Archive())
    {
        // Add dynamic content
        using (var ms = new MemoryStream(Encoding.UTF8.GetBytes("id,name\n1,Alice\n2,Bob\n")))
            archive.CreateEntry("data/users.csv", ms, settings);

        // Add static file
        var logo = "wwwroot/logo.png";
        if (File.Exists(logo))
        {
            using var fs = File.OpenRead(logo);
            archive.CreateEntry("assets/logo.png", fs, settings);
        }

        archive.Save(buffer);
    }

    buffer.Position = 0;
    return Results.File(
        fileContents: buffer.ToArray(),
        contentType: "application/zip",
        fileDownloadName: $"bundle-{DateTime.UtcNow:yyyyMMdd-HHmmss}.zip");
});

app.Run();
```

### Analysis

**Code Type**: ASP.NET Core minimal API (top-level statements)
**Framework**: ASP.NET Core 6.0+
**Issues**:
1. **Missing ASP.NET usings**: `WebApplication`, `Results` not imported
2. **CompressionLevel issue**: Same as snippet 138 (doesn't exist in Aspose.Zip)
3. **Top-level statements**: Uses implicit Program class (C# 9.0+)

### Compilation Errors Evolution (Run 29)

**Attempts 1-2**:
```
CS0103: The name 'WebApplication' does not exist in the current context
CS0103: The name 'args' does not exist in the current context
```
**Issue**: Missing ASP.NET Core using statements

**Attempt 3**:
```
CS0103: The name 'CompressionLevel' does not exist in the current context
CS1729: 'DeflateCompressionSettings' does not contain a constructor that takes 1 arguments
CS0103: The name 'Results' does not exist in the current context
```
**Issue**: LLM partially fixed ASP.NET usings but `CompressionLevel` and `Results` still missing

**Attempts 4-6**:
```
CS0246: The type or namespace name 'FileStreamResult' could not be found
```
**Issue**: LLM tried alternative return type `FileStreamResult` (which also doesn't exist properly)

---

## Snippet 140: Stream ZIP Response

### Original Code
```csharp
app.MapGet("/stream-zip", async (HttpContext ctx) =>
{
    ctx.Response.ContentType = "application/zip";
    ctx.Response.Headers.ContentDisposition = $"attachment; filename=\"bundle.zip\"";

    var deflate = new DeflateCompressionSettings(CompressionLevel.Normal);
    var settings = new ArchiveEntrySettings(deflate);

    using var archive = new Archive();

    // Add entries...
    using var ms = new MemoryStream(Encoding.UTF8.GetBytes("hello"));
    archive.CreateEntry("hello.txt", ms, settings);

    // Stream directly to the client without buffering full ZIP in RAM
    await archive.SaveAsync(ctx.Response.Body);
});
```

### Analysis

**Code Type**: Continuation of snippet 139 (depends on `app` variable)
**Framework**: ASP.NET Core 6.0+
**Issues**:
1. **Depends on snippet 139**: References `app` variable from snippet 139
2. **Cannot compile standalone**: This is a code fragment, not standalone code
3. **Missing usings**: `HttpContext`, `Microsoft.AspNetCore.Http`
4. **CompressionLevel issue**: Same as snippets 138 and 139
5. **SaveAsync issue**: Method is in `non_existent_apis` list (line 31-34 of zip.json)

### Compilation Errors (Run 29, All Attempts)

**All 4 attempts**:
```
CS0103: The name 'app' does not exist in the current context
CS0246: The type or namespace name 'HttpContext' could not be found
```

**Issue**: Code cannot compile without `app` from snippet 139. Context inference won't help because `app` is runtime, not code structure.

---

## Error Pattern Classification

### Pattern 1: Missing Framework Using Statements (Snippet 139)
**Error**: `WebApplication`, `Results`, `HttpContext` not found
**Root Cause**: ASP.NET Core minimal API code without ASP.NET Core usings
**Fix**: Add pattern for ASP.NET Core minimal API setup

### Pattern 2: CompressionLevel (Snippets 139, 140)
**Error**: `CompressionLevel` doesn't exist, constructor signature wrong
**Root Cause**: Same as snippet 138 - using System.IO.Compression enum instead of Aspose.Zip patterns
**Fix**: Already fixed with negative guidance and patterns (snippet 138 successful)

### Pattern 3: Non-Existent Async Methods (Snippet 140)
**Error**: `SaveAsync` usage
**Root Cause**: Code uses async method not in Aspose.Zip API
**Fix**: Already in `non_existent_apis` list, need to reinforce in prompt

### Pattern 4: Code Fragment Dependencies (Snippet 140)
**Error**: `app` variable not in scope
**Root Cause**: Snippet 140 is continuation of 139, cannot compile standalone
**Fix**: **NOT FIXABLE** - would require validating multiple snippets together

---

## Required API Patterns

### Pattern 1: ASP.NET Core Minimal API Setup
```csharp
// Required usings for ASP.NET Core minimal API
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;

// Minimal API setup
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

// Returning files from endpoints
app.MapGet("/endpoint", () => {
    byte[] fileBytes = ...;
    return Results.File(fileBytes, "application/zip", "filename.zip");
});

app.Run();
```

### Pattern 2: HttpContext Response Manipulation
```csharp
// Setting response headers and content type
app.MapGet("/endpoint", async (HttpContext ctx) => {
    ctx.Response.ContentType = "application/zip";
    ctx.Response.Headers["Content-Disposition"] = "attachment; filename=\"file.zip\"";

    // Write directly to response
    await ctx.Response.Body.WriteAsync(data);
});
```

### Pattern 3: Aspose.Zip SaveAsync Alternative
```csharp
// WRONG: SaveAsync doesn't exist
await archive.SaveAsync(stream); // ❌

// CORRECT: Use synchronous Save
archive.Save(stream); // ✅

// CORRECT: Wrap in Task if needed in async context
await Task.Run(() => archive.Save(stream)); // ✅
```

---

## Recommendations

### Snippet 139: FIXABLE
**Probability of Success**: HIGH (80-90%)

**Required Actions**:
1. Add ASP.NET Core minimal API pattern to family config
2. CompressionLevel fix already implemented (from snippet 138)
3. Results.File pattern needed

**Expected Iterations**: 3-5

### Snippet 140: LIKELY UNFIXABLE
**Probability of Success**: LOW (10-20%)

**Blockers**:
1. **Code fragment**: Depends on `app` from snippet 139
2. **Runtime dependency**: Cannot be resolved through patterns
3. **Would require**: Multi-snippet context (not currently supported)

**Options**:
1. **Mark as "needs-manual-fix"**: Document why unfixable
2. **Skip validation**: Add flag to skip continuation snippets
3. **Multi-snippet support** (future): Validate related snippets together

**Recommendation**: Mark snippet 140 as "needs-manual-fix" with reason: "Code fragment depending on previous snippet runtime context"

---

## Acceptance Criteria Check

- [x] Original code retrieved for both snippets
- [x] Compilation errors retrieved (Run 29)
- [x] All LLM attempts and code evolution retrieved
- [x] Error patterns identified and classified
- [x] Required API patterns identified
- [x] Evidence document created with patterns needed

---

## Commands Executed

```bash
./venv/Scripts/python.exe -c "[database query for snippets 139, 140 data and errors]"
```

**Files Read**:
- `data/examples.db` (snippets 139, 140 data, Run 29 build attempts)

---

**Agent A Conclusion**:
- **Snippet 139**: FIXABLE with ASP.NET Core patterns
- **Snippet 140**: LIKELY UNFIXABLE (code fragment dependency)
- Ready to hand off to Agent B for pattern implementation (snippet 139 only)
