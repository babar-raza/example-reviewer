---
linkTitle: "Class TarArchive"
title: "Class TarArchive"
description: "This class represents a tar archive file. Use it to compose, extract, or update tar archives."
summary: "This class represents a tar archive file. Use it to compose, extract, or update tar archives."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Tar](/zip/aspose.zip.tar)  
Assembly: Aspose.Zip.dll (25.12.0)  

This class represents a tar archive file. Use it to compose, extract, or update tar archives.

```csharp
public class TarArchive : IArchive, IDisposable
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[TarArchive](/zip/aspose.zip.tar.tararchive)

#### Implements

[IArchive](/zip/aspose.zip.iarchive), 
[IDisposable](https://learn.microsoft.com/dotnet/api/system.idisposable)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Tar_TarArchive__ctor"></a> TarArchive\(\)

Initializes a new instance of the Aspose.Zip.Tar.TarArchive class.

```csharp
public TarArchive()
```

#### Examples

<p>The following example shows how to compress a file.</p>

```csharp
using (var archive = new TarArchive())
{
    archive.CreateEntry("first.bin", "data.bin");
    archive.Save("archive.tar");
}
```

### <a id="Aspose_Zip_Tar_TarArchive__ctor_System_IO_Stream_"></a> TarArchive\(Stream\)

Initializes a new instance of the Aspose.Zip.Archive class and composes an entry list can be extracted from the archive.

```csharp
public TarArchive(Stream sourceStream)
```

#### Parameters

`sourceStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive. It must be seekable.

#### Examples

<p>The following example shows how to extract all the entries to a directory.</p>

```csharp
using (var archive = new TarArchive(File.OpenRead("archive.tar")))
{ 
   archive.ExtractToDirectory("C:\extracted");
}
```

#### Remarks

This constructor does not unpack any entry. See Aspose.Zip.Tar.TarEntry.Open method for unpacking.

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">sourceStream</code> is not seekable.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">sourceStream</code> is null.

### <a id="Aspose_Zip_Tar_TarArchive__ctor_System_String_"></a> TarArchive\(string\)

Initializes a new instance of the Aspose.Zip.Tar.TarArchive class and composes an entry list can be extracted from the archive.

```csharp
public TarArchive(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

#### Examples

<p>The following example shows how to extract all the entries to a directory.</p>

```csharp
using (var archive = new TarArchive("archive.tar")) 
{ 
   archive.ExtractToDirectory("C:\extracted");
}
```

#### Remarks

This constructor does not unpack any entry. See Aspose.Zip.Tar.TarEntry.Open method for unpacking.

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

## Properties

### <a id="Aspose_Zip_Tar_TarArchive_Entries"></a> Entries

Gets entries of Aspose.Zip.Tar.TarEntry type constituting the archive.

```csharp
public ReadOnlyCollection<TarEntry> Entries { get; }
```

#### Property Value

 [ReadOnlyCollection](https://learn.microsoft.com/dotnet/api/system.collections.objectmodel.readonlycollection\-1)<[TarEntry](/zip/aspose.zip.tar.tarentry)\>

## Methods

### <a id="Aspose_Zip_Tar_TarArchive_CreateEntries_System_IO_DirectoryInfo_System_Boolean_"></a> CreateEntries\(DirectoryInfo, bool\)

Adds to the archive all the files and directories recursively in the directory given.

```csharp
public TarArchive CreateEntries(DirectoryInfo directory, bool includeRootDirectory = true)
```

#### Parameters

`directory` [DirectoryInfo](https://learn.microsoft.com/dotnet/api/system.io.directoryinfo)

Directory to compress.

`includeRootDirectory` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Indicates whether to include the root directory itself or not.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

The archive with entries composed.

#### Examples


```csharp
using (FileStream tarFile = File.Open("archive.tar", FileMode.Create))
{
    using (var archive = new TarArchive())
    {
        archive.CreateEntries(new DirectoryInfo("C:\folder"), false);
        archive.Save(tarFile);
    }
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_CreateEntries_System_String_System_Boolean_"></a> CreateEntries\(string, bool\)

Adds to the archive all the files and directories recursively in the directory given.

```csharp
public TarArchive CreateEntries(string sourceDirectory, bool includeRootDirectory = true)
```

#### Parameters

`sourceDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

Directory to compress.

`includeRootDirectory` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Indicates whether to include the root directory itself or not.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

The archive with entries composed.

#### Examples


```csharp
using (FileStream tarFile = File.Open("archive.tar", FileMode.Create))
{
    using (var archive = new TarArchive())
    {
        archive.CreateEntries("C:\folder", false);
        archive.Save(tarFile);
    }
}
```

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">sourceDirectory</code> is null.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access <code class="paramref">sourceDirectory</code>.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">sourceDirectory</code> contains invalid characters such as ", &lt;, &gt;, or |.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified path, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters. The specified path, file name, or both are too long.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_CreateEntry_System_String_System_IO_Stream_System_IO_FileSystemInfo_"></a> CreateEntry\(string, Stream, FileSystemInfo\)

Create a single entry within the archive.

```csharp
public TarEntry CreateEntry(string name, Stream source, FileSystemInfo fileInfo = null)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The input stream for the entry.

`fileInfo` [FileSystemInfo](https://learn.microsoft.com/dotnet/api/system.io.filesysteminfo)

The metadata of file or folder to be compressed.

#### Returns

 [TarEntry](/zip/aspose.zip.tar.tarentry)

Tar entry instance.

#### Examples


```csharp
using (var archive = new TarArchive())
{
   archive.CreateEntry("bytes", new MemoryStream(new byte[] {0x00, 0xFF}));
   archive.Save(tarFile);
}
```

#### Remarks

<p>The entry name is solely set within <code class="paramref">name</code> parameter. The file name provided in <code class="paramref">fileInfo</code> parameter does not affect the entry name.</p>
<p>
  <code class="paramref">fileInfo</code> can refer to System.IO.DirectoryInfo if the entry is directory.</p>

#### Exceptions

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

<code class="paramref">name</code> is too long for tar as of IEEE 1003.1-1998 standard.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

File name, as a part of <code class="paramref">name</code>, exceeds 100 symbols.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_CreateEntry_System_String_System_IO_FileInfo_System_Boolean_"></a> CreateEntry\(string, FileInfo, bool\)

Create a single entry within the archive.

```csharp
public TarEntry CreateEntry(string name, FileInfo fileInfo, bool openImmediately = false)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`fileInfo` [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

The metadata of file or folder to be compressed.

`openImmediately` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

True, if open the file immediately, otherwise open the file on archive saving.

#### Returns

 [TarEntry](/zip/aspose.zip.tar.tarentry)

Tar entry instance.

#### Examples


```csharp
FileInfo fi = new FileInfo("data.bin");
using (var archive = new TarArchive())
{
   archive.CreateEntry("data.bin", fi);
   archive.Save(tarFile);
}
```

#### Remarks

<p>The entry name is solely set within <code class="paramref">name</code> parameter. The file name provided in <code class="paramref">fileInfo</code> parameter does not affect the entry name.</p>
<p>
  <code class="paramref">fileInfo</code> can refer to System.IO.DirectoryInfo if the entry is directory.</p>
<p>If the file is opened immediately with <code class="paramref">openImmediately</code> parameter it becomes blocked until archive is disposed.</p>

#### Exceptions

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

<code class="paramref">name</code> is too long for tar as of IEEE 1003.1-1998 standard.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

File name, as a part of <code class="paramref">name</code>, exceeds 100 symbols.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_CreateEntry_System_String_System_String_System_Boolean_"></a> CreateEntry\(string, string, bool\)

Create a single entry within the archive.

```csharp
public TarEntry CreateEntry(string name, string path, bool openImmediately = false)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

Path to file to be compressed.

`openImmediately` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

True, if open the file immediately, otherwise open the file on archive saving.

#### Returns

 [TarEntry](/zip/aspose.zip.tar.tarentry)

Tar entry instance.

#### Examples


```csharp
using (var archive = new TarArchive())
{
    archive.CreateEntry("first.bin", "data.bin");
    archive.Save(outputTarFile);
}
```

#### Remarks

<p>The entry name is solely set within <code class="paramref">name</code> parameter. The file name provided in <code class="paramref">path</code> parameter does not affect the entry name.</p>
<p>If the file is opened immediately with <code class="paramref">openImmediately</code> parameter it becomes blocked until archive is disposed.</p>

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">path</code> is empty, contains only white spaces, or contains invalid characters. - or - File name, as a part of <code class="paramref">name</code>, exceeds 100 symbols.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">path</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters. - or - <code class="paramref">name</code> is too long for tar as of IEEE 1003.1-1998 standard.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">path</code> contains a colon (:) in the middle of the string.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_DeleteEntry_Aspose_Zip_Tar_TarEntry_"></a> DeleteEntry\(TarEntry\)

Removes the first occurrence of a specific entry from the entry list.

```csharp
public TarArchive DeleteEntry(TarEntry entry)
```

#### Parameters

`entry` [TarEntry](/zip/aspose.zip.tar.tarentry)

The entry to remove from the entries list.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

The archive with the entry deleted.

#### Examples

<p>Here is how you can remove all entries except the last one:</p>

```csharp
using (var archive = new TarArchive("archive.tar"))
{
    while (archive.Entries.Count &gt; 1)
        archive.DeleteEntry(archive.Entries[0]);
    archive.Save(outputTarFile);
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_DeleteEntry_System_Int32_"></a> DeleteEntry\(int\)

Removes the entry from the entry list by index.

```csharp
public TarArchive DeleteEntry(int entryIndex)
```

#### Parameters

`entryIndex` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The zero-based index of the entry to remove.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

The archive with the entry deleted.

#### Examples


```csharp
using (var archive = new TarArchive("two_files.tar"))
{
    archive.DeleteEntry(0);
    archive.Save("single_file.tar");
}
```

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

<code class="paramref">entryIndex</code> is less than 0.-or- <code class="paramref">entryIndex</code> is equal to or greater than <code>Entries</code> count.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_Dispose"></a> Dispose\(\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_Tar_TarArchive_Dispose_System_Boolean_"></a> Dispose\(bool\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
protected virtual void Dispose(bool disposing)
```

#### Parameters

`disposing` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether managed resources should be disposed.

### <a id="Aspose_Zip_Tar_TarArchive_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

Extracts all the files in the archive to the directory provided.

```csharp
public void ExtractToDirectory(string destinationDirectory)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory to place the extracted files in.

#### Examples


```csharp
Using (var archive = new TarArchive("archive.tar")) 
{ 
   archive.ExtractToDirectory("C:\extracted");
}
```

#### Remarks

If the directory does not exist, it will be created.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

Path is null

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified path, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters and file names must be less than 260 characters.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access the existing directory.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

If the directory does not exist, the path contains a colon character (:) that is not part of a drive label ("C:\").

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

Path is a zero-length string, contains only white space, or contains one or more invalid characters. You can query for invalid characters by using the System.IO.Path.GetInvalidPathChars method. - or - path is prefixed with, or contains, only a colon character (:).

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The directory specified by path is a file. - or - The network name is not known.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_FromGZip_System_IO_Stream_"></a> FromGZip\(Stream\)

Extracts supplied gzip archive and composes Aspose.Zip.Tar.TarArchive from extracted data.
<p>
Important: gzip archive is fully extracted within this method, its content is kept internally. Beware of memory consumption.
</p>

```csharp
public static TarArchive FromGZip(Stream source)
```

#### Parameters

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

An instance of Aspose.Zip.Tar.TarArchive

#### Remarks

GZip extraction stream is not seekable by the nature of compression algorithm.
            Tar archive provides facility to extract arbitrary record, so it has to operate seekable stream under the hood.

#### Exceptions

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The archive is corrupted.

### <a id="Aspose_Zip_Tar_TarArchive_FromGZip_System_String_"></a> FromGZip\(string\)

Extracts supplied gzip archive and composes Aspose.Zip.Tar.TarArchive from extracted data.
<p>
Important: gzip archive is fully extracted within this method, its content is kept internally. Beware of memory consumption.
</p>

```csharp
public static TarArchive FromGZip(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

An instance of Aspose.Zip.Tar.TarArchive

#### Remarks

GZip extraction stream is not seekable by the nature of compression algorithm.
            Tar archive provides facility to extract arbitrary record, so it has to operate seekable stream under the hood.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">path</code> is empty, contains only white spaces, or contains invalid characters.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">path</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">path</code>  is in an invalid format.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified path is invalid, such as being on an unmapped drive.

 [FileNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.filenotfoundexception)

The file is not found.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The archive is corrupted.

### <a id="Aspose_Zip_Tar_TarArchive_FromLZ4_System_String_"></a> FromLZ4\(string\)

Extracts supplied LZ4 archive and composes Aspose.Zip.Tar.TarArchive from extracted data.
<p>
Important: LZ4 archive is fully extracted within this method, its content is kept internally. Beware of memory consumption.
</p>

```csharp
public static TarArchive FromLZ4(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

An instance of Aspose.Zip.Tar.TarArchive

#### Remarks

LZ4 extraction stream is not seekable by the nature of compression algorithm. Tar archive provides facility to extract arbitrary record, so it has to operate seekable stream under the hood.

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

File at <code class="paramref">path</code>  is in an invalid format.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified path is invalid, such as being on an unmapped drive.

 [FileNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.filenotfoundexception)

The file is not found.

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

The file is too short.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The file has the wrong signature.

### <a id="Aspose_Zip_Tar_TarArchive_FromLZ4_System_IO_Stream_"></a> FromLZ4\(Stream\)

Extracts supplied LZ4 archive and composes Aspose.Zip.Tar.TarArchive from extracted data.
<p>
Important: LZ4 archive is fully extracted within this method, its content is kept internally. Beware of memory consumption.
</p>

```csharp
public static TarArchive FromLZ4(Stream source)
```

#### Parameters

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

An instance of Aspose.Zip.Tar.TarArchive

#### Remarks

LZ4 extraction stream is not seekable by the nature of compression algorithm. Tar archive provides facility to extract arbitrary record, so it has to operate seekable stream under the hood.

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

Cannot read from <code class="paramref">source</code>

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">source</code> is null.

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

<code class="paramref">source</code> is too short.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The <code class="paramref">source</code> has the wrong signature.

### <a id="Aspose_Zip_Tar_TarArchive_FromLZMA_System_IO_Stream_"></a> FromLZMA\(Stream\)

Extracts supplied LZMA archive and composes Aspose.Zip.Tar.TarArchive from extracted data.
<p>
Important: LZMA archive is fully extracted within this method, its content is kept internally. Beware of memory consumption.
</p>

```csharp
public static TarArchive FromLZMA(Stream source)
```

#### Parameters

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

An instance of Aspose.Zip.Tar.TarArchive

#### Remarks

LZMA extraction stream is not seekable by the nature of compression algorithm.  Tar archive provides facility to extract arbitrary record, so it has to operate seekable stream under the hood.

#### Exceptions

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The archive is corrupted.

### <a id="Aspose_Zip_Tar_TarArchive_FromLZMA_System_String_"></a> FromLZMA\(string\)

Extracts supplied LZMA archive and composes Aspose.Zip.Tar.TarArchive from extracted data.
<p>
Important: LZMA archive is fully extracted within this method, its content is kept internally. Beware of memory consumption.
</p>

```csharp
public static TarArchive FromLZMA(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

An instance of Aspose.Zip.Tar.TarArchive

#### Remarks

LZMA extraction stream is not seekable by the nature of compression algorithm. Tar archive provides facility to extract arbitrary record, so it has to operate seekable stream under the hood.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">path</code> is empty, contains only white spaces, or contains invalid characters.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">path</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">path</code>  is in an invalid format.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified path is invalid, such as being on an unmapped drive.

 [FileNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.filenotfoundexception)

The file is not found.

### <a id="Aspose_Zip_Tar_TarArchive_FromLZip_System_IO_Stream_"></a> FromLZip\(Stream\)

Extracts supplied lzip archive and composes Aspose.Zip.Tar.TarArchive from extracted data.
<p>
Important: lzip archive is fully extracted within this method, its content is kept internally. Beware of memory consumption.
</p>

```csharp
public static TarArchive FromLZip(Stream source)
```

#### Parameters

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

An instance of Aspose.Zip.Tar.TarArchive

#### Remarks

Lzip extraction stream is not seekable by the nature of compression algorithm.  Tar archive provides facility to extract arbitrary record, so it has to operate seekable stream under the hood.

#### Exceptions

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The archive is corrupted.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">source</code> is not seekable.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">source</code> is null.

### <a id="Aspose_Zip_Tar_TarArchive_FromLZip_System_String_"></a> FromLZip\(string\)

Extracts supplied lzip archive and composes Aspose.Zip.Tar.TarArchive from extracted data.
<p>
Important: lzip archive is fully extracted within this method, its content is kept internally. Beware of memory consumption.
</p>

```csharp
public static TarArchive FromLZip(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

An instance of Aspose.Zip.Tar.TarArchive

#### Remarks

Lzip extraction stream is not seekable by the nature of compression algorithm.  Tar archive provides facility to extract arbitrary record, so it has to operate seekable stream under the hood.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">path</code> is empty, contains only white spaces, or contains invalid characters.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">path</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">path</code>  is in an invalid format.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified path is invalid, such as being on an unmapped drive.

 [FileNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.filenotfoundexception)

The file is not found.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The archive is corrupted.

### <a id="Aspose_Zip_Tar_TarArchive_FromXz_System_IO_Stream_"></a> FromXz\(Stream\)

Extracts supplied xz format archive and composes Aspose.Zip.Tar.TarArchive from extracted data.
<p>
Important: xz archive is fully extracted within this method, its content is kept internally. Beware of memory consumption.
</p>

```csharp
public static TarArchive FromXz(Stream source)
```

#### Parameters

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

An instance of Aspose.Zip.Tar.TarArchive

#### Remarks

Tar archive provides facility to extract arbitrary record, so it has to operate seekable stream under the hood.

### <a id="Aspose_Zip_Tar_TarArchive_FromXz_System_String_"></a> FromXz\(string\)

Extracts supplied xz format archive and composes Aspose.Zip.Tar.TarArchive from extracted data.
<p>
Important: xz archive is fully extracted within this method, its content is kept internally. Beware of memory consumption.
</p>

```csharp
public static TarArchive FromXz(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

An instance of Aspose.Zip.Tar.TarArchive

#### Remarks

Tar archive provides facility to extract arbitrary record, so it has to operate seekable stream under the hood.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">path</code> is empty, contains only white spaces, or contains invalid characters.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">path</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">path</code>  is in an invalid format.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified path is invalid, such as being on an unmapped drive.

 [FileNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.filenotfoundexception)

The file is not found.

### <a id="Aspose_Zip_Tar_TarArchive_FromZ_System_IO_Stream_"></a> FromZ\(Stream\)

Extracts supplied Z format archive and composes Aspose.Zip.Tar.TarArchive from extracted data.
<p>
Important: Z archive is fully extracted within this method, its content is kept internally. Beware of memory consumption.
</p>

```csharp
public static TarArchive FromZ(Stream source)
```

#### Parameters

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

An instance of Aspose.Zip.Tar.TarArchive

#### Remarks

Tar archive provides facility to extract arbitrary record, so it has to operate seekable stream under the hood.

### <a id="Aspose_Zip_Tar_TarArchive_FromZ_System_String_"></a> FromZ\(string\)

Extracts supplied Z format archive and composes Aspose.Zip.Tar.TarArchive from extracted data.
<p>
Important: Z archive is fully extracted within this method, its content is kept internally. Beware of memory consumption.
</p>

```csharp
public static TarArchive FromZ(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

An instance of Aspose.Zip.Tar.TarArchive

#### Remarks

Tar archive provides facility to extract arbitrary record, so it has to operate seekable stream under the hood.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">path</code> is empty, contains only white spaces, or contains invalid characters.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">path</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">path</code>  is in an invalid format.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified path is invalid, such as being on an unmapped drive.

 [FileNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.filenotfoundexception)

The file is not found.

### <a id="Aspose_Zip_Tar_TarArchive_FromZstandard_System_IO_Stream_"></a> FromZstandard\(Stream\)

Extracts supplied Zstandard archive and composes Aspose.Zip.Tar.TarArchive from extracted data.
<p>
Important: Zstandard archive is fully extracted within this method, its content is kept internally. Beware of memory consumption.
</p>

```csharp
public static TarArchive FromZstandard(Stream source)
```

#### Parameters

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

An instance of Aspose.Zip.Tar.TarArchive

#### Exceptions

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

Zstandard stream is corrupted or not readable.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Data is corrupted.

### <a id="Aspose_Zip_Tar_TarArchive_FromZstandard_System_String_"></a> FromZstandard\(string\)

Extracts supplied Zstandard archive and composes Aspose.Zip.Tar.TarArchive from extracted data.
<p>
Important: Zstandard archive is fully extracted within this method, its content is kept internally. Beware of memory consumption.
</p>

```csharp
public static TarArchive FromZstandard(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

#### Returns

 [TarArchive](/zip/aspose.zip.tar.tararchive)

An instance of Aspose.Zip.Tar.TarArchive

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">path</code> is empty, contains only white spaces, or contains invalid characters.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">path</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">path</code>  is in an invalid format.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified path is invalid, such as being on an unmapped drive.

 [FileNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.filenotfoundexception)

The file is not found.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

Zstandard stream is corrupted or not readable.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Data is corrupted.

### <a id="Aspose_Zip_Tar_TarArchive_Save_System_IO_Stream_System_Nullable_Aspose_Zip_Tar_TarFormat__"></a> Save\(Stream, TarFormat?\)

Saves archive to the stream provided.

```csharp
public void Save(Stream output, TarFormat? format = null)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)?

Defines the tar header format. Null value will be treated as USTar when possible.

#### Examples


```csharp
using (FileStream tarFile = File.Open("archive.tar", FileMode.Create))
{
    using (var archive = new TarArchive())
    {
        archive.CreateEntry("entry1", "data.bin");
        archive.Save(tarFile);
    }
}
```

#### Remarks

<p>
  <code class="paramref">output</code> must be writable.</p>

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">output</code> is not writable. - or - <code class="paramref">output</code> is the same stream we extract from.
        System.ObjectDisposedException?text=Archive+has+been+disposed+and+cannot+be+used
        - OR -
        It is impossible to save archive in <code class="paramref">format</code> due to format restrictions.

### <a id="Aspose_Zip_Tar_TarArchive_Save_System_String_System_Nullable_Aspose_Zip_Tar_TarFormat__"></a> Save\(string, TarFormat?\)

Saves archive to a destination file provided.

```csharp
public void Save(string destinationFileName, TarFormat? format = null)
```

#### Parameters

`destinationFileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)?

Defines the tar header format. Null value will be treated as USTar when possible.

#### Examples


```csharp
using (var archive = new TarArchive())
{
    archive.CreateEntry("entry1", "data.bin");        
    archive.Save("myarchive.tar");
}
```

#### Remarks

<p>It is possible to save an archive to the same path as it was loaded from.
        However, this is not recommended because this approach uses copying to a temporary file.</p>

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destinationFileName</code> is a zero-length string, contains only white space, or contains one or more invalid characters as defined by System.IO.Path.InvalidPathChars.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">destinationFileName</code> is null.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">destinationFileName</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified <code class="paramref">destinationFileName</code> is invalid, (for example, it is on an unmapped drive).

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

An I/O error occurred while opening the file.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

<code class="paramref">destinationFileName</code> specified a file that is read-only and access is not Read.-or- path specified a directory.-or- The caller does not have the required permission.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

<code class="paramref">destinationFileName</code> is in an invalid format.

 [FileNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.filenotfoundexception)

The file is not found.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_SaveGzipped_System_IO_Stream_System_Nullable_Aspose_Zip_Tar_TarFormat__"></a> SaveGzipped\(Stream, TarFormat?\)

Saves archive to the stream with gzip compression.

```csharp
public void SaveGzipped(Stream output, TarFormat? format = null)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)?

Defines the tar header format. Null value will be treated as USTar when possible.

#### Examples


```csharp
using (FileStream result = File.OpenWrite("result.tar.gz"))
{
    using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
    {
        using (var archive = new TarArchive())
        {
            archive.CreateEntry("entry.bin", source);
            archive.SaveGzipped(result);
        }
    }
}
```

#### Remarks

<p>
  <code class="paramref">output</code> must be writable.</p>

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">output</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">output</code> is not writable.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_SaveGzipped_System_String_System_Nullable_Aspose_Zip_Tar_TarFormat__"></a> SaveGzipped\(string, TarFormat?\)

Saves archive to the file by path with gzip compression.

```csharp
public void SaveGzipped(string path, TarFormat? format = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)?

Defines the tar header format. Null value will be treated as USTar when possible.

#### Examples


```csharp
using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
{
    using (var archive = new TarArchive())
    {
        archive.CreateEntry("entry.bin", source);
        archive.SaveGzipped("result.tar.gz");
    }
}
```

#### Exceptions

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

The caller does not have the required permission. -or- <code class="paramref">path</code> specified a read-only file or directory.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">path</code> is a zero-length string, contains only white space, or contains one or more invalid characters as defined by InvalidPathChars.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified <code class="paramref">path</code> is invalid, (for example, it is on an unmapped drive).

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

<code class="paramref">path</code> is in an invalid format.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_SaveLZ4Compressed_System_IO_Stream_System_Nullable_Aspose_Zip_Tar_TarFormat__"></a> SaveLZ4Compressed\(Stream, TarFormat?\)

Saves archive to the stream with LZ4 compression.

```csharp
public void SaveLZ4Compressed(Stream output, TarFormat? format = null)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)?

Defines the tar header format. Null value will be treated as USTar when possible.

#### Examples


```csharp
using (FileStream result = File.OpenWrite("result.tar.lz4"))
{
    using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
    {
        using (var archive = new TarArchive())
        {
            archive.CreateEntry("entry.bin", source);
            archive.SaveLZ4Compressed(result);
        }
    }
}
```

#### Remarks

<p>
  <code class="paramref">output</code> must be writable.</p>

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">output</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">output</code> is not writable.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_SaveLZ4Compressed_System_String_System_Nullable_Aspose_Zip_Tar_TarFormat__"></a> SaveLZ4Compressed\(string, TarFormat?\)

Saves archive to the file by path with LZ4 compression.

```csharp
public void SaveLZ4Compressed(string path, TarFormat? format = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)?

Defines the tar header format. Null value will be treated as USTar when possible.

#### Examples


```csharp
using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
{
    using (var archive = new TarArchive())
    {
        archive.CreateEntry("entry.bin", source);
        archive.SaveLZ4Compressed("result.tar.lz4");
    }
}
```

#### Exceptions

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

The caller does not have the required permission. -or- <code class="paramref">path</code> specified a read-only file or directory.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">path</code> is a zero-length string, contains only white space, or contains one or more invalid characters as defined by InvalidPathChars.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified <code class="paramref">path</code> is invalid, (for example, it is on an unmapped drive).

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

<code class="paramref">path</code> is in an invalid format.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_SaveLZMACompressed_System_IO_Stream_System_Nullable_Aspose_Zip_Tar_TarFormat__"></a> SaveLZMACompressed\(Stream, TarFormat?\)

Saves archive to the stream with LZMA compression.

```csharp
public void SaveLZMACompressed(Stream output, TarFormat? format = null)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)?

Defines the tar header format. Null value will be treated as USTar when possible.

#### Examples


```csharp
using (FileStream result = File.OpenWrite("result.tar.lzma"))
{
    using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
    {
        using (var archive = new TarArchive())
        {
            archive.CreateEntry("entry.bin", source);
            archive.SaveLZMACompressed(result);
        }
    }
}
```

#### Remarks

<p>
  <code class="paramref">output</code> must be writable.</p>
        Important: tar archive is composed then compressed within this method, its content is kept internally. Beware of memory consumption.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">output</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">output</code> is not writable.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_SaveLZMACompressed_System_String_System_Nullable_Aspose_Zip_Tar_TarFormat__"></a> SaveLZMACompressed\(string, TarFormat?\)

Saves archive to the file by path with lzma compression.

```csharp
public void SaveLZMACompressed(string path, TarFormat? format = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)?

Defines the tar header format. Null value will be treated as USTar when possible.

#### Examples


```csharp
using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
{
    using (var archive = new TarArchive())
    {
        archive.CreateEntry("entry.bin", source);
        archive.SaveLZMACompressed("result.tar.lzma");
    }
}
```

#### Remarks

Important: tar archive is composed then compressed within this method, its content is kept internally. Beware of memory consumption.

#### Exceptions

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

The caller does not have the required permission. -or- <code class="paramref">path</code> specified a read-only file or directory.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">path</code> is a zero-length string, contains only white space, or contains one or more invalid characters as defined by InvalidPathChars.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified <code class="paramref">path</code> is invalid, (for example, it is on an unmapped drive).

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

<code class="paramref">path</code> is in an invalid format.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_SaveLzipped_System_IO_Stream_System_Nullable_Aspose_Zip_Tar_TarFormat__"></a> SaveLzipped\(Stream, TarFormat?\)

Saves archive to the stream with lzip compression.

```csharp
public void SaveLzipped(Stream output, TarFormat? format = null)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)?

Defines the tar header format. Null value will be treated as USTar when possible.

#### Examples


```csharp
using (FileStream result = File.OpenWrite("result.tar.lz"))
{
    using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
    {
        using (var archive = new TarArchive())
        {
            archive.CreateEntry("entry.bin", source);
            archive.SaveLzipped(result);
        }
    }
}
```

#### Remarks

<p>
  <code class="paramref">output</code> must be writable.</p>

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">output</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">output</code> is not writable.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_SaveLzipped_System_String_System_Nullable_Aspose_Zip_Tar_TarFormat__"></a> SaveLzipped\(string, TarFormat?\)

Saves archive to the file by path with lzip compression.

```csharp
public void SaveLzipped(string path, TarFormat? format = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)?

Defines the tar header format. Null value will be treated as USTar when possible.

#### Examples


```csharp
using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
{
    using (var archive = new TarArchive())
    {
        archive.CreateEntry("entry.bin", source);
        archive.SaveGzipped("result.tar.lz");
    }
}
```

#### Exceptions

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

The caller does not have the required permission. -or- <code class="paramref">path</code> specified a read-only file or directory.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">path</code> is a zero-length string, contains only white space, or contains one or more invalid characters as defined by InvalidPathChars.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified <code class="paramref">path</code> is invalid, (for example, it is on an unmapped drive).

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

<code class="paramref">path</code> is in an invalid format.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_SaveXzCompressed_System_IO_Stream_System_Nullable_Aspose_Zip_Tar_TarFormat__Aspose_Zip_Xz_Settings_XzArchiveSettings_"></a> SaveXzCompressed\(Stream, TarFormat?, XzArchiveSettings\)

Saves archive to the stream with xz compression.

```csharp
public void SaveXzCompressed(Stream output, TarFormat? format = null, XzArchiveSettings settings = null)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)?

Defines the tar header format. Null value will be treated as USTar when possible.

`settings` [XzArchiveSettings](/zip/aspose.zip.xz.settings.xzarchivesettings)

Set of setting particular xz archive: dictionary size, block size, check type.

#### Examples


```csharp
using (FileStream result = File.OpenWrite("result.tar.xz"))
{
    using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
    {
        using (var archive = new TarArchive())
        {
            archive.CreateEntry("entry.bin", source);
            archive.SaveXzCompressed(result);
        }
    }
}
```

#### Remarks

<p>
  <code class="paramref">output</code>The stream must be writable.</p>

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">output</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">output</code> is not writable.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_SaveXzCompressed_System_String_System_Nullable_Aspose_Zip_Tar_TarFormat__Aspose_Zip_Xz_Settings_XzArchiveSettings_"></a> SaveXzCompressed\(string, TarFormat?, XzArchiveSettings\)

Saves archive to the path by path with xz compression.

```csharp
public void SaveXzCompressed(string path, TarFormat? format = null, XzArchiveSettings settings = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)?

Defines the tar header format. Null value will be treated as USTar when possible.

`settings` [XzArchiveSettings](/zip/aspose.zip.xz.settings.xzarchivesettings)

Set of setting particular xz archive: dictionary size, block size, check type.

#### Examples


```csharp
using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
{
    using (var archive = new TarArchive())
    {
        archive.CreateEntry("entry.bin", source);
        archive.SaveXzCompressed("result.tar.xz");
    }
}
```

#### Exceptions

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

The caller does not have the required permission. -or- <code class="paramref">path</code> specified a read-only file or directory.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">path</code> is a zero-length string, contains only white space, or contains one or more invalid characters as defined by InvalidPathChars.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified <code class="paramref">path</code> is invalid, (for example, it is on an unmapped drive).

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

<code class="paramref">path</code> is in an invalid format.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_SaveZCompressed_System_IO_Stream_System_Nullable_Aspose_Zip_Tar_TarFormat__"></a> SaveZCompressed\(Stream, TarFormat?\)

Saves archive to the stream with Z compression.

```csharp
public void SaveZCompressed(Stream output, TarFormat? format = null)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)?

Defines the tar header format. Null value will be treated as USTar when possible.

#### Examples


```csharp
using (FileStream result = File.OpenWrite("result.tar.Z"))
{
    using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
    {
        using (var archive = new TarArchive())
        {
            archive.CreateEntry("entry.bin", source);
            archive.SaveZCompressed(result);
        }
    }
}
```

#### Remarks

<p>
  <code class="paramref">output</code> must be writable.</p>

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">output</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">output</code> is not writable.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_SaveZCompressed_System_String_System_Nullable_Aspose_Zip_Tar_TarFormat__"></a> SaveZCompressed\(string, TarFormat?\)

Saves archive to the path by path with Z compression.

```csharp
public void SaveZCompressed(string path, TarFormat? format = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)?

Defines the tar header format. Null value will be treated as USTar when possible.

#### Examples


```csharp
using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
{
    using (var archive = new TarArchive())
    {
        archive.CreateEntry("entry.bin", source);
        archive.SaveZCompressed("result.tar.Z");
    }
}
```

#### Exceptions

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

The caller does not have the required permission. -or- <code class="paramref">path</code> specified a read-only file or directory.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">path</code> is a zero-length string, contains only white space, or contains one or more invalid characters as defined by InvalidPathChars.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified <code class="paramref">path</code> is invalid, (for example, it is on an unmapped drive).

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

<code class="paramref">path</code> is in an invalid format.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_SaveZstandard_System_IO_Stream_System_Nullable_Aspose_Zip_Tar_TarFormat__"></a> SaveZstandard\(Stream, TarFormat?\)

Saves archive to the stream with Zstandard compression.

```csharp
public void SaveZstandard(Stream output, TarFormat? format = null)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)?

Defines the tar header format. Null value will be treated as USTar when possible.

#### Examples


```csharp
using (FileStream result = File.OpenWrite("result.tar.zst"))
{
    using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
    {
        using (var archive = new TarArchive())
        {
            archive.CreateEntry("entry.bin", source);
            archive.SaveZstandard(result);
        }
    }
}
```

#### Remarks

<p>
  <code class="paramref">output</code> must be writable.</p>

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">output</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">output</code> is not writable.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used

### <a id="Aspose_Zip_Tar_TarArchive_SaveZstandard_System_String_System_Nullable_Aspose_Zip_Tar_TarFormat__"></a> SaveZstandard\(string, TarFormat?\)

Saves archive to the file by path with Zstandard compression.

```csharp
public void SaveZstandard(string path, TarFormat? format = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`format` [TarFormat](/zip/aspose.zip.tar.tarformat)?

Defines the tar header format. Null value will be treated as USTar when possible.

#### Examples


```csharp
using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
{
    using (var archive = new TarArchive())
    {
        archive.CreateEntry("entry.bin", source);
        archive.SaveZstandard("result.tar.zst");
    }
}
```

#### Exceptions

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

The caller does not have the required permission. -or- <code class="paramref">path</code> specified a read-only file or directory.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">path</code> is a zero-length string, contains only white space, or contains one or more invalid characters as defined by InvalidPathChars.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">path</code> is null.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">path</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified <code class="paramref">path</code> is invalid, (for example, it is on an unmapped drive).

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

<code class="paramref">path</code> is in an invalid format.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used
