---
linkTitle: "Class Bzip2Archive"
title: "Class Bzip2Archive"
description: "This class represents bzip2 archive file. Use it to compose or extract bzip2 archives."
summary: "This class represents bzip2 archive file. Use it to compose or extract bzip2 archives."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Bzip2](/zip/aspose.zip.bzip2)  
Assembly: Aspose.Zip.dll (25.12.0)  

This class represents bzip2 archive file. Use it to compose or extract bzip2 archives.

```csharp
public class Bzip2Archive : IArchive, IDisposable, IArchiveFileEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[Bzip2Archive](/zip/aspose.zip.bzip2.bzip2archive)

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

bzip2 compresses files using the Burrows-Wheeler block sorting text compression algorithm, and Huffman coding. See more: https://en.wikipedia.org/wiki/Bzip2

## Constructors

### <a id="Aspose_Zip_Bzip2_Bzip2Archive__ctor"></a> Bzip2Archive\(\)

Initializes a new instance of the Aspose.Zip.Bzip2.Bzip2Archive class prepared for compressing.

```csharp
public Bzip2Archive()
```

#### Examples

<p>
        The following example shows how to compress a file.
        </p>

```csharp
using (Bzip2Archive archive = new Bzip2Archive()) 
{
    archive.SetSource("data.bin");
    archive.Save("archive.bz2");
}
```

### <a id="Aspose_Zip_Bzip2_Bzip2Archive__ctor_System_IO_Stream_Aspose_Zip_Bzip2_Bzip2LoadOptions_"></a> Bzip2Archive\(Stream, Bzip2LoadOptions\)

Initializes a new instance of the Aspose.Zip.Bzip2.Bzip2Archive class prepared for decompressing.

```csharp
public Bzip2Archive(Stream sourceStream, Bzip2LoadOptions loadOptions = null)
```

#### Parameters

`sourceStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

`loadOptions` [Bzip2LoadOptions](/zip/aspose.zip.bzip2.bzip2loadoptions)

The options to load archive with.

#### Examples

<p>Open an archive from a stream and extract it to a <code>MemoryStream</code></p>

```csharp
var ms = new MemoryStream();
using (Bzip2Archive archive = new Bzip2Archive(File.OpenRead("archive.bz2")))
  archive.Open().CopyTo(ms);
```

#### Remarks

This constructor does not decompress. See Aspose.Zip.Bzip2.Bzip2Archive.Open method for decompressing.

#### Exceptions

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

Premature stream end.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Wrong signature bytes.

### <a id="Aspose_Zip_Bzip2_Bzip2Archive__ctor_System_String_Aspose_Zip_Bzip2_Bzip2LoadOptions_"></a> Bzip2Archive\(string, Bzip2LoadOptions\)

Initializes a new instance of the Aspose.Zip.Bzip2.Bzip2Archive class prepared for decompressing.

```csharp
public Bzip2Archive(string path, Bzip2LoadOptions loadOptions = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

`loadOptions` [Bzip2LoadOptions](/zip/aspose.zip.bzip2.bzip2loadoptions)

The options to load archive with.

#### Examples

<p>Open an archive from file by path and extract it to a <code>MemoryStream</code></p>

```csharp
var ms = new MemoryStream();
using (Bzip2Archive archive = new Bzip2Archive("archive.bz2"))
  archive.Open().CopyTo(ms);
```

#### Remarks

This constructor does not decompress. See Aspose.Zip.Bzip2.Bzip2Archive.Open method for decompressing.

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

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

Premature stream end.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Wrong signature bytes.

## Methods

### <a id="Aspose_Zip_Bzip2_Bzip2Archive_Dispose"></a> Dispose\(\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_Bzip2_Bzip2Archive_Dispose_System_Boolean_"></a> Dispose\(bool\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
protected virtual void Dispose(bool disposing)
```

#### Parameters

`disposing` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether managed resources should be disposed.

### <a id="Aspose_Zip_Bzip2_Bzip2Archive_Extract_System_IO_Stream_"></a> Extract\(Stream\)

Extracts the archive to the stream provided.

```csharp
public void Extract(Stream destination)
```

#### Parameters

`destination` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream. Must be writable.

#### Examples


```csharp
using (Bzip2Archive archive = new Bzip2Archive("archive.bz2"))
{
     archive.Extract(httpResponseStream);
}
```

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destination</code> does not support writing.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Bzip2_Bzip2Archive_Extract_System_String_"></a> Extract\(string\)

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

### <a id="Aspose_Zip_Bzip2_Bzip2Archive_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

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

If the directory does not exist, the path contains a colon character (:) that is not part of a drive label ("C:\").

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destinationDirectory</code> is a zero-length string, contains only white space, or contains one or more invalid characters. You can query for invalid characters by using the System.IO.Path.GetInvalidPathChars method. 
        -or- path is prefixed with, or contains, only a colon character (:).

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The directory specified by path is a file. -or- The network name is not known.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Bzip2_Bzip2Archive_Open"></a> Open\(\)

Opens the archive for extraction and provides a stream with archive content.

```csharp
public Stream Open()
```

#### Returns

 [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The stream that represents the contents of the archive.

#### Examples

Usage:
`Stream decompressed = archive.Open();`<p>
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

Read from the stream to get the original content of the file. See examples section.

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Bzip2_Bzip2Archive_Save_System_IO_Stream_Aspose_Zip_Bzip2_Bzip2SaveOptions_"></a> Save\(Stream, Bzip2SaveOptions\)

Saves archive to the stream provided.

```csharp
public void Save(Stream outputStream, Bzip2SaveOptions saveOptions = null)
```

#### Parameters

`outputStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`saveOptions` [Bzip2SaveOptions](/zip/aspose.zip.bzip2.bzip2saveoptions)

Options for saving a bzip2 archive. If not specified, 900 Kb block size would be used.

#### Examples

<p>Write compressed data to http response stream.</p>

```csharp
using (var archive = new Bzip2Archive()) 
{
    archive.SetSource(new FileInfo("data.bin"));
    archive.Save(httpResponse.OutputStream);
}
```

#### Remarks

<p>
  <code class="paramref">outputStream</code> must be writable.</p>

#### Exceptions

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The source of data to be archived has not been provided.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">outputStream</code> is not writable.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

File source is read-only or is a directory.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified file source path is invalid, such as being on an unmapped drive.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The File source is already open.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Bzip2_Bzip2Archive_Save_System_String_Aspose_Zip_Bzip2_Bzip2SaveOptions_"></a> Save\(string, Bzip2SaveOptions\)

Saves archive to a destination file provided.

```csharp
public void Save(string destinationFileName, Bzip2SaveOptions saveOptions = null)
```

#### Parameters

`destinationFileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`saveOptions` [Bzip2SaveOptions](/zip/aspose.zip.bzip2.bzip2saveoptions)

Options for saving a bzip2 archive. If not specified, 900 Kb block size would be used.

#### Examples

<p>Writes compressed data to file.</p>

```csharp
using (var archive = new Bzip2Archive()) 
{
    archive.SetSource(new FileInfo("data.bin"));
    archive.Save("data.bz2");
}
```

#### Exceptions

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

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Bzip2_Bzip2Archive_SetSource_System_IO_Stream_"></a> SetSource\(Stream\)

Sets the content to be compressed within the archive.

```csharp
public void SetSource(Stream source)
```

#### Parameters

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The input stream for the archive.

#### Examples


```csharp
using (Bzip2Archive archive = new Bzip2Archive()) 
{
    archive.SetSource(new MemoryStream(new byte[] { 0x00,0xFF }));
    archive.Save("archive.bz2");
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Bzip2_Bzip2Archive_SetSource_System_IO_FileInfo_"></a> SetSource\(FileInfo\)

Sets the content to be compressed within the archive.

```csharp
public void SetSource(FileInfo fileInfo)
```

#### Parameters

`fileInfo` [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

The reference to a file to be compressed.

#### Examples


```csharp
using (Bzip2Archive archive = new Bzip2Archive()) 
{
    archive.SetSource(new FileInfo("data.bin"));
    archive.Save("archive.bz2");
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Bzip2_Bzip2Archive_SetSource_System_String_"></a> SetSource\(string\)

Sets the content to be compressed within the archive.

```csharp
public void SetSource(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

Path to file to be compressed.

#### Examples


```csharp
using (Bzip2Archive archive = new Bzip2Archive()) 
{
    archive.SetSource("data.bin");
    archive.Save("archive.bz2");
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

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Bzip2_Bzip2Archive_SetSource_Aspose_Zip_Tar_TarArchive_Aspose_Zip_Tar_TarFormat_"></a> SetSource\(TarArchive, TarFormat\)

Sets the content to be compressed within the archive.

```csharp
public void SetSource(TarArchive tarArchive, TarFormat format = TarFormat.UsTar)
```

#### Parameters

`tarArchive` [TarArchive](/zip/aspose.zip.tar.tararchive)

Tar archive to be compressed.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)

Defines tar header format.

#### Examples


```csharp
using (var tarArchive = new TarArchive())
{
    tarArchive.CreateEntry("first.bin", "data1.bin");
    tarArchive.CreateEntry("second.bin", "data2.bin");
    using (var bzippedArchive = new Bzip2Archive())
    {
        bzippedArchive.SetSource(tarArchive);
        bzippedArchive.Save("archive.tar.bz2");
    }
}
```

#### Remarks

Use this method to compose joint tar.bz2 archive.

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Bzip2_Bzip2Archive_SetSource_Aspose_Zip_Cpio_CpioArchive_Aspose_Zip_Cpio_CpioFormat_"></a> SetSource\(CpioArchive, CpioFormat\)

Sets the content to be compressed within the archive.

```csharp
public void SetSource(CpioArchive cpioArchive, CpioFormat format = CpioFormat.OldAscii)
```

#### Parameters

`cpioArchive` [CpioArchive](/zip/aspose.zip.cpio.cpioarchive)

Cpio archive to be compressed.

`format` [CpioFormat](/zip/aspose.zip.cpio.cpioformat)

Defines cpio header format.

#### Examples


```csharp
using (var cpioArchive = new CpioArchive())
{
    cpioArchive.CreateEntry("first.bin", "data1.bin");
    cpioArchive.CreateEntry("second.bin", "data2.bin");
    using (var bzippedArchive = new Bzip2Archive())
    {
        bzippedArchive.SetSource(cpioArchive);
        bzippedArchive.Save("archive.cpio.bz2");
    }
}
```

#### Remarks

Use this method to compose joint cpio.bz2 archive.

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.
