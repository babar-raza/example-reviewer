---
linkTitle: "Class ArchiveEntry"
title: "Class ArchiveEntry"
description: "Represents single file within archive."
summary: "Represents single file within archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip](/zip/)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents single file within archive.

```csharp
public abstract class ArchiveEntry : IArchiveFileEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ArchiveEntry](/zip/aspose.zip.archiveentry)

#### Derived

[ArchiveEntryEncrypted](/zip/aspose.zip.archiveentryencrypted), 
[ArchiveEntryPlain](/zip/aspose.zip.archiveentryplain)

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

Cast an Aspose.Zip.ArchiveEntry instance to Aspose.Zip.ArchiveEntryEncrypted to determine whether the entry encrypted or not.

## Constructors

### <a id="Aspose_Zip_ArchiveEntry__ctor_System_String_Aspose_Zip_Saving_CompressionSettings_System_Func_System_IO_Stream__System_UInt32_"></a> ArchiveEntry\(string, CompressionSettings, Func<Stream\>, uint\)

Initializes a new instance of the Aspose.Zip.ArchiveEntry class.

```csharp
protected ArchiveEntry(string name, CompressionSettings compressionSettings, Func<Stream> sourceProvider, uint fileAttributes)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

Entry name.

`compressionSettings` [CompressionSettings](/zip/aspose.zip.saving.compressionsettings)

Settings for compression or decompression.

`sourceProvider` [Func](https://learn.microsoft.com/dotnet/api/system.func\-1)<[Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)\>

Method returning stream with entry data either to be compressed.

`fileAttributes` [uint](https://learn.microsoft.com/dotnet/api/system.uint32)

Attributes from the file system.

### <a id="Aspose_Zip_ArchiveEntry__ctor_System_String_Aspose_Zip_Saving_CompressionSettings_System_IO_Stream_System_UInt32_System_IO_FileSystemInfo_"></a> ArchiveEntry\(string, CompressionSettings, Stream, uint, FileSystemInfo\)

Initializes a new instance of the Aspose.Zip.ArchiveEntry class.

```csharp
protected ArchiveEntry(string name, CompressionSettings compressionSettings, Stream source, uint fileAttributes, FileSystemInfo fileInfo = null)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

Entry name.

`compressionSettings` [CompressionSettings](/zip/aspose.zip.saving.compressionsettings)

Settings for compression or decompression.

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Stream with entry data either to be compressed or to be decompressed.

`fileAttributes` [uint](https://learn.microsoft.com/dotnet/api/system.uint32)

Attributes from the file system.

`fileInfo` [FileSystemInfo](https://learn.microsoft.com/dotnet/api/system.io.filesysteminfo)

File or directory info the entry based on.

## Properties

### <a id="Aspose_Zip_ArchiveEntry_Comment"></a> Comment

Gets comment of the entry within archive.

```csharp
public string Comment { get; protected set; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_ArchiveEntry_CompressedSize"></a> CompressedSize

Gets size of the compressed file.

```csharp
public ulong CompressedSize { get; }
```

#### Property Value

 [ulong](https://learn.microsoft.com/dotnet/api/system.uint64)

### <a id="Aspose_Zip_ArchiveEntry_CompressionSettings"></a> CompressionSettings

Gets settings for compression or decompression.

```csharp
public CompressionSettings CompressionSettings { get; }
```

#### Property Value

 [CompressionSettings](/zip/aspose.zip.saving.compressionsettings)

### <a id="Aspose_Zip_ArchiveEntry_DataSource"></a> DataSource

Source for the entry if the entry was added to the archive, not extracted.

```csharp
public Stream DataSource { get; }
```

#### Property Value

 [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

#### Remarks

Before assigned, the source is null. This source may be assigned within <code>Archive.Save</code> method in some cases.

### <a id="Aspose_Zip_ArchiveEntry_FileAttributes"></a> FileAttributes

Gets file attributes from the host system.

```csharp
protected FileAttributes FileAttributes { get; }
```

#### Property Value

 [FileAttributes](https://learn.microsoft.com/dotnet/api/system.io.fileattributes)

### <a id="Aspose_Zip_ArchiveEntry_IsDirectory"></a> IsDirectory

Gets a value indicating whether the entry represents a directory.

```csharp
public bool IsDirectory { get; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_ArchiveEntry_ModificationTime"></a> ModificationTime

Gets or sets last modified date and time.

```csharp
public DateTime ModificationTime { get; set; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_ArchiveEntry_Name"></a> Name

Gets name of the entry within the archive.

```csharp
public string Name { get; protected set; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_ArchiveEntry_UncompressedSize"></a> UncompressedSize

Gets size of the original file.

```csharp
public ulong UncompressedSize { get; }
```

#### Property Value

 [ulong](https://learn.microsoft.com/dotnet/api/system.uint64)

## Methods

### <a id="Aspose_Zip_ArchiveEntry_Extract_System_String_System_String_"></a> Extract\(string, string\)

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

The file info of the composed file.

#### Examples

<p>Extract two entries of ZIP archive, each with own password</p>

```csharp
using (FileStream zipFile = File.Open("archive.zip", FileMode.Open))
{
    using (Archive archive = new Archive(zipFile))
    {
        archive.Entries[0].Extract("first.bin", "first_pass");
        archive.Entries[1].Extract("second.bin", "second_pass");
    }
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

Data is corrupted. -or- CRC or MAC verification failed for the entry.

### <a id="Aspose_Zip_ArchiveEntry_Extract_System_IO_Stream_System_String_"></a> Extract\(Stream, string\)

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
using (FileStream zipFile = File.Open("archive.zip", FileMode.Open))
{
    using (Archive archive = new Archive(zipFile))
    {
        archive.Entries[0].Extract(httpResponseStream, "p@s$");
    }
}
```

#### Exceptions

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Data is corrupted. -or- CRC or MAC verification failed for the entry.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The source is corrupted or not readable.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destination</code> does not support writing.

### <a id="Aspose_Zip_ArchiveEntry_Open_System_String_"></a> Open\(string\)

Opens the entry for extraction and provides a stream with decompressed entry content.

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

<p>Read from the stream to get the original content of a file. See examples section.</p>

#### Exceptions

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is in an incorrect state.

### <a id="Aspose_Zip_ArchiveEntry_CompressionProgressed"></a> CompressionProgressed

Raises when a portion of raw stream compressed.

```csharp
public event EventHandler<ProgressEventArgs> CompressionProgressed
```

#### Event Type

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[ProgressEventArgs](/zip/aspose.zip.progresseventargs)\>

#### Examples

`archive.Entries[0].CompressionProgressed += (s, e) =&gt; { int percent = (int)((100 * (long)e.ProceededBytes) / entrySourceStream.Length); };`

#### Remarks

Event sender is an Aspose.Zip.ArchiveEntry instance.

### <a id="Aspose_Zip_ArchiveEntry_ExtractionProgressed"></a> ExtractionProgressed

Raises when a portion of raw stream extracted.

```csharp
public event EventHandler<ProgressCancelEventArgs> ExtractionProgressed
```

#### Event Type

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[ProgressCancelEventArgs](/zip/aspose.zip.progresscanceleventargs)\>

#### Examples

In this sample event handler is used for calculation the share of proceeded size in percents.  
`a.Entries[0].ExtractionProgressed += (s, e) =&gt; {  int percent = (int)((100 * e.ProceededBytes) / ((ArchiveEntry)s).UncompressedSize); };`

In this sample event handler is used for cancellation after the first hundred of Mb of entry was extracted.
`a.Entries[0].ExtractionProgressed += (s, e) =&gt; { if (e.ProceededBytes &gt; 100000000) e.Cancel = true; };`

#### Remarks

Event sender is an Aspose.Zip.ArchiveEntry instance.
            It is possible to cancel extraction.
