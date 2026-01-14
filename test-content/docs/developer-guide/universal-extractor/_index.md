---
weight: 2
title: Universal Extractor for .NET
description: Extract and decompress archives in multiple formats including ZIP, RAR, 7Z, TAR, and GZIP using the Universal Extractor plugin in Aspose.ZIP for .NET.
type: docs
---
The **Universal Extractor for .NET** is a specialized plugin within the [Aspose.ZIP for .NET](https://products.aspose.net/zip/) library. It provides a simplified interface to extract and decompress archives across multiple formats such as **ZIP, RAR, 7Z, TAR, GZIP, and BZIP2**. This plugin is designed for developers who require efficient extraction capabilities without needing the complete API surface of Aspose.ZIP.

## Installation and Setup

1. Add the Aspose.ZIP package to your project via NuGet:

   ```bash
   dotnet add package Aspose.ZIP
   ```
2. Configure your license keys to unlock full features (see [Metered Licensing](https://docs.aspose.net/zip/net/licensing/)).
3. For supported frameworks and environments, check the [Installation Guide](https://docs.aspose.net/zip/getting-started/).

Compatible with:

* **Operating Systems:** Windows, macOS (10.12+), Linux (with .NET Core 2.0+)
* **Frameworks:** .NET Framework 2.0–4.8, .NET Standard 2.0+, .NET Core, .NET 5–7
* **IDEs:** Microsoft Visual Studio 2010–2022 and JetBrains Rider

## Supported Archive Formats

The Universal Extractor plugin supports extracting archives from the following formats:

* **ZIP** (.zip)
* **RAR** (.rar) — including RAR4 and RAR5
* **7Z** (.7z)
* **TAR** (.tar)
* **GZIP** (.gz)
* **BZIP2** (.bz2)

## Features and Functionalities

### Extract Entire Archives

```csharp
using Aspose.Zip;

using (var archive = new Archive("example.zip"))
{
    archive.ExtractToDirectory("extracted");
}
```

This extracts all files from the archive into the specified `extracted` directory.

### Extract Password-Protected Archives

```csharp
using Aspose.Zip;

using (var archive = new Archive("example.zip", new ArchiveLoadOptions { DecryptionPassword = "YOUR-PASSWORD" }))
{
    archive.ExtractToDirectory("extracted");
}
```

This extracts the contents of a password-protected [ZIP](https://docs.aspose.net/file-formats/zip/) archive.

### List Archive Contents

```csharp
using Aspose.Zip;

using (var archive = new Archive("example.zip"))
{
    foreach (var entry in archive.Entries)
    {
        Console.WriteLine(entry.Name);
    }
}
```

This lists all entries in the archive without extracting them.

### Extract Specific Files

```csharp
using Aspose.Zip;

using (var archive = new Archive("example.zip"))
{
    var entry = archive.Entries[0];
    entry.Extract("firstFile.txt");
}
```

This extracts only the first file in the archive to the output path.

## Best Practices

* Always use the latest version of **Aspose.ZIP** for maximum compatibility and bug fixes.
* Implement error handling to manage corrupted or unsupported archive cases gracefully.
* Use password handling securely when working with protected archives.
* For large archives, prefer **stream extraction** to avoid high memory consumption.
* Validate archive format before extraction to ensure compatibility with your workflow.

## Frequently Asked Questions

**Can Universal Extractor handle formats other than ZIP?**
Yes. It supports multiple formats including RAR, 7Z, TAR, GZIP, and BZIP2.

**Does it support encrypted archives?**
Yes, password-protected archives are supported by supplying the password during archive loading.

**Can I list files before extracting them?**
Yes, by iterating over the `Entries` property you can inspect archive contents.

**Is Universal Extractor multi-thread safe?**
Yes, you can safely use it in multi-threaded environments, provided each archive instance is processed independently.

**Is extraction the only feature provided?**
Yes, this plugin focuses solely on archive extraction. For advanced compression or archive creation, use the full Aspose.ZIP API.

---

With **Aspose.ZIP Universal Extractor for .NET**, you can easily integrate archive decompression into your .NET applications, whether you’re handling ZIP attachments in an email client, batch-extracting [RAR](https://docs.aspose.net/file-formats/rar/) archives, or integrating 7Z extraction into automated pipelines.
