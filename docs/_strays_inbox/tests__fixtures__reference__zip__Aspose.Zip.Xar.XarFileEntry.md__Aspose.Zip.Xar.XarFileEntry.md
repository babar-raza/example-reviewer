---
linkTitle: "Class XarFileEntry"
title: "Class XarFileEntry"
description: "Represents file entry within xar archive."
summary: "Represents file entry within xar archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Xar](/zip/aspose.zip.xar)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents file entry within xar archive.

```csharp
public sealed class XarFileEntry : XarEntry, IArchiveFileEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[XarEntry](/zip/aspose.zip.xar.xarentry) ← 
[XarFileEntry](/zip/aspose.zip.xar.xarfileentry)

#### Implements

[IArchiveFileEntry](/zip/aspose.zip.iarchivefileentry)

#### Inherited Members

[XarEntry.ToString\(\)](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_ToString), 
[XarEntry.Name](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_Name), 
[XarEntry.FullPath](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_FullPath), 
[XarEntry.IsDirectory](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_IsDirectory), 
[XarEntry.Parent](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_Parent), 
[XarEntry.CreationTime](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_CreationTime), 
[XarEntry.LastAccessTime](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_LastAccessTime), 
[XarEntry.LastWriteTime](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_LastWriteTime), 
[XarEntry.ModificationTime](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_ModificationTime), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Properties

### <a id="Aspose_Zip_Xar_XarFileEntry_Length"></a> Length

Gets the length of the entry in bytes.

```csharp
public long Length { get; }
```

#### Property Value

 [long](https://learn.microsoft.com/dotnet/api/system.int64)

## Methods

### <a id="Aspose_Zip_Xar_XarFileEntry_Extract_System_String_"></a> Extract\(string\)

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
using (var archive = new XarArchive("archive.xar"))
{
    ((XarFileEntry)archive.Entries[0]).Extract("data.bin");
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

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The archive is corrupted.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

### <a id="Aspose_Zip_Xar_XarFileEntry_Extract_System_IO_Stream_"></a> Extract\(Stream\)

Extracts the entry to the stream provided.

```csharp
public void Extract(Stream destination)
```

#### Parameters

`destination` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream. Must be writable.

#### Examples

<p>Extract an entry of xar archive.</p>

```csharp
using (var archive = new XarArchive("archive.xar"))
{
    ((XarFileEntry)archive.Entries[0]).Extract(httpResponseStream);
}
```

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destination</code> does not support writing.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The archive is corrupted.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

### <a id="Aspose_Zip_Xar_XarFileEntry_Open"></a> Open\(\)

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

### <a id="Aspose_Zip_Xar_XarFileEntry_CompressionProgressed"></a> CompressionProgressed

Raises when a portion of raw stream compressed.

```csharp
public event EventHandler<ProgressEventArgs> CompressionProgressed
```

#### Event Type

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[ProgressEventArgs](/zip/aspose.zip.progresseventargs)\>

#### Examples

`archive.Entries.First().CompressionProgressed += (s, e) =&gt; { int percent = (int)((100 * (long)e.ProceededBytes) / entrySourceStream.Length); };`

#### Remarks

Event sender is an Aspose.Zip.Xar.XarFileEntry instance.
