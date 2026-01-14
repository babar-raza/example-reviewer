---
linkTitle: "Class ZstandardArchive"
title: "Class ZstandardArchive"
description: "This class represents a Zstandard archive file. Use it to compose Zstandard archives."
summary: "This class represents a Zstandard archive file. Use it to compose Zstandard archives."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Zstandard](/zip/aspose.zip.zstandard)  
Assembly: Aspose.Zip.dll (25.12.0)  

This class represents a Zstandard archive file. Use it to compose Zstandard archives.

```csharp
public class ZstandardArchive : IArchive, IDisposable, IArchiveFileEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ZstandardArchive](/zip/aspose.zip.zstandard.zstandardarchive)

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

## Constructors

### <a id="Aspose_Zip_Zstandard_ZstandardArchive__ctor"></a> ZstandardArchive\(\)

Initializes a new instance of the Aspose.Zip.Zstandard.ZstandardArchive class prepared for compressing.

```csharp
public ZstandardArchive()
```

#### Examples

<p>
        The following example shows how to compress a file.
        </p>

```csharp
using (ZstandardArchive archive = new ZstandardArchive()) 
{
    archive.SetSource("data.bin");
    archive.Save("archive.zst");
}
```

### <a id="Aspose_Zip_Zstandard_ZstandardArchive__ctor_System_IO_Stream_Aspose_Zip_Zstandard_ZstandardLoadOptions_"></a> ZstandardArchive\(Stream, ZstandardLoadOptions\)

Initializes a new instance of the Aspose.Zip.Zstandard.ZstandardArchive class prepared for decompressing.

```csharp
public ZstandardArchive(Stream sourceStream, ZstandardLoadOptions options = null)
```

#### Parameters

`sourceStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

`options` [ZstandardLoadOptions](/zip/aspose.zip.zstandard.zstandardloadoptions)

The options to load archive with.

#### Examples

<p>Open an archive from a stream and extract it to a <code>MemoryStream</code></p>

```csharp
var ms = new MemoryStream();
using (GzipArchive archive = new ZstandardArchive(File.OpenRead("archive.zst")))
  archive.Open().CopyTo(ms);
```

#### Remarks

This constructor does not decompress. See Aspose.Zip.Zstandard.ZstandardArchive.Open method for decompressing.

### <a id="Aspose_Zip_Zstandard_ZstandardArchive__ctor_System_String_Aspose_Zip_Zstandard_ZstandardLoadOptions_"></a> ZstandardArchive\(string, ZstandardLoadOptions\)

Initializes a new instance of the Aspose.Zip.Zstandard.ZstandardArchive class.

```csharp
public ZstandardArchive(string path, ZstandardLoadOptions options = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

`options` [ZstandardLoadOptions](/zip/aspose.zip.zstandard.zstandardloadoptions)

The options to load archive with.

#### Examples

<p>Open an archive from file by path and extract it to a <code>MemoryStream</code></p>

```csharp
var ms = new MemoryStream();
using (ZstandardArchive archive = new ZstandardArchive("archive.zst"))
  archive.Open().CopyTo(ms);
```

#### Remarks

This constructor does not decompress. See Aspose.Zip.Zstandard.ZstandardArchive.Open method for decompressing.

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

## Methods

### <a id="Aspose_Zip_Zstandard_ZstandardArchive_Dispose"></a> Dispose\(\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_Zstandard_ZstandardArchive_Dispose_System_Boolean_"></a> Dispose\(bool\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
protected virtual void Dispose(bool disposing)
```

#### Parameters

`disposing` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether managed resources should be disposed.

### <a id="Aspose_Zip_Zstandard_ZstandardArchive_Extract_System_IO_Stream_"></a> Extract\(Stream\)

Extracts the archive to the stream provided.

```csharp
public void Extract(Stream destination)
```

#### Parameters

`destination` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream. Must be writable.

#### Examples


```csharp
using (var archive = new GzipArchive("archive.zst"))
{
     archive.Extract(httpResponseStream);
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destination</code> does not support writing.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

### <a id="Aspose_Zip_Zstandard_ZstandardArchive_Extract_System_String_"></a> Extract\(string\)

Extracts the archive to the file by path.

```csharp
public FileInfo Extract(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to destination file. If the file already exists, it will be overwritten.

#### Returns

 [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

Info of an extracted file.

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

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

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

### <a id="Aspose_Zip_Zstandard_ZstandardArchive_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

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

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">destinationDirectory</code> is null.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified path, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters and file names must be less than 260 characters.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access the existing directory.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

If the directory does not exist, the path contains a colon character (:) that is not part of a drive label ("C:\").

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destinationDirectory</code> is a zero-length string, contains only white space, or contains one or more invalid characters. You can query for invalid characters by using the System.IO.Path.GetInvalidPathChars method. 
        -or- path is prefixed with, or contains, only a colon character (:).

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The directory specified by path is a file. -or- The network name is not known.

### <a id="Aspose_Zip_Zstandard_ZstandardArchive_Open"></a> Open\(\)

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
using (var archive = new ZstandardArchive("archive.zst"))
{
    using (var extracted = File.Create("data.bin"))
    {
        var unpacked = archive.Open();
        byte[] b = new byte[8192];
        int bytesRead;
        while (0 &lt; (bytesRead = unpacked.Read(b, 0, b.Length)))
            extracted.Write(b, 0, bytesRead);
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

### <a id="Aspose_Zip_Zstandard_ZstandardArchive_Save_System_IO_Stream_Aspose_Zip_Zstandard_ZstandardSaveOptions_"></a> Save\(Stream, ZstandardSaveOptions\)

Saves archive to the stream provided.

```csharp
public void Save(Stream outputStream, ZstandardSaveOptions settings = null)
```

#### Parameters

`outputStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`settings` [ZstandardSaveOptions](/zip/aspose.zip.zstandard.zstandardsaveoptions)

Optional settings for archive composition.

#### Examples

<p>Write compressed data to http response stream.</p>

```csharp
using (var archive = new ZstandardArchive()) 
{
    archive.SetSource(new FileInfo("data.bin"));
    archive.Save(httpResponse.OutputStream);
}
```

#### Remarks

<p>
  <code class="paramref">outputStream</code> must be writable.</p>

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">outputStream</code> is not writable.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

Source has not been supplied.

### <a id="Aspose_Zip_Zstandard_ZstandardArchive_Save_System_String_Aspose_Zip_Zstandard_ZstandardSaveOptions_"></a> Save\(string, ZstandardSaveOptions\)

Saves archive to the destination file provided.

```csharp
public void Save(string destinationFileName, ZstandardSaveOptions settings = null)
```

#### Parameters

`destinationFileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`settings` [ZstandardSaveOptions](/zip/aspose.zip.zstandard.zstandardsaveoptions)

Optional settings for archive composition.

#### Examples


```csharp
using (var archive = new ZstandardArchive()) 
{
    archive.SetSource(new FileInfo("data.bin"));
    archive.Save("result.zst");
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">destinationFileName</code> is null.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">destinationFileName</code> is empty, contains only white spaces, or contains invalid characters.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">destinationFileName</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">destinationFileName</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">destinationFileName</code> contains a colon (:) in the middle of the string.

### <a id="Aspose_Zip_Zstandard_ZstandardArchive_Save_System_IO_FileInfo_Aspose_Zip_Zstandard_ZstandardSaveOptions_"></a> Save\(FileInfo, ZstandardSaveOptions\)

Saves archive to the destination file provided.

```csharp
public void Save(FileInfo destination, ZstandardSaveOptions settings = null)
```

#### Parameters

`destination` [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

FileInfo, which will be opened as destination stream.

`settings` [ZstandardSaveOptions](/zip/aspose.zip.zstandard.zstandardsaveoptions)

Optional settings for archive composition.

#### Examples


```csharp
using (var archive = new ZstandardArchive()) 
{
    archive.SetSource(new FileInfo("data.bin"));
    archive.Save(new FileInfo("archive.zst"));
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to open the <code class="paramref">destination</code>.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The file path is empty or contains only white spaces.

 [FileNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.filenotfoundexception)

The file is not found.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Path to file is read-only or is a directory.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">destination</code> is null.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified path is invalid, such as being on an unmapped drive.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The file is already open.

### <a id="Aspose_Zip_Zstandard_ZstandardArchive_SetSource_System_IO_Stream_"></a> SetSource\(Stream\)

Sets the content to be compressed within the archive.

```csharp
public void SetSource(Stream source)
```

#### Parameters

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The input stream for the archive.

#### Examples


```csharp
using (var archive = new ZstandardArchive())
{
    archive.SetSource(new MemoryStream(new byte[] { 0x00, 0xFF }));
    archive.Save("archive.zst");
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Zstandard_ZstandardArchive_SetSource_System_IO_FileInfo_"></a> SetSource\(FileInfo\)

Sets the content to be compressed within the archive.

```csharp
public void SetSource(FileInfo fileInfo)
```

#### Parameters

`fileInfo` [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

The reference to a file to be compressed.

#### Examples


```csharp
using (var archive = new ZstandardArchive()) 
{
    archive.SetSource(new FileInfo("data.bin"));
    archive.Save("archive.zst");
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Zstandard_ZstandardArchive_SetSource_System_String_"></a> SetSource\(string\)

Sets the content to be compressed within the archive.

```csharp
public void SetSource(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

Path to file to be compressed.

#### Examples


```csharp
using (var archive = new ZstandardArchive()) 
{
    archive.SetSource("data.bin");
    archive.Save("archive.zst");
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

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
