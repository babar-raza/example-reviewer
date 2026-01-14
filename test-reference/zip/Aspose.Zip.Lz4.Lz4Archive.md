---
linkTitle: "Class Lz4Archive"
title: "Class Lz4Archive"
description: "This class represents LZ4 archive file. Use it to extract or compose LZ4 archives."
summary: "This class represents LZ4 archive file. Use it to extract or compose LZ4 archives."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Lz4](/zip/aspose.zip.lz4)  
Assembly: Aspose.Zip.dll (25.12.0)  

This class represents LZ4 archive file. Use it to extract or compose LZ4 archives.

```csharp
public class Lz4Archive : IArchive, IDisposable, IArchiveFileEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[Lz4Archive](/zip/aspose.zip.lz4.lz4archive)

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

### <a id="Aspose_Zip_Lz4_Lz4Archive__ctor_System_IO_Stream_Aspose_Zip_Lz4_Lz4LoadOptions_"></a> Lz4Archive\(Stream, Lz4LoadOptions\)

Initializes a new instance of the Aspose.Zip.Lz4.Lz4Archive class prepared for decompressing.

```csharp
public Lz4Archive(Stream sourceStream, Lz4LoadOptions loadOptions = null)
```

#### Parameters

`sourceStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

`loadOptions` [Lz4LoadOptions](/zip/aspose.zip.lz4.lz4loadoptions)

The options to load archive with.

#### Examples

<p>Open an archive from a stream and extract it to a <code>MemoryStream</code></p>

```csharp
var ms = new MemoryStream();
using (Lz4Archive archive = new Lz4Archive(File.OpenRead("archive.lz4")))
  archive.Open().CopyTo(ms);
```

#### Remarks

This constructor does not decompress. See Aspose.Zip.Lz4.Lz4Archive.Open method for decompressing.

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

Cannot read from <code class="paramref">sourceStream</code>

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">sourceStream</code> is null.

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

<code class="paramref">sourceStream</code> is too short.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The <code class="paramref">sourceStream</code> has wrong signature.

### <a id="Aspose_Zip_Lz4_Lz4Archive__ctor_System_String_Aspose_Zip_Lz4_Lz4LoadOptions_"></a> Lz4Archive\(string, Lz4LoadOptions\)

Initializes a new instance of the Aspose.Zip.Lz4.Lz4Archive class.

```csharp
public Lz4Archive(string path, Lz4LoadOptions loadOptions = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

`loadOptions` [Lz4LoadOptions](/zip/aspose.zip.lz4.lz4loadoptions)

The options to load archive with.

#### Examples

<p>Open an archive from file by path and extract it to a <code>MemoryStream</code></p>

```csharp
var ms = new MemoryStream();
using (Lz4Archive archive = new Lz4Archive("archive.lz4"))
  archive.Open().CopyTo(ms);
```

#### Remarks

This constructor does not decompress. See Aspose.Zip.Lz4.Lz4Archive.Open method for decompressing.

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

### <a id="Aspose_Zip_Lz4_Lz4Archive__ctor_Aspose_Zip_Lz4_Lz4ArchiveSetting_"></a> Lz4Archive\(Lz4ArchiveSetting\)

Initializes a new instance of the Aspose.Zip.Lz4.Lz4Archive class prepared for compressing.

```csharp
public Lz4Archive(Lz4ArchiveSetting settings = null)
```

#### Parameters

`settings` [Lz4ArchiveSetting](/zip/aspose.zip.lz4.lz4archivesetting)

The setting of the composed archive.

## Methods

### <a id="Aspose_Zip_Lz4_Lz4Archive_Dispose"></a> Dispose\(\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_Lz4_Lz4Archive_Dispose_System_Boolean_"></a> Dispose\(bool\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
protected virtual void Dispose(bool disposing)
```

#### Parameters

`disposing` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether managed resources should be disposed.

### <a id="Aspose_Zip_Lz4_Lz4Archive_Extract_System_String_"></a> Extract\(string\)

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

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

Source stream is too short.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Wrong bytes found while decoding.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

This LZ4 version is not supported.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Lz4_Lz4Archive_Extract_System_IO_Stream_"></a> Extract\(Stream\)

Extracts the archive to the stream provided.

```csharp
public void Extract(Stream destination)
```

#### Parameters

`destination` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream. Must be writable.

#### Examples


```csharp
using (var archive = new Lz4Archive("archive.lz4"))
{
     archive.Extract(httpResponseStream);
}
```

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destination</code> does not support writing.

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

Source stream is too short.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Wrong bytes found while decoding.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

This LZ4 version is not supported.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is prepared for composition.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Lz4_Lz4Archive_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

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

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

Source stream is too short.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Wrong bytes found while initialize decoding.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is prepared for composition.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Lz4_Lz4Archive_Open"></a> Open\(\)

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
using (var archive = new Lz4Archive("archive.lz4"))
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

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

Source stream is too short.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Wrong bytes found while initialize decoding.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is prepared for composition.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Lz4_Lz4Archive_Save_System_IO_Stream_"></a> Save\(Stream\)

Saves lz4 archive to the stream provided.

```csharp
public void Save(Stream output)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

#### Examples


```csharp
using (FileStream lz4File = File.Open("archive.lz4", FileMode.Create))
{
    using (var archive = new Lz4Archive())
    {
        archive.SetSource("data.bin");
        archive.Save(lz4File);
     }
}
```

#### Remarks

<p>
  <code class="paramref">output</code> must be seekable.</p>

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">output</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">output</code> is not writable.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is prepared for extraction. - or - Source was not supplied.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the compression is canceled via the provided cancellation token.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Lz4_Lz4Archive_Save_System_IO_FileInfo_"></a> Save\(FileInfo\)

Saves lz4 archive to destination file provided.

```csharp
public void Save(FileInfo destination)
```

#### Parameters

`destination` [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

FileInfo, which will be opened as destination stream.

#### Examples


```csharp
using (var archive = new Lz4Archive()) 
{
    archive.SetSource(new FileInfo("data.bin"));
    archive.Save(new FileInfo("archive.lz4"));
}
```

#### Exceptions

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

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is prepared for extraction.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Lz4_Lz4Archive_Save_System_String_"></a> Save\(string\)

Saves archive to the destination file provided.

```csharp
public void Save(string destinationFileName)
```

#### Parameters

`destinationFileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

#### Examples


```csharp
using (var archive = new LZ4Archive())
{
    archive.SetSource("data.bin");
    archive.Save("archive.lz4");
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

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is prepared for extraction.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Lz4_Lz4Archive_SetSource_System_IO_Stream_"></a> SetSource\(Stream\)

Sets the content to be compressed within the archive.

```csharp
public void SetSource(Stream source)
```

#### Parameters

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The input stream for the archive.

#### Examples


```csharp
using (var archive = new Lz4Archive())
{
    archive.SetSource(new MemoryStream(new byte[] { 0x00, 0xFF }));
    archive.Save("archive.lz4");
}
```

#### Exceptions

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is prepared for extraction.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Lz4_Lz4Archive_SetSource_System_IO_FileInfo_"></a> SetSource\(FileInfo\)

Sets the content to be compressed within the archive.

```csharp
public void SetSource(FileInfo fileInfo)
```

#### Parameters

`fileInfo` [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

The reference to a file to be compressed.

#### Examples

<p>Open an archive from a stream and extract it to a <code>MemoryStream</code></p>

```csharp
using (var archive = new Lz4Archive()) 
{
    archive.SetSource(new FileInfo("data.bin"));
    archive.Save("archive.lz4");
}
```

#### Exceptions

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is prepared for extraction.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Lz4_Lz4Archive_SetSource_Aspose_Zip_Tar_TarArchive_Aspose_Zip_Tar_TarFormat_"></a> SetSource\(TarArchive, TarFormat\)

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
    using (var lz4Archive = new Lz4Archive())
    {
        lz4Archive.SetSource(tarArchive);
        lz4Archive.Save("archive.tar.lz4");
    }
}
```

#### Remarks

Use this method to compose joint tar.lz4 archive.

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Lz4_Lz4Archive_SetSource_System_String_"></a> SetSource\(string\)

Sets the content to be compressed within the archive.

```csharp
public void SetSource(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

Path to file to be compressed.

#### Examples

<p>Open an archive from file by path and extract it to a <code>MemoryStream</code></p>

```csharp
using (var archive = new Lz4Archive()) 
{
    archive.SetSource("data.bin");
    archive.Save("archive.lz4");
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

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

This archive is prepared for extraction.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.
