---
title: "Aspose.ZIP Runtime Smoke Test"
description: "Minimal smoke test for runtime validation with Aspose.ZIP"
date: 2026-01-14
author: "Bootstrap Script"
type: post
url: /zip/runtime-smoke/
---

# Aspose.ZIP Runtime Smoke Test

This page contains minimal C# snippets for testing the runtime validation pipeline.

## Basic ZIP Creation

This snippet creates a simple ZIP archive with a text entry using MemoryStream:

```csharp
using System;
using System.IO;
using System.Text;
using Aspose.Zip;
using Aspose.Zip.Saving;

// Create a simple ZIP archive
using (var memoryStream = new MemoryStream())
{
    using (var archive = new Archive())
    {
        // Add text content as an entry
        var textContent = "Hello from Aspose.ZIP!";
        var textBytes = Encoding.UTF8.GetBytes(textContent);

        using (var contentStream = new MemoryStream(textBytes))
        {
            archive.CreateEntry("hello.txt", contentStream);
        }

        // Save archive to memory stream
        archive.Save(memoryStream);

        Console.WriteLine($"ZIP created successfully. Size: {memoryStream.Length} bytes");
    }
}
```

## Multi-Entry Archive

This snippet demonstrates creating an archive with multiple entries:

```csharp
using System;
using System.IO;
using System.Text;
using Aspose.Zip;
using Aspose.Zip.Saving;

// Create archive with multiple text files
using (var outputStream = new MemoryStream())
{
    using (var archive = new Archive())
    {
        // Add first entry
        var content1 = Encoding.UTF8.GetBytes("First file content");
        using (var stream1 = new MemoryStream(content1))
        {
            archive.CreateEntry("file1.txt", stream1);
        }

        // Add second entry
        var content2 = Encoding.UTF8.GetBytes("Second file content");
        using (var stream2 = new MemoryStream(content2))
        {
            archive.CreateEntry("file2.txt", stream2);
        }

        // Save the archive
        archive.Save(outputStream);

        Console.WriteLine($"Archive created with {archive.Entries.Count} entries");
        Console.WriteLine($"Total size: {outputStream.Length} bytes");
    }
}
```
