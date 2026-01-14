---
linkTitle: "Class CpioEntry"
title: "Class CpioEntry"
description: "Represents single file within cpio archive."
summary: "Represents single file within cpio archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Cpio](/zip/aspose.zip.cpio)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents single file within cpio archive.

```csharp
public sealed class CpioEntry : IArchiveFileEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[CpioEntry](/zip/aspose.zip.cpio.cpioentry)

#### Implements

[IArchiveFileEntry](/zip/aspose.zip.iarchivefileentry)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Properties

### <a id="Aspose_Zip_Cpio_CpioEntry_IsDirectory"></a> IsDirectory

Gets a value indicating whether the entry represents a directory.

```csharp
public bool IsDirectory { get; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_Cpio_CpioEntry_LastWriteTimeUtc"></a> LastWriteTimeUtc

Gets the last write time.

```csharp
public DateTime LastWriteTimeUtc { get; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_Cpio_CpioEntry_Length"></a> Length

Gets the length of the entry in bytes.

```csharp
public long Length { get; }
```

#### Property Value

 [long](https://learn.microsoft.com/dotnet/api/system.int64)

### <a id="Aspose_Zip_Cpio_CpioEntry_Name"></a> Name

Gets name of the entry within the archive.

```csharp
public string Name { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_Cpio_CpioEntry_Parent"></a> Parent

Gets the archive the entry belongs to.

```csharp
public CpioArchive Parent { get; }
```

#### Property Value

 [CpioArchive](/zip/aspose.zip.cpio.cpioarchive)

## Methods

### <a id="Aspose_Zip_Cpio_CpioEntry_Extract_System_String_"></a> Extract\(string\)

Extracts the entry to the filesystem by the path provided.

```csharp
public FileSystemInfo Extract(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to destination file. If the file already exists, it will be overwritten.

#### Returns

 [FileSystemInfo](https://learn.microsoft.com/dotnet/api/system.io.filesysteminfo)

The file info of a composed file.

#### Examples


```csharp
using (var archive = new CpioArchive("archive.cpio"))
{
    archive.Entries[0].Extract("data.bin");
}
```

#### Exceptions

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

 [FileNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.filenotfoundexception)

The file is not found.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified path is invalid, such as being on an unmapped drive.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The file is already open.

### <a id="Aspose_Zip_Cpio_CpioEntry_Extract_System_IO_Stream_"></a> Extract\(Stream\)

Extracts the entry to the stream provided.

```csharp
public void Extract(Stream destination)
```

#### Parameters

`destination` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream. Must be writable.

#### Examples

<p>Extract an entry of cpio archive.</p>

```csharp
using (var archive = new CpioArchive("archive.cpio"))
{
    archive.Entries[0].Extract(httpResponseStream);
}
```

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destination</code> does not support writing.

### <a id="Aspose_Zip_Cpio_CpioEntry_Open"></a> Open\(\)

Opens the entry for extraction and provides a stream with entry content.

```csharp
public Stream Open()
```

#### Returns

 [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The stream that represents the contents of the entry.

#### Examples

Usage:
`Stream decompressed = entry.Open();`<p>
.NET 4.0 and higher - use Stream.CopyTo method:
`decompressed.CopyTo(httpResponse.OutputStream)`</p><p>
.NET 3.5 and before - copy bytes manually:

```csharp
byte[] buffer = new byte[8192];
int bytesRead;
while (0 &lt; (bytesRead = decompressed.Read(buffer, 0, buffer.Length)))
 fileStream.Write(buffer, 0, bytesRead);
```</p>

#### Remarks

Read from the stream to get the original content of a file. See examples section.

### <a id="Aspose_Zip_Cpio_CpioEntry_ToString"></a> ToString\(\)

```csharp
public override string ToString()
```

#### Returns

 [string](https://learn.microsoft.com/dotnet/api/system.string)
