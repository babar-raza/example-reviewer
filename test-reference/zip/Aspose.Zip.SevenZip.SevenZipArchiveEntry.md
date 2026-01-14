---
linkTitle: "Class SevenZipArchiveEntry"
title: "Class SevenZipArchiveEntry"
description: "Represents a single file within 7z archive."
summary: "Represents a single file within 7z archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.SevenZip](/zip/aspose.zip.sevenzip)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents a single file within 7z archive.

```csharp
public abstract class SevenZipArchiveEntry : IArchiveFileEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[SevenZipArchiveEntry](/zip/aspose.zip.sevenzip.sevenziparchiveentry)

#### Derived

[SevenZipArchiveEntryEncrypted](/zip/aspose.zip.sevenzip.sevenziparchiveentryencrypted), 
[SevenZipArchiveEntryPlain](/zip/aspose.zip.sevenzip.sevenziparchiveentryplain)

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

## Remarks

Cast an Aspose.Zip.SevenZip.SevenZipArchiveEntry instance to Aspose.Zip.SevenZip.SevenZipArchiveEntryEncrypted to determine whether the entry encrypted or not.

## Properties

### <a id="Aspose_Zip_SevenZip_SevenZipArchiveEntry_CompressedSize"></a> CompressedSize

Gets the size of a compressed file.

```csharp
public ulong CompressedSize { get; }
```

#### Property Value

 [ulong](https://learn.microsoft.com/dotnet/api/system.uint64)

### <a id="Aspose_Zip_SevenZip_SevenZipArchiveEntry_CompressionSettings"></a> CompressionSettings

Gets settings for compression or decompression.

```csharp
public SevenZipCompressionSettings CompressionSettings { get; }
```

#### Property Value

 [SevenZipCompressionSettings](/zip/aspose.zip.saving.sevenzipcompressionsettings)

### <a id="Aspose_Zip_SevenZip_SevenZipArchiveEntry_FileAttributes"></a> FileAttributes

Gets file attributes from a host system.

```csharp
protected FileAttributes FileAttributes { get; }
```

#### Property Value

 [FileAttributes](https://learn.microsoft.com/dotnet/api/system.io.fileattributes)

### <a id="Aspose_Zip_SevenZip_SevenZipArchiveEntry_IsDirectory"></a> IsDirectory

Gets a value indicating whether the entry represents a directory.

```csharp
public bool IsDirectory { get; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_SevenZip_SevenZipArchiveEntry_ModificationTime"></a> ModificationTime

Gets last modified date and time.

```csharp
public DateTime ModificationTime { get; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_SevenZip_SevenZipArchiveEntry_Name"></a> Name

Gets name of the entry within the archive.

```csharp
public string Name { get; protected set; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_SevenZip_SevenZipArchiveEntry_Source"></a> Source

Gets the data source stream for the entry.

```csharp
protected Stream Source { get; }
```

#### Property Value

 [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

### <a id="Aspose_Zip_SevenZip_SevenZipArchiveEntry_UncompressedSize"></a> UncompressedSize

Gets size of an original file.

```csharp
public ulong UncompressedSize { get; }
```

#### Property Value

 [ulong](https://learn.microsoft.com/dotnet/api/system.uint64)

## Methods

### <a id="Aspose_Zip_SevenZip_SevenZipArchiveEntry_Extract_System_String_System_String_"></a> Extract\(string, string\)

Extracts the entry to the filesystem by the path provided.

```csharp
public FileInfo Extract(string path, string password = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to destination file. If the file already exists, it will be overwritten.

`password` [string](https://learn.microsoft.com/dotnet/api/system.string)

Optional password for decryption.

#### Returns

 [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

The file info of a composed file.

#### Examples


```csharp
using (var archive = new SevenZipArchive("archive.7z"))
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

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The archive is corrupted.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

### <a id="Aspose_Zip_SevenZip_SevenZipArchiveEntry_Extract_System_IO_Stream_System_String_"></a> Extract\(Stream, string\)

Extracts the entry to the stream provided.

```csharp
public void Extract(Stream destination, string password = null)
```

#### Parameters

`destination` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream. Must be writable.

`password` [string](https://learn.microsoft.com/dotnet/api/system.string)

Optional password for decryption.

#### Examples

<p>Extract an entry of zip archive with password.</p>

```csharp
using (var archive = new SevenZipArchive("archive.7z"))
{
    archive.Entries[0].Extract(httpResponseStream);
}
```

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destination</code> does not support writing.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is not opened for extraction. - or - This entry is a directory.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Wrong data within the entry.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

### <a id="Aspose_Zip_SevenZip_SevenZipArchiveEntry_FinalizeCompressedData_System_IO_Stream_System_Byte___"></a> FinalizeCompressedData\(Stream, byte\[\]\)

Write to output stream any headers that follow compressed data.

```csharp
protected abstract int FinalizeCompressedData(Stream outputStream, byte[] encoderProperties)
```

#### Parameters

`outputStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Output stream for the entry.

`encoderProperties` [byte](https://learn.microsoft.com/dotnet/api/system.byte)\[\]

Properties of compressor.

#### Returns

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

Number of "technical" bytes that were added after entry significant data block.

### <a id="Aspose_Zip_SevenZip_SevenZipArchiveEntry_GetDestinationStream_System_IO_Stream_"></a> GetDestinationStream\(Stream\)

Destination stream for the entry, may be decorated.

```csharp
protected abstract Stream GetDestinationStream(Stream outputStream)
```

#### Parameters

`outputStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Output stream for the entry.

#### Returns

 [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The destination stream for entry compression.

### <a id="Aspose_Zip_SevenZip_SevenZipArchiveEntry_Open_System_String_"></a> Open\(string\)

Opens the entry for extraction and provides a stream with entry content.

```csharp
public Stream Open(string password = null)
```

#### Parameters

`password` [string](https://learn.microsoft.com/dotnet/api/system.string)

Optional password for decryption.

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

#### Exceptions

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is not opened for extraction. - or - This entry is a directory.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Wrong data within the entry.

### <a id="Aspose_Zip_SevenZip_SevenZipArchiveEntry_CompressionProgressed"></a> CompressionProgressed

Raises when a portion of raw stream compressed.

```csharp
public event EventHandler<ProgressEventArgs> CompressionProgressed
```

#### Event Type

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[ProgressEventArgs](/zip/aspose.zip.progresseventargs)\>

#### Examples

`archive.Entries[0].CompressionProgressed += (s, e) =&gt; { int percent = (int)((100 * (long)e.ProceededBytes) / entrySourceStream.Length); };`

#### Remarks

<p>Event sender is an Aspose.Zip.SevenZip.SevenZipArchiveEntry instance.</p>
<p>Does not invoke in solid mode and in multithreaded mode for LZMA2 entries.</p>
