---
linkTitle: "Class Archive"
title: "Class Archive"
description: "This class represents a zip archive file. Use it to compose, extract, or update zip archives."
summary: "This class represents a zip archive file. Use it to compose, extract, or update zip archives."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip](/zip/)  
Assembly: Aspose.Zip.dll (25.12.0)  

This class represents a zip archive file. Use it to compose, extract, or update zip archives.

```csharp
public class Archive : IArchive, IDisposable
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[Archive](/zip/aspose.zip.archive)

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

### <a id="Aspose_Zip_Archive__ctor_Aspose_Zip_Saving_ArchiveEntrySettings_"></a> Archive\(ArchiveEntrySettings\)

Initializes a new instance of the Aspose.Zip.Archive class with optional settings for its entries.

```csharp
public Archive(ArchiveEntrySettings newEntrySettings = null)
```

#### Parameters

`newEntrySettings` [ArchiveEntrySettings](/zip/aspose.zip.saving.archiveentrysettings)

Compression and encryption settings used for newly added Aspose.Zip.ArchiveEntry items.
            If not specified, the most common Deflate compression without encryption would be used.

#### Examples

<p>
        The following example shows how to compress a single file with default settings.
        </p>

```csharp
using (FileStream zipFile = File.Open("archive.zip", FileMode.Create))
{
    using (var archive = new Archive())
    {
        archive.CreateEntry("data.bin", "file.dat");
        archive.Save(zipFile);
    }
}
```

### <a id="Aspose_Zip_Archive__ctor_System_IO_Stream_Aspose_Zip_ArchiveLoadOptions_Aspose_Zip_Saving_ArchiveEntrySettings_"></a> Archive\(Stream, ArchiveLoadOptions, ArchiveEntrySettings\)

Initializes a new instance of the Aspose.Zip.Archive class and composes an entry list can be extracted from the archive.

```csharp
public Archive(Stream sourceStream, ArchiveLoadOptions loadOptions = null, ArchiveEntrySettings newEntrySettings = null)
```

#### Parameters

`sourceStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

`loadOptions` [ArchiveLoadOptions](/zip/aspose.zip.archiveloadoptions)

Options to load existing archive with.

`newEntrySettings` [ArchiveEntrySettings](/zip/aspose.zip.saving.archiveentrysettings)

Compression and encryption settings used for newly added Aspose.Zip.ArchiveEntry items.
            If not specified, the most common Deflate compression without encryption would be used.

#### Examples

<p>The following example extracts an encrypted archive, then decompresses first entry to a <code>MemoryStream</code>.</p>

```csharp
var fs = File.OpenRead("encrypted.zip");
var extracted = new MemoryStream();
using (Archive archive = new Archive(fs, new ArchiveLoadOptions() { DecryptionPassword = "p@s$" }))
{
    using (var decompressed = archive.Entries[0].Open())
    {
        byte[] b = new byte[8192];
        int bytesRead;
        while (0 &lt; (bytesRead = decompressed.Read(b, 0, b.Length)))
            extracted.Write(b, 0, bytesRead);
    }
}
```

#### Remarks

This constructor does not decompress any entry. See Aspose.Zip.ArchiveEntry.Open(System.String) method for decompressing.

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">sourceStream</code> is not seekable.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Encryption header for AES contradicts WinZip compression method.

### <a id="Aspose_Zip_Archive__ctor_System_String_Aspose_Zip_ArchiveLoadOptions_Aspose_Zip_Saving_ArchiveEntrySettings_"></a> Archive\(string, ArchiveLoadOptions, ArchiveEntrySettings\)

Initializes a new instance of the Aspose.Zip.Archive class and composes an entry list can be extracted from the archive.

```csharp
public Archive(string path, ArchiveLoadOptions loadOptions = null, ArchiveEntrySettings newEntrySettings = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The fully qualified or the relative path to the archive file.

`loadOptions` [ArchiveLoadOptions](/zip/aspose.zip.archiveloadoptions)

Options to load existing archive with.

`newEntrySettings` [ArchiveEntrySettings](/zip/aspose.zip.saving.archiveentrysettings)

Compression and encryption settings used for newly added Aspose.Zip.ArchiveEntry items.
            If not specified, the most common Deflate compression without encryption would be used.

#### Examples

<p>The following example extracts an encrypted archive, then decompresses first entry to a <code>MemoryStream</code>.</p>

```csharp
var extracted = new MemoryStream();
using (Archive archive = new Archive("encrypted.zip", new ArchiveLoadOptions() { DecryptionPassword = "p@s$" }))
{
    using (var decompressed = archive.Entries[0].Open())
    {
        byte[] b = new byte[8192];
        int bytesRead;
        while (0 &lt; (bytesRead = decompressed.Read(b, 0, b.Length)))
            extracted.Write(b, 0, bytesRead);
    }
}
```

#### Remarks

This constructor does not decompress any entry. See Aspose.Zip.ArchiveEntry.Open(System.String) method for decompressing.

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

The file is corrupted.

### <a id="Aspose_Zip_Archive__ctor_System_String_System_String___Aspose_Zip_ArchiveLoadOptions_"></a> Archive\(string, string\[\], ArchiveLoadOptions\)

Initializes a new instance of the Aspose.Zip.Archive class from multi-volume ZIP archive and composes an entry list can be extracted from the archive.

```csharp
public Archive(string mainSegment, string[] segmentsInOrder, ArchiveLoadOptions loadOptions = null)
```

#### Parameters

`mainSegment` [string](https://learn.microsoft.com/dotnet/api/system.string)

Path to the last segment of multi-volume archive with the central directory.
            <p>Usually this segment has *.zip extension and smaller than others.</p>

`segmentsInOrder` [string](https://learn.microsoft.com/dotnet/api/system.string)\[\]

Paths to each segment but the last of multi-volume zip archive respecting order. 
            <p>Usually they named filename.z01, filename.z02, ..., filename.z(n-1).</p>

`loadOptions` [ArchiveLoadOptions](/zip/aspose.zip.archiveloadoptions)

Options to load existing archive with.

#### Examples

This sample extract to a directory an archive of three segments.

```csharp
using (Archive a = new Archive("archive.zip", new string[] { "archive.z01", "archive.z02" }))
{
    a.ExtractToDirectory("destination");
}
```

#### Exceptions

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

Cannot load ZIP headers because provided files are corrupted.

## Properties

### <a id="Aspose_Zip_Archive_Entries"></a> Entries

Gets entries of Aspose.Zip.ArchiveEntry type constituting the archive.

```csharp
public ReadOnlyCollection<ArchiveEntry> Entries { get; }
```

#### Property Value

 [ReadOnlyCollection](https://learn.microsoft.com/dotnet/api/system.collections.objectmodel.readonlycollection\-1)<[ArchiveEntry](/zip/aspose.zip.archiveentry)\>

### <a id="Aspose_Zip_Archive_NewEntrySettings"></a> NewEntrySettings

Compression and encryption settings used for newly added Aspose.Zip.ArchiveEntry items.

```csharp
public ArchiveEntrySettings NewEntrySettings { get; }
```

#### Property Value

 [ArchiveEntrySettings](/zip/aspose.zip.saving.archiveentrysettings)

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

## Methods

### <a id="Aspose_Zip_Archive_CreateEntries_System_IO_DirectoryInfo_System_Boolean_"></a> CreateEntries\(DirectoryInfo, bool\)

Add to the archive all files and directories recursively in the directory given.

```csharp
public Archive CreateEntries(DirectoryInfo directory, bool includeRootDirectory = true)
```

#### Parameters

`directory` [DirectoryInfo](https://learn.microsoft.com/dotnet/api/system.io.directoryinfo)

Directory to compress.

`includeRootDirectory` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Indicates whether to include the root directory itself or not.

#### Returns

 [Archive](/zip/aspose.zip.archive)

The archive with entries composed.

#### Examples


```csharp
using (Archive archive = new Archive())
{
    DirectoryInfo folder = new DirectoryInfo("C:\folder");
    archive.CreateEntries(folder);
    archive.Save("folder.zip");
}
```

#### Exceptions

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The path to <code class="paramref">directory</code> is invalid, such as being on an unmapped drive.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access <code class="paramref">directory</code>.

### <a id="Aspose_Zip_Archive_CreateEntries_System_String_System_Boolean_"></a> CreateEntries\(string, bool\)

Add to the archive all files and directories recursively in the directory given.

```csharp
public Archive CreateEntries(string sourceDirectory, bool includeRootDirectory = true)
```

#### Parameters

`sourceDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

Directory to compress.

`includeRootDirectory` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Indicates whether to include the root directory itself or not.

#### Returns

 [Archive](/zip/aspose.zip.archive)

The archive with entries composed.

#### Examples


```csharp
using (Archive archive = new Archive())
{
    archive.CreateEntries("C:\folder");
    archive.Save("folder.zip");
}
```

### <a id="Aspose_Zip_Archive_CreateEntry_System_String_System_String_System_Boolean_Aspose_Zip_Saving_ArchiveEntrySettings_"></a> CreateEntry\(string, string, bool, ArchiveEntrySettings\)

Create a single entry within the archive.

```csharp
public ArchiveEntry CreateEntry(string name, string path, bool openImmediately = false, ArchiveEntrySettings newEntrySettings = null)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The fully qualified name of the new file, or the relative file name to be compressed.

`openImmediately` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

True, if open the file immediately, otherwise open the file on archive saving.

`newEntrySettings` [ArchiveEntrySettings](/zip/aspose.zip.saving.archiveentrysettings)

Compression and encryption settings used for added Aspose.Zip.ArchiveEntry item.

#### Returns

 [ArchiveEntry](/zip/aspose.zip.archiveentry)

Zip entry instance.

#### Examples


```csharp
using (FileStream zipFile = File.Open("archive.zip", FileMode.Create))
{
    using (var archive = new Archive())
    {
        archive.CreateEntry("data.bin", "file.dat");
        archive.Save(zipFile);
    }
}
```

#### Remarks

<p>The entry name is solely set within <code class="paramref">name</code> parameter. The file name provided in <code class="paramref">path</code> parameter does not affect the entry name.</p>
<p>If the file is opened immediately with <code class="paramref">openImmediately</code> parameter it becomes blocked until archive is saved.</p>

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

### <a id="Aspose_Zip_Archive_CreateEntry_System_String_System_IO_Stream_Aspose_Zip_Saving_ArchiveEntrySettings_"></a> CreateEntry\(string, Stream, ArchiveEntrySettings\)

Create a single entry within the archive.

```csharp
public ArchiveEntry CreateEntry(string name, Stream source, ArchiveEntrySettings newEntrySettings = null)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The input stream for the entry.

`newEntrySettings` [ArchiveEntrySettings](/zip/aspose.zip.saving.archiveentrysettings)

Compression and encryption settings used for added Aspose.Zip.ArchiveEntry item.

#### Returns

 [ArchiveEntry](/zip/aspose.zip.archiveentry)

Zip entry instance.

#### Examples


```csharp
using (var archive = new Archive(new ArchiveEntrySettings(null, new AesEcryptionSettings("p@s$", EncryptionMethod.AES256))))
{
    archive.CreateEntry("data.bin", new MemoryStream(new byte[] {0x00, 0xFF} ));
    archive.Save("archive.zip");
}
```

### <a id="Aspose_Zip_Archive_CreateEntry_System_String_System_IO_FileInfo_System_Boolean_Aspose_Zip_Saving_ArchiveEntrySettings_"></a> CreateEntry\(string, FileInfo, bool, ArchiveEntrySettings\)

Create a single entry within the archive.

```csharp
public ArchiveEntry CreateEntry(string name, FileInfo fileInfo, bool openImmediately = false, ArchiveEntrySettings newEntrySettings = null)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`fileInfo` [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

The metadata of file to be compressed.

`openImmediately` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

True, if open the file immediately, otherwise open the file on archive saving.

`newEntrySettings` [ArchiveEntrySettings](/zip/aspose.zip.saving.archiveentrysettings)

Compression and encryption settings used for added Aspose.Zip.ArchiveEntry item.

#### Returns

 [ArchiveEntry](/zip/aspose.zip.archiveentry)

Zip entry instance.

#### Examples

<p>Compose archive with entries encrypted with different encryption methods and passwords each.</p>

```csharp
using (FileStream zipFile = File.Open("archive.zip", FileMode.Create))
{
    FileInfo fi1 = new FileInfo("data1.bin");
    FileInfo fi2 = new FileInfo("data2.bin");
    FileInfo fi3 = new FileInfo("data3.bin");
    using (var archive = new Archive())
    {
        archive.CreateEntry("entry1.bin", fi1, false, new ArchiveEntrySettings(new DeflateCompressionSettings(), new TraditionalEncryptionSettings("pass1")));
        archive.CreateEntry("entry2.bin", fi2, false, new ArchiveEntrySettings(new DeflateCompressionSettings(), new AesEcryptionSettings("pass2", EncryptionMethod.AES128)));
        archive.CreateEntry("entry3.bin", fi3, false, new ArchiveEntrySettings(new DeflateCompressionSettings(), new AesEcryptionSettings("pass3", EncryptionMethod.AES256)));
        archive.Save(zipFile);
    }
}
```

#### Remarks

<p>The entry name is solely set within <code class="paramref">name</code> parameter. The file name provided in <code class="paramref">fileInfo</code> parameter does not affect the entry name.</p>
<p>If the file is opened immediately with <code class="paramref">openImmediately</code> parameter it becomes blocked until archive is saved.</p>

#### Exceptions

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

<code class="paramref">fileInfo</code> is read-only or is a directory.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified path is invalid, such as being on an unmapped drive.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The file is already open.

### <a id="Aspose_Zip_Archive_CreateEntry_System_String_System_IO_Stream_Aspose_Zip_Saving_ArchiveEntrySettings_System_IO_FileSystemInfo_"></a> CreateEntry\(string, Stream, ArchiveEntrySettings, FileSystemInfo\)

Create a single entry within the archive.

```csharp
public ArchiveEntry CreateEntry(string name, Stream source, ArchiveEntrySettings newEntrySettings, FileSystemInfo fileInfo)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The input stream for the entry.

`newEntrySettings` [ArchiveEntrySettings](/zip/aspose.zip.saving.archiveentrysettings)

Compression and encryption settings used for added Aspose.Zip.ArchiveEntry item.

`fileInfo` [FileSystemInfo](https://learn.microsoft.com/dotnet/api/system.io.filesysteminfo)

The metadata of file or folder to be compressed.

#### Returns

 [ArchiveEntry](/zip/aspose.zip.archiveentry)

Zip entry instance.

#### Examples

<p>Compose archive with encrypted entry.</p>

```csharp
using (FileStream zipFile = File.Open("archive.zip", FileMode.Create))
{
    using (var archive = new Archive())
    {
        archive.CreateEntry("entry1.bin", new MemoryStream(new byte[] {0x00, 0xFF} ), new ArchiveEntrySettings(new DeflateCompressionSettings(), new TraditionalEncryptionSettings("pass1")), new FileInfo("data1.bin")); 
        archive.Save(zipFile);
    }
}
```

#### Remarks

<p>The entry name is solely set within <code class="paramref">name</code> parameter. The file name provided in <code class="paramref">fileInfo</code> parameter does not affect the entry name.</p>
<p>
  <code class="paramref">fileInfo</code> can refer to System.IO.DirectoryInfo if the entry is directory.</p>

#### Exceptions

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

Both <code class="paramref">source</code> and <code class="paramref">fileInfo</code> are null or <code class="paramref">source</code> is null and <code class="paramref">fileInfo</code> stands for directory.

### <a id="Aspose_Zip_Archive_CreateEntry_System_String_System_Func_System_IO_Stream__Aspose_Zip_Saving_ArchiveEntrySettings_"></a> CreateEntry\(string, Func<Stream\>, ArchiveEntrySettings\)

Create a single entry within the archive.

```csharp
public ArchiveEntry CreateEntry(string name, Func<Stream> streamProvider, ArchiveEntrySettings newEntrySettings = null)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`streamProvider` [Func](https://learn.microsoft.com/dotnet/api/system.func\-1)<[Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)\>

The method providing input stream for the entry.

`newEntrySettings` [ArchiveEntrySettings](/zip/aspose.zip.saving.archiveentrysettings)

Compression and encryption settings used for added Aspose.Zip.ArchiveEntry item.

#### Returns

 [ArchiveEntry](/zip/aspose.zip.archiveentry)

Zip entry instance.

#### Examples

<p>Compose archive with encrypted entry.</p>

```csharp
System.Func&lt;Stream&gt; provider = delegate(){ return new MemoryStream(new byte[]{0xFF, 0x00}); };
using (FileStream zipFile = File.Open("archive.zip", FileMode.Create))
{
    using (var archive = new Archive())
    {
        archive.CreateEntry("entry1.bin", provider, new ArchiveEntrySettings(new DeflateCompressionSettings(), new TraditionalEncryptionSettings("pass1")))); 
        archive.Save(zipFile);
    }
}
```

#### Remarks

<p>This method is for .NET Framework 4.0 and above and for .NET Standard 2.0 version.</p>

### <a id="Aspose_Zip_Archive_DeleteEntry_Aspose_Zip_ArchiveEntry_"></a> DeleteEntry\(ArchiveEntry\)

Removes the first occurrence of the specific entry from the entry list.

```csharp
public Archive DeleteEntry(ArchiveEntry entry)
```

#### Parameters

`entry` [ArchiveEntry](/zip/aspose.zip.archiveentry)

The entry to remove from the entries list.

#### Returns

 [Archive](/zip/aspose.zip.archive)

The archive with the entry deleted.

#### Examples

<p>Here is how you can remove all entries except the last one:</p>

```csharp
using (var archive = new Archive("archive.zip"))
{
    while (archive.Entries.Count &gt; 1)
        archive.DeleteEntry(archive.Entries[0]);
    archive.Save("last_entry.zip");
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

The archive is disposed.

### <a id="Aspose_Zip_Archive_DeleteEntry_System_Int32_"></a> DeleteEntry\(int\)

Removes the entry from the entry list by index.

```csharp
public Archive DeleteEntry(int entryIndex)
```

#### Parameters

`entryIndex` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The zero-based index of the entry to remove.

#### Returns

 [Archive](/zip/aspose.zip.archive)

The archive with the entry deleted.

#### Examples


```csharp
using (var archive = new TarArchive("two_files.zip"))
{
    archive.DeleteEntry(0);
    archive.Save("single_file.zip");
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive is disposed.

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

<code class="paramref">entryIndex</code> is less than 0.-or- <code class="paramref">entryIndex</code> is equal to or greater than <code>Entries</code> count.

### <a id="Aspose_Zip_Archive_Dispose"></a> Dispose\(\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_Archive_Dispose_System_Boolean_"></a> Dispose\(bool\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
protected virtual void Dispose(bool disposing)
```

#### Parameters

`disposing` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether managed resources should be disposed.

### <a id="Aspose_Zip_Archive_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

Extracts all the files in the archive to the directory provided.

```csharp
public void ExtractToDirectory(string destinationDirectory)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory to place the extracted files in.

#### Examples


```csharp
using (var archive = new Archive("archive.zip")) 
{ 
   archive.ExtractToDirectory("C:\extracted");
}
```

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

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Wrong password has been supplied. - or - Archive is corrupted.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Archive_Save_System_IO_Stream_Aspose_Zip_Saving_ArchiveSaveOptions_"></a> Save\(Stream, ArchiveSaveOptions\)

Saves archive to the stream provided.

```csharp
public void Save(Stream outputStream, ArchiveSaveOptions saveOptions = null)
```

#### Parameters

`outputStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`saveOptions` [ArchiveSaveOptions](/zip/aspose.zip.saving.archivesaveoptions)

Options for archive saving.

#### Examples


```csharp
using (FileStream zipFile = File.Open("archive.zip", FileMode.Create))
{
    using (var archive = new Archive())
    {
        archive.CreateEntry("entry.bin", "data.bin");
        archive.Save(zipFile);
    }
}
```

#### Remarks

<p>
  <code class="paramref">outputStream</code> must be writable.</p>

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">outputStream</code> is not writable.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

The archive is disposed.

### <a id="Aspose_Zip_Archive_Save_System_String_Aspose_Zip_Saving_ArchiveSaveOptions_"></a> Save\(string, ArchiveSaveOptions\)

Saves archive to the destination file provided.

```csharp
public void Save(string destinationFileName, ArchiveSaveOptions saveOptions = null)
```

#### Parameters

`destinationFileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`saveOptions` [ArchiveSaveOptions](/zip/aspose.zip.saving.archivesaveoptions)

Options for archive saving.

#### Examples


```csharp
using (var archive = new Archive())
{
    archive.CreateEntry("entry.bin", "data.bin");
    archive.Save("archive.zip",  new ArchiveSaveOptions() { Encoding = Encoding.ASCII });
}
```

#### Remarks

<p>It is possible to save an archive to the same path as it was loaded from.
        However, this is not recommended because this approach uses copying to a temporary file.</p>

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

The specified <code class="paramref">destinationFileName</code>, file name, or both exceed the system-defined maximum length. 
           For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">destinationFileName</code> contains a colon (:) in the middle of the string.

 [FileNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.filenotfoundexception)

The file is not found.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified path is invalid, such as being on an unmapped drive.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The file is already open.

### <a id="Aspose_Zip_Archive_SaveSplit_System_String_Aspose_Zip_Saving_SplitArchiveSaveOptions_"></a> SaveSplit\(string, SplitArchiveSaveOptions\)

Saves multi-volume archive to destination directory provided.

```csharp
public void SaveSplit(string destinationDirectory, SplitArchiveSaveOptions options)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory where archive segments to be created.

`options` [SplitArchiveSaveOptions](/zip/aspose.zip.saving.splitarchivesaveoptions)

Options for archive saving, including file name.

#### Examples


```csharp
using (Archive archive = new Archive())
{
    archive.CreateEntry("entry.bin", "data.bin");
    archive.SaveSplit(@"C:\Folder",  new SplitArchiveSaveOptions("volume", 65536));
}
```

#### Remarks

<p>This method composes several (<code>n</code>) files filename.z01, filename.z02, ..., filename.z(n-1), filename.zip.</p>
<p>Cannot make existing archive multi-volume.</p>

#### Exceptions

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

This archive was opened from the existing source.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

This archive is both compressed with XZ method and encrypted.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">destinationDirectory</code> is null.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access the directory.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destinationDirectory</code> contains invalid characters such as ", &gt;, &lt;, or |.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified path exceeds the system-defined maximum length.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

The archive is disposed.
