---
linkTitle: "Class ArchiveFactory"
title: "Class ArchiveFactory"
description: "Detects the archive format and creates the appropriate  object according to the type of archive."
summary: "Detects the archive format and creates the appropriate  object according to the type of archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip](/zip/)  
Assembly: Aspose.Zip.dll (25.12.0)  

Detects the archive format and creates the appropriate Aspose.Zip.IArchive object according to the type of archive.

```csharp
public static class ArchiveFactory
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ArchiveFactory](/zip/aspose.zip.archivefactory)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Methods

### <a id="Aspose_Zip_ArchiveFactory_CompressDirectory_System_String_System_String_Aspose_Zip_ArchiveInfo_ArchiveFormat_"></a> CompressDirectory\(string, string, ArchiveFormat\)

Compresses the specified directory into an archive file using the provided archive format.

```csharp
public static void CompressDirectory(string path, string outputFileName, ArchiveFormat archiveFormat)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory that will be compressed.

`outputFileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

Destination file name.

`archiveFormat` [ArchiveFormat](/zip/aspose.zip.archiveinfo.archiveformat)

The format of the archive to create (e.g., zip, rar, tar, etc.).

#### Examples

Here is an example of how to use the CompressDirectory method:

```csharp
string directoryPath = @"C:\path\to\your\directory";
ArchiveInfo.ArchiveFormat format = ArchiveInfo.ArchiveFormat.Zip;
ArchiveFactory.CompressDirectory(directoryPath, "result", format);
// This will create a ZIP file with the contents of the directory at the specified path.
```

#### Remarks

This method will create an archive file at the location specified by the <code class="paramref">path</code> parameter.
The name of the archive file will typically be the directory name followed by the appropriate file extension
based on the <code class="paramref">archiveFormat</code>. The directory itself is not modified or deleted.

#### Exceptions

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

Thrown if the directory specified by <code class="paramref">path</code> does not exist.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

Thrown if <code class="paramref">path</code> is null or an empty string.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

Thrown if the specified <code class="paramref">archiveFormat</code> is not supported or recognized.

### <a id="Aspose_Zip_ArchiveFactory_GetArchive_System_String_"></a> GetArchive\(string\)

Detects the archive format and creates the appropriate Aspose.Zip.IArchive object according to the type of archive specified by the given path.

```csharp
public static IArchive GetArchive(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive to be analyzed.

#### Returns

 [IArchive](/zip/aspose.zip.iarchive)

An Aspose.Zip.IArchive object representing the archive.

### <a id="Aspose_Zip_ArchiveFactory_GetArchive_System_IO_Stream_"></a> GetArchive\(Stream\)

Detects the archive format and creates the appropriate Aspose.Zip.IArchive object according to the type of archive specified by the given stream.

```csharp
public static IArchive GetArchive(Stream stream)
```

#### Parameters

`stream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The stream containing the archive data. It must be seekable.

#### Returns

 [IArchive](/zip/aspose.zip.iarchive)

An Aspose.Zip.IArchive object representing the archive.

### <a id="Aspose_Zip_ArchiveFactory_GetArchive_System_IO_Stream_System_String_"></a> GetArchive\(Stream, string\)

Detects the archive format and creates the appropriate Aspose.Zip.IArchive object according to the type of encrypted archive specified by the given stream.

```csharp
public static IArchive GetArchive(Stream stream, string password)
```

#### Parameters

`stream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The stream containing the archive data. It must be seekable.

`password` [string](https://learn.microsoft.com/dotnet/api/system.string)

Password to decrypt an encrypted archive.

#### Returns

 [IArchive](/zip/aspose.zip.iarchive)

An Aspose.Zip.IArchive object representing the archive.
