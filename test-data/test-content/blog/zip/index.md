# Test Aspose.ZIP Example

This is a test document to verify the pipeline with Aspose.ZIP.

## Extract ZIP Archive

Here's a simple example showing how to extract a ZIP archive:

```csharp
using System;
using System.IO;
using Aspose.Zip;

// Open the ZIP archive
using (var archive = new Archive("sample.zip"))
{
    // Extract all entries to a directory
    archive.ExtractToDirectory("output");
    Console.WriteLine("Extraction completed successfully!");
}
```

## Create ZIP Archive

Another example showing how to create a ZIP archive:

```csharp
using System;
using System.IO;
using Aspose.Zip;
using Aspose.Zip.Saving;

// Create a new archive
var settings = new ArchiveEntrySettings(new DeflateCompressionSettings());
using (var archive = new Archive(settings))
{
    // Add a file to the archive
    archive.CreateEntry("alice29.txt", "test-data/zip/alice29.txt");

    // Save the archive
    archive.Save("output.zip");
    Console.WriteLine("Archive created successfully!");
}
```
