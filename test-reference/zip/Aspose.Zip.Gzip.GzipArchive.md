---
linkTitle: "Class GzipArchive"
title: "Class GzipArchive"
description: "This class represents a gzip archive file. Use it to compose or extract gzip archives."
summary: "This class represents a gzip archive file. Use it to compose or extract gzip archives."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Gzip](/zip/aspose.zip.gzip)  
Assembly: Aspose.Zip.dll (25.12.0)  

This class represents a gzip archive file. Use it to compose or extract gzip archives.

```csharp
public class GzipArchive : IArchive, IDisposable, IArchiveFileEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[GzipArchive](/zip/aspose.zip.gzip.gziparchive)

#### Implements

[IArchive](/zip/aspose.zip.iarchive), 
[IDisposable](https://learn.microsoft.com/dotnet/api/system.idisposable), 
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

Gzip compression algorithm is based on the DEFLATE algorithm, which is a combination of LZ77 and Huffman coding.

## Constructors

### <a id="Aspose_Zip_Gzip_GzipArchive__ctor"></a> GzipArchive\(\)

Initializes a new instance of the Aspose.Zip.Gzip.GzipArchive class prepared for compressing.

```csharp
public GzipArchive()
```

#### Examples

<p>
        The following example shows how to compress a file.
        </p>

```csharp
using (GzipArchive archive = new GzipArchive()) 
{
    archive.SetSource("data.bin");
    archive.Save("archive.gz");
}
```

### <a id="Aspose_Zip_Gzip_GzipArchive__ctor_System_IO_Stream_System_Boolean_"></a> GzipArchive\(Stream, bool\)

Initializes a new instance of the Aspose.Zip.Gzip.GzipArchive class prepared for decompressing.

```csharp
public GzipArchive(Stream sourceStream, bool parseHeader = false)
```

#### Parameters

`sourceStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

`parseHeader` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether to parse stream header to figure out properties, including name. Makes sense for seekable stream only.

#### Examples

<p>Open an archive from a stream and extract it to a <code>MemoryStream</code></p>

```csharp
var ms = new MemoryStream();
using (GzipArchive archive = new GzipArchive(File.OpenRead("archive.gz")))
  archive.Open().CopyTo(ms);
```

#### Remarks

This constructor does not decompress. See Aspose.Zip.Gzip.GzipArchive.Open method for decompressing.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">sourceStream</code> is null.

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

<code class="paramref">sourceStream</code> is too short.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The <code class="paramref">sourceStream</code> has wrong signature.

### <a id="Aspose_Zip_Gzip_GzipArchive__ctor_System_IO_Stream_Aspose_Zip_Gzip_GzipLoadOptions_"></a> GzipArchive\(Stream, GzipLoadOptions\)

Initializes a new instance of the Aspose.Zip.Gzip.GzipArchive class prepared for decompressing.

```csharp
public GzipArchive(Stream sourceStream, GzipLoadOptions options)
```

#### Parameters

`sourceStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

`options` [GzipLoadOptions](/zip/aspose.zip.gzip.gziploadoptions)

Options to load the archive with.

#### Examples

<p>Open an archive from a stream and extract it to a <code>MemoryStream</code></p>

```csharp
var ms = new MemoryStream();
GzipLoadOptions options = new GzipLoadOptions();
using (GzipArchive archive = new GzipArchive(File.OpenRead("archive.gz"), options))
  archive.Extract(ms);
```

#### Remarks

This constructor does not decompress. See Aspose.Zip.Gzip.GzipArchive.Open method for decompressing.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">sourceStream</code> is null.

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

<code class="paramref">sourceStream</code> is too short.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The <code class="paramref">sourceStream</code> has wrong signature.

### <a id="Aspose_Zip_Gzip_GzipArchive__ctor_System_String_Aspose_Zip_Gzip_GzipLoadOptions_"></a> GzipArchive\(string, GzipLoadOptions\)

Initializes a new instance of the Aspose.Zip.Gzip.GzipArchive class prepared for decompressing.

```csharp
public GzipArchive(string path, GzipLoadOptions options)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

`options` [GzipLoadOptions](/zip/aspose.zip.gzip.gziploadoptions)

Options to load the archive with.

#### Examples

<p>Open an archive from file by path and extract it to a <code>MemoryStream</code></p>

```csharp
var ms = new MemoryStream();
GzipLoadOptions options = new GzipLoadOptions();
using (GzipArchive archive = new GzipArchive("archive.gz", options))
  archive.Extract(ms);
```

#### Remarks

This constructor does not decompress. See Aspose.Zip.Gzip.GzipArchive.Open method for decompressing.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">path</code> is empty, contains only white spaces, or contains invalid characters.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">path</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">path</code> contains a colon (:) in the middle of the string.

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

The file is too short.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Data in the file has the wrong signature.

### <a id="Aspose_Zip_Gzip_GzipArchive__ctor_System_String_System_Boolean_"></a> GzipArchive\(string, bool\)

Initializes a new instance of the Aspose.Zip.Gzip.GzipArchive class prepared for decompressing.

```csharp
public GzipArchive(string path, bool parseHeader = false)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

`parseHeader` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether to parse stream header to figure out properties, including name. Makes sense for seekable stream only.

#### Examples

<p>Open an archive from file by path and extract it to a <code>MemoryStream</code></p>

```csharp
var ms = new MemoryStream();
using (GzipArchive archive = new GzipArchive("archive.gz"))
  archive.Open().CopyTo(ms);
```

#### Remarks

This constructor does not decompress. See Aspose.Zip.Gzip.GzipArchive.Open method for decompressing.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">path</code> is empty, contains only white spaces, or contains invalid characters.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">path</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">path</code> contains a colon (:) in the middle of the string.

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

The file is too short.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Data in the file has the wrong signature.

## Properties

### <a id="Aspose_Zip_Gzip_GzipArchive_Name"></a> Name

Name of the original file.

```csharp
public string Name { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Gzip_GzipArchive_UncompressedSize"></a> UncompressedSize

Gets size of an original file.

```csharp
public ulong UncompressedSize { get; }
```

#### Property Value

 [ulong](https://learn.microsoft.com/dotnet/api/system.uint64)

#### Remarks

During decompression, this property may contain incorrect size. If the uncompressed file size exceeds 4GB, this property will give a wrong value due to the 32-bit limit in header.

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

## Methods

### <a id="Aspose_Zip_Gzip_GzipArchive_Dispose"></a> Dispose\(\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_Gzip_GzipArchive_Dispose_System_Boolean_"></a> Dispose\(bool\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
protected virtual void Dispose(bool disposing)
```

#### Parameters

`disposing` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether managed resources should be disposed.

### <a id="Aspose_Zip_Gzip_GzipArchive_Extract_System_IO_Stream_"></a> Extract\(Stream\)

Extracts the archive to the stream provided.

```csharp
public void Extract(Stream destination)
```

#### Parameters

`destination` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream. Must be writable.

#### Examples


```csharp
using (var archive = new GzipArchive("archive.gz"))
{
     archive.Extract(httpResponseStream);
}
```

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destination</code> does not support writing.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Stream is corrupted and does not contain valid data.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

### <a id="Aspose_Zip_Gzip_GzipArchive_Extract_System_String_"></a> Extract\(string\)

Extracts the archive to the file by path.

```csharp
public FileInfo Extract(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to destination file. If the file already exists, it will be overwritten.

#### Returns

 [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

Info of the extracted file.

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

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

### <a id="Aspose_Zip_Gzip_GzipArchive_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

Extracts content of the archive to the directory provided.

```csharp
public void ExtractToDirectory(string destinationDirectory)
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

If the directory does not exist, path contains a colon character (:) that is not part of a drive label ("C:\").

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destinationDirectory</code> is a zero-length string, contains only white space, or contains one or more invalid characters. You can query for invalid characters by using the System.IO.Path.GetInvalidPathChars method. 
        -or- path is prefixed with, or contains, only a colon character (:).

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The directory specified by path is a file. -or- The network name is not known.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

### <a id="Aspose_Zip_Gzip_GzipArchive_Open"></a> Open\(\)

Opens the archive for extraction and provides a stream with archive content.

```csharp
public Stream Open()
```

#### Returns

 [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The stream that represents the contents of the archive.

#### Examples

<p>Extracts the archive and copies extracted content to file stream.</p>

```csharp
using (var archive = new GzipArchive("archive.gz"))
{
    using (var extracted = File.Create("data.bin"))
    {
        using (var unpacked = archive.Open())
        {
            byte[] b = new byte[8192];
            int bytesRead;
            while (0 &lt; (bytesRead = unpacked.Read(b, 0, b.Length)))
                extracted.Write(b, 0, bytesRead);
        }
    }            
}
```
<p>
        You may use Stream.CopyTo method for .NET 4.0 and higher:
        `unpacked.CopyTo(extracted);`</p>

#### Remarks

Read from the stream to get the original content of a file. See examples section.

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Gzip_GzipArchive_Save_System_IO_Stream_"></a> Save\(Stream\)

Saves archive to the stream provided.

```csharp
public void Save(Stream outputStream)
```

#### Parameters

`outputStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

#### Examples

<p>Write compressed data to http response stream.</p>

```csharp
using (var archive = new GzipArchive()) 
{
    archive.SetSource(new FileInfo("data.bin"));
    archive.Save(httpResponse.OutputStream);
}
```

#### Remarks

<p>
  <code class="paramref">outputStream</code> must be writable.</p>

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">outputStream</code> is not writable.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

Source has not been supplied.

### <a id="Aspose_Zip_Gzip_GzipArchive_Save_System_String_"></a> Save\(string\)

Saves archive to the destination file provided.

```csharp
public void Save(string destinationFileName)
```

#### Parameters

`destinationFileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

#### Examples


```csharp
using (var archive = new GzipArchive())
{
    archive.SetSource("data.bin");
    archive.Save("archive.gz");
}
```

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">destinationFileName</code> is null.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">destinationFileName</code> is empty, contains only white spaces, or contains invalid characters.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">destinationFileName</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">destinationFileName</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">destinationFileName</code> contains a colon (:) in the middle of the string.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Gzip_GzipArchive_SetSource_System_IO_Stream_"></a> SetSource\(Stream\)

Sets the content to be compressed within the archive.

```csharp
public void SetSource(Stream source)
```

#### Parameters

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The input stream for the archive.

#### Examples


```csharp
using (var archive = new GzipArchive())
{
    archive.SetSource(new MemoryStream(new byte[] { 0x00, 0xFF }));
    archive.Save("archive.gz");
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Gzip_GzipArchive_SetSource_System_IO_FileInfo_"></a> SetSource\(FileInfo\)

Sets the content to be compressed within the archive.

```csharp
public void SetSource(FileInfo fileInfo)
```

#### Parameters

`fileInfo` [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

The reference to a file to be compressed.

#### Examples


```csharp
using (var archive = new GzipArchive()) 
{
    archive.SetSource(new FileInfo("data.bin"));
    archive.Save("archive.gz");
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Gzip_GzipArchive_SetSource_System_String_"></a> SetSource\(string\)

Sets the content to be compressed within the archive.

```csharp
public void SetSource(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

Path to file to be compressed.

#### Examples


```csharp
using (var archive = new GzipArchive()) 
{
    archive.SetSource("data.bin");
    archive.Save("archive.gz");
}
```

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">path</code> is empty, contains only white spaces, or contains invalid characters.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">path</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">path</code> contains a colon (:) in the middle of the string.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Gzip_GzipArchive_SetSource_Aspose_Zip_Tar_TarArchive_"></a> SetSource\(TarArchive\)

Sets the content to be compressed within the archive.

```csharp
public void SetSource(TarArchive tarArchive)
```

#### Parameters

`tarArchive` [TarArchive](/zip/aspose.zip.tar.tararchive)

Tar archive to be compressed.

#### Examples


```csharp
using (var tarArchive = new TarArchive())
{
    tarArchive.CreateEntry("first.bin", "data1.bin");
    tarArchive.CreateEntry("second.bin", "data2.bin");
    using (var gzippedArchive = new GzipArchive())
    {
           gzippedArchive.SetSource(tarArchive);
           gzippedArchive.Save("archive.tar.gz");
    }
}
```

#### Remarks

Use this method to compose joint tar.gz archive.

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.
