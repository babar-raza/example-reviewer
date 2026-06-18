---
linkTitle: "Class ArjEntryPlain"
title: "Class ArjEntryPlain"
description: "Represents a single file within ARJ archive."
summary: "Represents a single file within ARJ archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Arj](/zip/aspose.zip.arj)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents a single file within ARJ archive.

```csharp
public class ArjEntryPlain : IArchiveFileEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ArjEntryPlain](/zip/aspose.zip.arj.arjentryplain)

#### Implements

[IArchiveFileEntry](/zip/aspose.zip.iarchivefileentry)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Properties

### <a id="Aspose_Zip_Arj_ArjEntryPlain_CompressedSize"></a> CompressedSize

Gets the size of a compressed file.

```csharp
public uint CompressedSize { get; }
```

#### Property Value

 [uint](https://learn.microsoft.com/dotnet/api/system.uint32)

### <a id="Aspose_Zip_Arj_ArjEntryPlain_Name"></a> Name

Gets name of the entry within the archive.

```csharp
public string Name { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_Arj_ArjEntryPlain_UncompressedSize"></a> UncompressedSize

Gets size of an original file.

```csharp
public uint UncompressedSize { get; }
```

#### Property Value

 [uint](https://learn.microsoft.com/dotnet/api/system.uint32)

## Methods

### <a id="Aspose_Zip_Arj_ArjEntryPlain_Extract_System_String_"></a> Extract\(string\)

Extracts the entry to the filesystem by the path provided.

```csharp
public FileInfo Extract(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to destination file. If the file already exists, it will be overwritten.

#### Returns

 [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

The file info of a composed file.

#### Examples

<p>Extract two entries of rar archive.</p>

```csharp
using (FileStream arjFile = File.Open("archive.arj", FileMode.Open))
{
    using (ArjArchive archive = new ArjArchive(arjFile))
    {
        archive.Entries[0].Extract("first.bin");
        archive.Entries[1].Extract("second.bin");
    }
}
```

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null or empty.

### <a id="Aspose_Zip_Arj_ArjEntryPlain_Extract_System_IO_FileInfo_"></a> Extract\(FileInfo\)

Extracts ARJ archive entry to a file.

```csharp
public void Extract(FileInfo fileInfo)
```

#### Parameters

`fileInfo` [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

FileInfo for storing decompressed data.

#### Examples


```csharp
using (var arjFile = File.Open(sourceFileName, FileMode.Open))
{
    using (var archive = new ArjArchive(arjFile))
    {
        archive.Entries[0].Extract(new FileInfo("extracted.bin"));
    }
}
```

#### Exceptions

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

Archive headers and service information were not read.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to open the <code class="paramref">fileInfo</code>.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The file path is empty or contains only white spaces.

 [FileNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.filenotfoundexception)

The file is not found.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Path to file is read-only or is a directory.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">fileInfo</code> is null.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified path is invalid, such as being on an unmapped drive.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The file is already open.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

### <a id="Aspose_Zip_Arj_ArjEntryPlain_Extract_System_IO_Stream_"></a> Extract\(Stream\)

Extracts the entry to the stream provided.

```csharp
public void Extract(Stream destination)
```

#### Parameters

`destination` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream. Must be writable.

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destination</code> does not support writing.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Checksum mismatch for headers or data. - or - Archive is corrupted.

 [NotImplementedException](https://learn.microsoft.com/dotnet/api/system.notimplementedexception)

Entry compressed with method 4.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.
