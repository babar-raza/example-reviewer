---
title: "Create 7z Archives in C# with Aspose.ZIP"
seoTitle: "C# 7z Archive Creation with Aspose.ZIP"
description: "A complete C# guide to creating 7z archives with Aspose.ZIP. Learn how to add files and folders, set entry names, and save reliable 7z archives."

date: "2025-07-18"
draft: false
author: "Babar Raza"
summary: "A step-by-step, production-ready guide for building 7z archives in C# using Aspose.ZIP. Includes adding files from disk and streams, organizing entry names, and saving to .7z."
tags: ["csharp", "7z-archive", "aspose-zip", "file-compression", "dotnet"]
categories: ["Aspose.ZIP Plugin Family"]
---

The 7z format is a popular choice for high-ratio compression and distribution. With **Aspose.ZIP for .NET**, you can create 7z archives programmatically using a simple, modern API. This guide walks through a minimal working example and adds practical patterns for real projects, such as adding files from disk, streaming data from memory, controlling entry names and folders inside the archive, and basic error handling.

All code samples are inline and self-contained.

---

## Prerequisites

* .NET 6 or later
* NuGet package `Aspose.Zip`

```bash
dotnet add package Aspose.Zip
```

> Namespaces used in the samples:
> `Aspose.Zip`, `Aspose.Zip.SevenZip`

---

## Quick start: create a 7z archive with a few files

This minimal example creates a new 7z archive in memory, adds two entries, and saves it to disk.

```csharp
// File: Program.cs
using System;
using System.IO;
using System.Text;
using Aspose.Zip.SevenZip;

class Program
{
    static void Main()
    {
        var outputPath = "example.7z";

        using (var archive = new SevenZipArchive())
        {
            // Add a text file from memory
            using (var ms = new MemoryStream(Encoding.UTF8.GetBytes("Hello 7z from Aspose.ZIP")))
            {
                archive.CreateEntry("docs/readme.txt", ms);
            }

            // Add a file from disk
            var sourceFile = "report.pdf"; // ensure this file exists
            if (File.Exists(sourceFile))
            {
                using var fs = File.OpenRead(sourceFile);
                archive.CreateEntry("reports/2025/report.pdf", fs);
            }

            // Save the 7z archive
            using var outStream = File.Create(outputPath);
            archive.Save(outStream);
        }

        Console.WriteLine("Saved 7z: " + Path.GetFullPath(outputPath));
    }
}
```

**What to notice**

* `SevenZipArchive` starts empty, then you call `CreateEntry(entryName, stream)` per item.
* Entry names define the folder structure inside the archive, such as `docs/readme.txt`.
* You can pass any readable `Stream`, which is useful for data that you generate in memory.

---

## Add an entire folder tree

Walk a directory recursively, preserve its relative structure inside the archive, and save as `.7z`.

```csharp
using System;
using System.IO;
using Aspose.Zip.SevenZip;

static class FolderTo7z
{
    public static void CreateFromFolder(string sourceDir, string output7z)
    {
        if (!Directory.Exists(sourceDir))
            throw new DirectoryNotFoundException(sourceDir);

        using var archive = new SevenZipArchive();

        var basePath = Path.GetFullPath(sourceDir);
        foreach (var filePath in Directory.GetFiles(basePath, "*", SearchOption.AllDirectories))
        {
            var relPath = Path.GetRelativePath(basePath, filePath)
                              .Replace(Path.DirectorySeparatorChar, '/'); // normalize to forward slashes

            using var fs = File.OpenRead(filePath);
            archive.CreateEntry(relPath, fs);
        }

        using var outStream = File.Create(output7z);
        archive.Save(outStream);
    }
}

// Usage
// FolderTo7z.CreateFromFolder(@"C:\data\input", "bundle.7z");
```

**Tips**

* Use `Path.GetRelativePath` to keep the internal folder layout clean.
* Normalize path separators to forward slashes for consistent archive entries.

---

## Stream large files safely

When adding large files, stream them rather than buffering the entire file in memory. The basic pattern above with `File.OpenRead` already streams. If you generate content on the fly, write it to a `Stream` and pass that stream directly to `CreateEntry`.

```csharp
using System.IO;
using System.Text;
using Aspose.Zip.SevenZip;

static void AddGeneratedCsv(SevenZipArchive archive, string entryName)
{
    // Example generator that writes CSV rows in a forward-only fashion
    using var pipe = new MemoryStream();
    using var writer = new StreamWriter(pipe, Encoding.UTF8, leaveOpen: true);

    writer.WriteLine("id,name");
    for (int i = 1; i <= 1000; i++)
        writer.WriteLine($"{i},Item {i}");

    writer.Flush();
    pipe.Position = 0;

    archive.CreateEntry(entryName, pipe);
}
```

---

## Organize entries with a helper

For larger jobs, use a small helper to add files with a common prefix. This keeps your archive structure predictable.

```csharp
using System.IO;
using Aspose.Zip.SevenZip;

static class SevenZipHelpers
{
    public static void AddFile(SevenZipArchive archive, string rootPrefix, string fullPath)
    {
        var relName = Path.Combine(rootPrefix, Path.GetFileName(fullPath))
                           .Replace(Path.DirectorySeparatorChar, '/');
        using var fs = File.OpenRead(fullPath);
        archive.CreateEntry(relName, fs);
    }
}
```

---

## End-to-end example with logging and basic checks

This example creates a 7z archive from a mixed list of sources. It validates paths and logs results.

```csharp
// File: BuildArchive.cs
using System;
using System.Collections.Generic;
using System.IO;
using Aspose.Zip.SevenZip;

public static class BuildArchive
{
    public static bool Run(IEnumerable<string> paths, string output7z)
    {
        if (paths == null) throw new ArgumentNullException(nameof(paths));
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output7z)) ?? ".");

        int added = 0, skipped = 0;

        using var archive = new SevenZipArchive();

        foreach (var p in paths)
        {
            if (string.IsNullOrWhiteSpace(p)) { skipped++; continue; }

            if (File.Exists(p))
            {
                using var fs = File.OpenRead(p);
                var entryName = Path.GetFileName(p);
                archive.CreateEntry(entryName, fs);
                Console.WriteLine("Added file: " + entryName);
                added++;
            }
            else if (Directory.Exists(p))
            {
                var basePath = Path.GetFullPath(p);
                foreach (var fp in Directory.GetFiles(basePath, "*", SearchOption.AllDirectories))
                {
                    var rel = Path.GetRelativePath(basePath, fp).Replace(Path.DirectorySeparatorChar, '/');
                    using var fs = File.OpenRead(fp);
                    archive.CreateEntry(rel, fs);
                    Console.WriteLine("Added: " + rel);
                    added++;
                }
            }
            else
            {
                Console.WriteLine("Skip missing: " + p);
                skipped++;
            }
        }

        using var outStream = File.Create(output7z);
        archive.Save(outStream);

        Console.WriteLine($"Saved: {Path.GetFullPath(output7z)}");
        Console.WriteLine($"Entries added: {added}, skipped: {skipped}");
        return added > 0;
    }
}

// Usage sample:
// BuildArchive.Run(new [] { "README.md", "assets", "docs/spec.pdf" }, "release.7z");
```

---

## Best practices

* **Use forward slashes for entry names**
  Many tools display paths more consistently when entries use `/` as the separator.

* **Dispose streams**
  Always wrap file streams in `using` blocks. The samples above ensure clean disposal.

* **Validate inputs**
  Check that files exist before adding them. Provide clear logs for skipped paths.

* **Keep archive structure clean**
  Decide on a root folder name inside the archive and stick to it, such as `app/` or `package/`.

* **Test on target platforms**
  Verify that your 7z opens correctly in the tools your users rely on.

---

## Summary

You created a 7z archive programmatically with **Aspose.ZIP for .NET**, added files from disk and memory, preserved a clean folder structure, and saved the result to `.7z`. Use these patterns to package releases, bundles, and exports directly from your C# applications.
