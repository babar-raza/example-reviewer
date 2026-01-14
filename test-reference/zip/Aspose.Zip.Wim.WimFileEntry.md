---
linkTitle: "Class WimFileEntry"
title: "Class WimFileEntry"
description: "Represents a single file within wim archive."
summary: "Represents a single file within wim archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Wim](/zip/aspose.zip.wim)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents a single file within wim archive.

```csharp
public sealed class WimFileEntry : WimEntry, IArchiveFileEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[WimEntry](/zip/aspose.zip.wim.wimentry) ← 
[WimFileEntry](/zip/aspose.zip.wim.wimfileentry)

#### Implements

[IArchiveFileEntry](/zip/aspose.zip.iarchivefileentry)

#### Inherited Members

[WimEntry.ToString\(\)](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_ToString), 
[WimEntry.Archive](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_Archive), 
[WimEntry.Image](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_Image), 
[WimEntry.Parent](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_Parent), 
[WimEntry.Name](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_Name), 
[WimEntry.ShortName](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_ShortName), 
[WimEntry.FullPath](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_FullPath), 
[WimEntry.ChangeTime](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_ChangeTime), 
[WimEntry.CreationTime](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_CreationTime), 
[WimEntry.LastAccessTime](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_LastAccessTime), 
[WimEntry.LastWriteTime](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_LastWriteTime), 
[WimEntry.ModificationTime](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_ModificationTime), 
[WimEntry.FileAttributes](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_FileAttributes), 
[WimEntry.AlternateDataStreams](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_AlternateDataStreams), 
[WimEntry.HardLink](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_HardLink), 
[WimEntry.HasHardLinks](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_HasHardLinks), 
[WimEntry.IsDirectory](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_IsDirectory), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Properties

### <a id="Aspose_Zip_Wim_WimFileEntry_Length"></a> Length

Gets the length of the entry in bytes.

```csharp
public long Length { get; }
```

#### Property Value

 [long](https://learn.microsoft.com/dotnet/api/system.int64)

## Methods

### <a id="Aspose_Zip_Wim_WimFileEntry_Extract_System_String_"></a> Extract\(string\)

Extracts the entry to the filesystem by the path provided.

```csharp
public FileInfo Extract(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to destination file. If the file already exists, it will be overwritten.

#### Returns

 [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

The file info of the composed file.

#### Examples


```csharp
using (var archive = new WimArchive("archive.wim"))
{
    archive.Images[0].RootDirectory.Files[0].Extract("data.bin");
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

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The archive is corrupted.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

### <a id="Aspose_Zip_Wim_WimFileEntry_Extract_System_IO_Stream_"></a> Extract\(Stream\)

Extracts the entry to the stream provided.

```csharp
public void Extract(Stream destination)
```

#### Parameters

`destination` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream. Must be writable.

#### Examples

<p>Extract an entry of wim archive.</p>

```csharp
using (var archive = new WimArchive("archive.wim"))
{
    archive.Images[0].RootDirectory.Files[0].Extract(httpResponseStream);
}
```

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destination</code> does not support writing.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The archive is corrupted.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

### <a id="Aspose_Zip_Wim_WimFileEntry_Open"></a> Open\(\)

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
