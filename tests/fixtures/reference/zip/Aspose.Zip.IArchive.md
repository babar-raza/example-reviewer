---
linkTitle: "Interface IArchive"
title: "Interface IArchive"
description: "This interface represents an archive."
summary: "This interface represents an archive."
categories:
  - Interface
layout: "reference-single"
---

Namespace: [Aspose.Zip](/zip/)  
Assembly: Aspose.Zip.dll (25.12.0)  

This interface represents an archive.

```csharp
public interface IArchive : IDisposable
```

#### Implements

[IDisposable](https://learn.microsoft.com/dotnet/api/system.idisposable)

## Properties

### <a id="Aspose_Zip_IArchive_FileEntries"></a> FileEntries

Gets entries of Aspose.Zip.IArchiveFileEntry type constituting the archive.

```csharp
IEnumerable<IArchiveFileEntry> FileEntries { get; }
```

#### Property Value

 [IEnumerable](https://learn.microsoft.com/dotnet/api/system.collections.generic.ienumerable\-1)<[IArchiveFileEntry](/zip/aspose.zip.iarchivefileentry)\>

#### Remarks

Archives for compression only, such as gzip, bzip2, lzip, lzma, lz4, xz, z consist of the single record - the archive itself.

### <a id="Aspose_Zip_IArchive_Format"></a> Format

Gets the archive format.

```csharp
ArchiveFormat Format { get; }
```

#### Property Value

 [ArchiveFormat](/zip/aspose.zip.archiveinfo.archiveformat)

## Methods

### <a id="Aspose_Zip_IArchive_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

Extracts all the files in the archive to the directory provided.

```csharp
void ExtractToDirectory(string destinationDirectory)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory to place the extracted files in.

#### Remarks

If the directory does not exist, it will be created.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">destinationDirectory</code> is null.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified path, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters and file names must be less than 260 characters.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access the existing directory.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

If the directory does not exist, a path contains a colon character (:) that is not part of a drive label ("C:\").

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destinationDirectory</code> is a zero-length string, contains only white space, or contains one or more invalid characters. You can query for invalid characters by using the System.IO.Path.GetInvalidPathChars method. -or- path is prefixed with, or contains, only a colon character (:).

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The directory specified by path is a file. -or- The network name is not known.
