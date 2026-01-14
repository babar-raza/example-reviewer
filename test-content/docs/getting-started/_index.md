---
title: Getting Started
description: >-
  Get started with compressing and decompressing ZIP archives in your .NET
  applications using Aspose.ZIP for .NET.
type: docs
sidebar:
  open: true
---
**Aspose.ZIP for .NET Getting Started Guide**

Welcome to the Aspose.ZIP for .NET getting started guide! This page provides an overview of the necessary steps to get started with using Aspose.ZIP in your .NET applications.

### System Requirements

* .NET Framework 4.0 or later (all versions)
* Windows Operating Systems
* ASP.NET Web Development Environment

### Installation

To start using Aspose.ZIP for .NET, you can download the DLL's from the following links:
- **NuGet Packages**: Install Aspose.ZIP NuGet package by running `Install-Package Aspose.Zip.` in your .NET project.
- **ZIP Archive**: Download Aspose.ZIP and include it in your project.

### Supported Formats

The Aspose.ZIP for .NET library allows you to read and write the following compress/expandible file formats:
* [ZIP](https://docs.aspose.net/file-formats/zip/)
* GZip (.gz)
* Tar (.tar, .tgz, .txtar, .tar.gz, .tar.bz2)

### Getting Started with Code Examples

Below are some simple code snippets for basic compression and decompression operations within your .NET project:

```csharp
// Create ZIP archive and add files.
using (var archive = new Archive()) // Instantiate an archive
{
   archive.CreateEntry("test.txt", "data.bin"); // Add an entry from file
   archive.Save("archive.zip"); // Save composed archive to file
}
```
