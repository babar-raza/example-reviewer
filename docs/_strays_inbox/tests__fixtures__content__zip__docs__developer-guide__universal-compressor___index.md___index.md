---
weight: 1
title: Universal Compressor for .NET
description: Compress directories into ZIP, 7z, TAR, and CPIO formats with the Aspose.ZIP Universal Compressor for .NET plugin. A simple and efficient solution for directory compression in .NET applications.
type: docs
---

Aspose.ZIP Universal Compressor for .NET is a lightweight plugin that simplifies directory compression into multiple archive formats. Whether you need to package content for distribution, create backups, or prepare archives for storage and transfer, this plugin provides an easy-to-use API built on the Aspose.ZIP library. It supports widely used formats like **ZIP**, **7z**, **TAR**, and **CPIO**, enabling broad compatibility across systems and workflows.

## Installation and Setup

1. Install the **Aspose.ZIP** package in your project via NuGet Package Manager or Package Manager Console.
2. Configure your license keys to enable full, watermark-free functionality.
3. Supported platforms:

   * **Operating Systems**: Windows, Linux (.NET Core 2.0+), macOS (10.12+)
   * **Frameworks**: .NET Framework 2.0–4.8, .NET Standard 2.0, .NET Core, and newer
   * **Development Environments**: Visual Studio 2010–2022

For detailed instructions, see the [Installation Guide](https://docs.aspose.com/zip/net/installation/).

## Features and Functionalities

* **Multi-Format Support**: Compress directories into **ZIP, 7z, TAR, and CPIO** formats.
* **Simple API**: One-line method to compress entire directories with minimal configuration.
* **Cross-Platform Compatibility**: Works seamlessly across Windows, Linux, and macOS environments.
* **Enterprise Ready**: Supports metered licensing and scalable integration for large applications.

## How to Compress Directories via C# .NET

The following snippet shows how to compress a directory using the plugin:

```csharp
using Aspose.Zip;

// Compress a directory into a ZIP archive
ArchiveFactory.CompressDirectory("C:\\InputDirectory", "C:\\OutputArchive.zip");

// Compress into a 7z archive
ArchiveFactory.CompressDirectory("C:\\InputDirectory", "C:\\OutputArchive.7z");

// Compress into a TAR archive
ArchiveFactory.CompressDirectory("C:\\InputDirectory", "C:\\OutputArchive.tar");
```

This code uses the `ArchiveFactory.CompressDirectory` method to compress a source directory into the desired archive format.

## Best Practices

* Always validate the target directory path before starting compression to avoid runtime errors.
* Choose the right format for your scenario:

  * **ZIP** for general-purpose use and compatibility
  * **7z** for higher compression ratios
  * **TAR/CPIO** for Unix/Linux workflows
* Monitor compression performance on large directories and consider running the process in background tasks for UI applications.
* Keep your Aspose.ZIP library updated to benefit from performance optimizations and new features.
