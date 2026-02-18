---
linkTitle: "Class RarArchiveEntry"
title: "Class RarArchiveEntry"
description: "Represents single file within archive."
summary: "Represents single file within archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Rar](/zip/aspose.zip.rar)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents single file within archive.

```csharp
public abstract class RarArchiveEntry : IArchiveFileEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[RarArchiveEntry](/zip/aspose.zip.rar.rararchiveentry)

#### Derived

[RarArchiveEntryEncrypted](/zip/aspose.zip.rar.rararchiveentryencrypted), 
[RarArchiveEntryPlain](/zip/aspose.zip.rar.rararchiveentryplain)

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

Cast a Aspose.Zip.Rar.RarArchiveEntry instance to Aspose.Zip.Rar.RarArchiveEntryEncrypted to determine whether the entry encrypted or not.

## Properties

### <a id="Aspose_Zip_Rar_RarArchiveEntry_CompressedSize"></a> CompressedSize

Gets the size of a compressed file.

```csharp
public ulong CompressedSize { get; }
```

#### Property Value

 [ulong](https://learn.microsoft.com/dotnet/api/system.uint64)

### <a id="Aspose_Zip_Rar_RarArchiveEntry_CreationTime"></a> CreationTime

Gets creation date and time.

```csharp
public DateTime CreationTime { get; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_Rar_RarArchiveEntry_IsDirectory"></a> IsDirectory

Gets a value indicating whether the entry represents a directory.

```csharp
public bool IsDirectory { get; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_Rar_RarArchiveEntry_LastAccessTime"></a> LastAccessTime

Gets last access date and time.

```csharp
public DateTime LastAccessTime { get; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_Rar_RarArchiveEntry_ModificationTime"></a> ModificationTime

Gets last modified date and time.

```csharp
public DateTime ModificationTime { get; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_Rar_RarArchiveEntry_Name"></a> Name

Gets name of the entry within the archive.

```csharp
public string Name { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_Rar_RarArchiveEntry_Source"></a> Source

Gets the data source stream for the entry.

```csharp
protected Stream Source { get; set; }
```

#### Property Value

 [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

### <a id="Aspose_Zip_Rar_RarArchiveEntry_UncompressedSize"></a> UncompressedSize

Gets the size of an original file.

```csharp
public ulong UncompressedSize { get; }
```

#### Property Value

 [ulong](https://learn.microsoft.com/dotnet/api/system.uint64)

## Methods

### <a id="Aspose_Zip_Rar_RarArchiveEntry_Extract_System_String_System_String_"></a> Extract\(string, string\)

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

<p>Extract two entries of rar archive.</p>

```csharp
using (FileStream rarFile = File.Open("archive.rar", FileMode.Open))
{
    using (RarArchive archive = new RarArchive(rarFile))
    {
        archive.Entries[0].Extract("first.bin", "pass");
        archive.Entries[1].Extract("second.bin", "pass");
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

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

### <a id="Aspose_Zip_Rar_RarArchiveEntry_Extract_System_IO_Stream_System_String_"></a> Extract\(Stream, string\)

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

<p>Extract an entry of rar archive with password.</p>

```csharp
using (FileStream rarFile = File.Open("archive.zip", FileMode.Open))
{
    using (RarArchive archive = new RarArchive(rarFile))
    {
        archive.Entries[0].Extract(httpResponseStream, "p@s$");
    }
}
```

#### Exceptions

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

CRC or MAC verification failed for the entry.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destination</code> does not support writing.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Data is corrupted. -or- CRC or MAC verification failed for the entry.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

### <a id="Aspose_Zip_Rar_RarArchiveEntry_Open_System_String_"></a> Open\(string\)

Opens the entry for extraction and provides a stream with decompressed entry content.

```csharp
public Stream Open(string password = null)
```

#### Parameters

`password` [string](https://learn.microsoft.com/dotnet/api/system.string)

Optional password for decryption. It can also be set within Aspose.Zip.Rar.RarArchiveLoadOptions.DecryptionPassword.

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

### <a id="Aspose_Zip_Rar_RarArchiveEntry_ExtractionProgressed"></a> ExtractionProgressed

Raises when a portion of raw stream extracted.

```csharp
public event EventHandler<ProgressEventArgs> ExtractionProgressed
```

#### Event Type

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[ProgressEventArgs](/zip/aspose.zip.progresseventargs)\>

#### Examples

`archive.Entries[0].ExtractionProgressed += (s, e) =&gt; {  int percent = (int)((100 * e.ProceededBytes) / ((RarArchiveEntry)s).UncompressedSize); };`

#### Remarks

Event sender is an Aspose.Zip.Rar.RarArchiveEntry instance.
