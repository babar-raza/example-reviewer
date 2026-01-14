---
linkTitle: "Class LzxArchiveEntry"
title: "Class LzxArchiveEntry"
description: "Represents a single file within LZX archive."
summary: "Represents a single file within LZX archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Lzx](/zip/aspose.zip.lzx)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents a single file within LZX archive.

```csharp
public class LzxArchiveEntry : IArchiveFileEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[LzxArchiveEntry](/zip/aspose.zip.lzx.lzxarchiveentry)

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

### <a id="Aspose_Zip_Lzx_LzxArchiveEntry_Commentary"></a> Commentary

Gets the commentary.

```csharp
public string Commentary { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_Lzx_LzxArchiveEntry_CompressedSize"></a> CompressedSize

Gets size of the compressed file.

```csharp
public uint CompressedSize { get; }
```

#### Property Value

 [uint](https://learn.microsoft.com/dotnet/api/system.uint32)

### <a id="Aspose_Zip_Lzx_LzxArchiveEntry_IsDirectory"></a> IsDirectory

Gets a value indicating whether this entry is a directory.

```csharp
public bool IsDirectory { get; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_Lzx_LzxArchiveEntry_Length"></a> Length

Gets the length of the entry in bytes.

```csharp
public long? Length { get; }
```

#### Property Value

 [long](https://learn.microsoft.com/dotnet/api/system.int64)?

### <a id="Aspose_Zip_Lzx_LzxArchiveEntry_ModificationTime"></a> ModificationTime

Gets the last modified time of the entry.

```csharp
public DateTime ModificationTime { get; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_Lzx_LzxArchiveEntry_Name"></a> Name

Gets name of the entry.

```csharp
public string Name { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

#### Remarks

Archives for compression only, such as gzip, bzip2, lzip, lzma, xz, z has name "File.bin" unless another name can be found in headers.

### <a id="Aspose_Zip_Lzx_LzxArchiveEntry_UncompressedSize"></a> UncompressedSize

Gets size of the original file.

```csharp
public uint UncompressedSize { get; }
```

#### Property Value

 [uint](https://learn.microsoft.com/dotnet/api/system.uint32)

## Methods

### <a id="Aspose_Zip_Lzx_LzxArchiveEntry_Extract_System_String_"></a> Extract\(string\)

Extracts Lzx archive entry to a filesystem by path.

```csharp
public FileSystemInfo Extract(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

Path to file which will store decompressed data.

#### Returns

 [FileSystemInfo](https://learn.microsoft.com/dotnet/api/system.io.filesysteminfo)

System.IO.FileSystemInfoInstance containing extracted data.

#### Examples


```csharp
using (FileStream lzxFile = File.Open(sourceFileName, FileMode.Open))
{
    using (var archive = new LzxArchive(lhaFile))
    {
        archive.Entries[0].Extract("extracted.bin");
    }
}
```

#### Exceptions

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

Archive headers and service information were not read.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">path</code> is empty, contains only white spaces, or contains invalid characters.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">path</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">path</code> contains a colon (:) in the middle of the string.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Checksum mismatch for headers or data. - or - Archive is corrupted.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

Invalid compression method.

### <a id="Aspose_Zip_Lzx_LzxArchiveEntry_Extract_System_IO_Stream_"></a> Extract\(Stream\)

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

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

Destination stream is null.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

Invalid compression method.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.
