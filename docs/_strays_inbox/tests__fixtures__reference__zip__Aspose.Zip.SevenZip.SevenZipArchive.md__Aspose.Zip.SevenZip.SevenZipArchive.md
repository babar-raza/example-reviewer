---
linkTitle: "Class SevenZipArchive"
title: "Class SevenZipArchive"
description: "This class represents 7z archive file. Use it to compose and extract 7z archives."
summary: "This class represents 7z archive file. Use it to compose and extract 7z archives."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.SevenZip](/zip/aspose.zip.sevenzip)  
Assembly: Aspose.Zip.dll (25.12.0)  

This class represents 7z archive file. Use it to compose and extract 7z archives.

```csharp
public class SevenZipArchive : IArchive, IDisposable
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[SevenZipArchive](/zip/aspose.zip.sevenzip.sevenziparchive)

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

### <a id="Aspose_Zip_SevenZip_SevenZipArchive__ctor_Aspose_Zip_Saving_SevenZipEntrySettings_"></a> SevenZipArchive\(SevenZipEntrySettings\)

Initializes a new instance of the Aspose.Zip.SevenZip.SevenZipArchive class with optional settings for its entries.

```csharp
public SevenZipArchive(SevenZipEntrySettings newEntrySettings = null)
```

#### Parameters

`newEntrySettings` [SevenZipEntrySettings](/zip/aspose.zip.saving.sevenzipentrysettings)

Compression and encryption settings used for newly added Aspose.Zip.SevenZip.SevenZipArchiveEntry items.
            If not specified, LZMA compression without encryption would be used.

#### Examples

<p>
        The following example shows how to compress a single file with default settings: LZMA compression without encryption.
        </p>

```csharp
using (FileStream sevenZipFile = File.Open("archive.7z", FileMode.Create))
{
    using (var archive = new SevenZipArchive())
    {
        archive.CreateEntry("data.bin", "file.dat");
        archive.Save(sevenZipFile);
    }
}
```

### <a id="Aspose_Zip_SevenZip_SevenZipArchive__ctor_System_IO_Stream_System_String_"></a> SevenZipArchive\(Stream, string\)

Initializes a new instance of the Aspose.Zip.SevenZip.SevenZipArchive class and composes an entry list can be extracted from the archive.

```csharp
public SevenZipArchive(Stream sourceStream, string password = null)
```

#### Parameters

`sourceStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

`password` [string](https://learn.microsoft.com/dotnet/api/system.string)

Optional password for decryption. If file names are encrypted, it must be present.

#### Examples


```csharp
using (SevenZipArchive archive = new SevenZipArchive(File.OpenRead("archive.7z")))
{
    archive.ExtractToDirectory("C:\\extracted");
}
```

#### Remarks

This constructor does not decompress any entry. See Aspose.Zip.SevenZip.SevenZipArchive.ExtractToDirectory(System.String,System.String) method for decompressing.

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">sourceStream</code> is not seekable.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">sourceStream</code> is null.

 [NotImplementedException](https://learn.microsoft.com/dotnet/api/system.notimplementedexception)

The archive contains more than one coder. Now only LZMA compression supported.

### <a id="Aspose_Zip_SevenZip_SevenZipArchive__ctor_System_String_System_String_"></a> SevenZipArchive\(string, string\)

Initializes a new instance of the Aspose.Zip.SevenZip.SevenZipArchive class and composes an entry list can be extracted from the archive.

```csharp
public SevenZipArchive(string path, string password = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The fully qualified or the relative path to the archive file.

`password` [string](https://learn.microsoft.com/dotnet/api/system.string)

Optional password for decryption. If file names are encrypted, it must be present.

#### Examples


```csharp
using (SevenZipArchive archive = new SevenZipArchive("archive.7z"))
{
    archive.ExtractToDirectory("C:\\extracted");
}
```

#### Remarks

This constructor does not decompress any entry. See Aspose.Zip.SevenZip.SevenZipArchive.ExtractToDirectory(System.String,System.String) method for decompressing.

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

### <a id="Aspose_Zip_SevenZip_SevenZipArchive__ctor_System_IO_Stream_Aspose_Zip_SevenZip_SevenZipLoadOptions_"></a> SevenZipArchive\(Stream, SevenZipLoadOptions\)

Initializes a new instance of the Aspose.Zip.SevenZip.SevenZipArchive class and composes an entry list can be extracted from the archive.

```csharp
public SevenZipArchive(Stream sourceStream, SevenZipLoadOptions options)
```

#### Parameters

`sourceStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

`options` [SevenZipLoadOptions](/zip/aspose.zip.sevenzip.sevenziploadoptions)

Options to load existing archive with.

#### Examples

<p>Extract an encrypted archive. Allow up to 60 seconds to proceed, cancel after that period.</p>

```csharp
using(CancellationTokenSource cts = new CancellationTokenSource())
{
    SevenZipLoadOptions options = new SevenZipLoadOptions(){ DecryptionPassword = "Top$ecr3t", CancellationToken = cts.Token }
    cts.CancelAfter(TimeSpan.FromSeconds(60));
    using (SevenZipArchive archive = new SevenZipArchive(File.OpenRead("archive.7z"), options))
    {
        archive.ExtractToDirectory("C:\\extracted");
    }
}
```

#### Remarks

This constructor does not decompress any entry. See Aspose.Zip.SevenZip.SevenZipArchive.ExtractToDirectory(System.String,System.String) method for decompressing.

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">sourceStream</code> is not seekable.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">sourceStream</code> is null.

 [NotImplementedException](https://learn.microsoft.com/dotnet/api/system.notimplementedexception)

The archive contains more than one coder. Now only LZMA compression supported.

### <a id="Aspose_Zip_SevenZip_SevenZipArchive__ctor_System_String_Aspose_Zip_SevenZip_SevenZipLoadOptions_"></a> SevenZipArchive\(string, SevenZipLoadOptions\)

Initializes a new instance of the Aspose.Zip.SevenZip.SevenZipArchive class and composes an entry list can be extracted from the archive.

```csharp
public SevenZipArchive(string path, SevenZipLoadOptions options)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The fully qualified or the relative path to the archive file.

`options` [SevenZipLoadOptions](/zip/aspose.zip.sevenzip.sevenziploadoptions)

Options to load existing archive with.

#### Examples

<p>Extract an encrypted archive. Allow up to 60 seconds to proceed, cancel after that period.</p>

```csharp
using(CancellationTokenSource cts = new CancellationTokenSource())
{
    SevenZipLoadOptions options = new SevenZipLoadOptions(){ DecryptionPassword = "Top$ecr3t", CancellationToken = cts.Token }
    cts.CancelAfter(TimeSpan.FromSeconds(60));
    using (SevenZipArchive archive = new SevenZipArchive(File.OpenRead("archive.7z"), options))
    {
        archive.ExtractToDirectory("C:\\extracted");
    }
}
```

#### Remarks

This constructor does not decompress any entry. See Aspose.Zip.SevenZip.SevenZipArchive.ExtractToDirectory(System.String,System.String) method for decompressing.

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

### <a id="Aspose_Zip_SevenZip_SevenZipArchive__ctor_System_String___System_String_"></a> SevenZipArchive\(string\[\], string\)

Initializes a new instance of the Aspose.Zip.SevenZip.SevenZipArchive class from multi-volume 7z archive and composes an entry list can be extracted from the archive.

```csharp
public SevenZipArchive(string[] parts, string password = null)
```

#### Parameters

`parts` [string](https://learn.microsoft.com/dotnet/api/system.string)\[\]

Paths to each segment of multi-volume 7z archive respecting order

`password` [string](https://learn.microsoft.com/dotnet/api/system.string)

Optional password for decryption. If file names are encrypted, it must be present.

#### Examples


```csharp
using (SevenZipArchive archive = new SevenZipArchive(new string[] { "multi.7z.001", "multi.7z.002", "multi.7z.003" }))
{
    archive.ExtractToDirectory("C:\\extracted");
}
```

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">parts</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">parts</code> has no entries.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The path to a file is empty, contains only white spaces, or contains invalid characters.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to a file is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified path to a part, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at a path contains a colon (:) in the middle of the string.

## Properties

### <a id="Aspose_Zip_SevenZip_SevenZipArchive_Entries"></a> Entries

Gets entries of Aspose.Zip.SevenZip.SevenZipArchiveEntry type constituting the archive.

```csharp
public ReadOnlyCollection<SevenZipArchiveEntry> Entries { get; }
```

#### Property Value

 [ReadOnlyCollection](https://learn.microsoft.com/dotnet/api/system.collections.objectmodel.readonlycollection\-1)<[SevenZipArchiveEntry](/zip/aspose.zip.sevenzip.sevenziparchiveentry)\>

### <a id="Aspose_Zip_SevenZip_SevenZipArchive_NewEntrySettings"></a> NewEntrySettings

Compression and encryption settings used for newly added Aspose.Zip.SevenZip.SevenZipArchiveEntry items.

```csharp
public SevenZipEntrySettings NewEntrySettings { get; }
```

#### Property Value

 [SevenZipEntrySettings](/zip/aspose.zip.saving.sevenzipentrysettings)

## Methods

### <a id="Aspose_Zip_SevenZip_SevenZipArchive_CreateEntries_System_IO_DirectoryInfo_System_Boolean_"></a> CreateEntries\(DirectoryInfo, bool\)

Adds to the archive all files and directories recursively in the directory given.

```csharp
public SevenZipArchive CreateEntries(DirectoryInfo directory, bool includeRootDirectory = true)
```

#### Parameters

`directory` [DirectoryInfo](https://learn.microsoft.com/dotnet/api/system.io.directoryinfo)

Directory to compress.

`includeRootDirectory` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Indicates whether to include the root directory itself or not.

#### Returns

 [SevenZipArchive](/zip/aspose.zip.sevenzip.sevenziparchive)

The archive with entries composed.

#### Examples


```csharp
using (SevenZipArchive archive = new SevenZipArchive())
{
    DirectoryInfo folder = new DirectoryInfo("C:\folder");
    archive.CreateEntries(folder);
    archive.Save("folder.7z");
}
```

#### Exceptions

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The path to <code class="paramref">directory</code> is invalid, such as being on an unmapped drive.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access <code class="paramref">directory</code>.

### <a id="Aspose_Zip_SevenZip_SevenZipArchive_CreateEntries_System_String_System_Boolean_"></a> CreateEntries\(string, bool\)

Adds to the archive all files and directories recursively in the directory given.

```csharp
public SevenZipArchive CreateEntries(string sourceDirectory, bool includeRootDirectory = true)
```

#### Parameters

`sourceDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

Directory to compress.

`includeRootDirectory` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Indicates whether to include the root directory itself or not.

#### Returns

 [SevenZipArchive](/zip/aspose.zip.sevenzip.sevenziparchive)

The archive with entries composed.

#### Examples

<p>Compose 7z archive with LZMA2 compression.</p>

```csharp
using (SevenZipArchive archive = new SevenZipArchive(new SevenZipEntrySettings(new SevenZipLZMACompressionSettings())))
{
    archive.CreateEntries("C:\folder");
    archive.Save("folder.7z");
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_SevenZip_SevenZipArchive_CreateEntry_System_String_System_IO_FileInfo_System_Boolean_Aspose_Zip_Saving_SevenZipEntrySettings_"></a> CreateEntry\(string, FileInfo, bool, SevenZipEntrySettings\)

Create a single entry within the archive.

```csharp
public SevenZipArchiveEntry CreateEntry(string name, FileInfo fileInfo, bool openImmediately = false, SevenZipEntrySettings newEntrySettings = null)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`fileInfo` [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

The metadata of file to be compressed.

`openImmediately` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

True, if open the file immediately, otherwise open the file on archive saving.

`newEntrySettings` [SevenZipEntrySettings](/zip/aspose.zip.saving.sevenzipentrysettings)

Compression and encryption settings used for added Aspose.Zip.SevenZip.SevenZipArchiveEntry item. 
            Individual compression settings is ignored in case of solid compression, see Aspose.Zip.Saving.SevenZipEntrySettings.Solid.

#### Returns

 [SevenZipArchiveEntry](/zip/aspose.zip.sevenzip.sevenziparchiveentry)

Seven Zip entry instance.

#### Examples

<p>Compose archive with entries encrypted with different passwords each.</p>

```csharp
using (FileStream sevenZipFile = File.Open("archive.7z", FileMode.Create))
{
    FileInfo fi1 = new FileInfo("data1.bin");
    FileInfo fi2 = new FileInfo("data2.bin");
    FileInfo fi3 = new FileInfo("data3.bin");
    using (var archive = new SevenZipArchive())
    {
        archive.CreateEntry("entry1.bin", fi1, false, new SevenZipEntrySettings(new SevenZipStoreCompressionSettings(), new SevenZipAESEncryptionSettings("test1")));
        archive.CreateEntry("entry2.bin", fi2, false, new SevenZipEntrySettings(new SevenZipStoreCompressionSettings(), new SevenZipAESEncryptionSettings("test2")));
        archive.CreateEntry("entry3.bin", fi3, false, new SevenZipEntrySettings(new SevenZipStoreCompressionSettings(), new SevenZipAESEncryptionSettings("test3")));
        archive.Save(sevenZipFile);
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

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_SevenZip_SevenZipArchive_CreateEntry_System_String_System_IO_Stream_Aspose_Zip_Saving_SevenZipEntrySettings_System_IO_FileSystemInfo_"></a> CreateEntry\(string, Stream, SevenZipEntrySettings, FileSystemInfo\)

Create a single entry within the archive.

```csharp
public SevenZipArchiveEntry CreateEntry(string name, Stream source, SevenZipEntrySettings newEntrySettings, FileSystemInfo fileInfo)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The input stream for the entry.

`newEntrySettings` [SevenZipEntrySettings](/zip/aspose.zip.saving.sevenzipentrysettings)

Compression and encryption settings used for added Aspose.Zip.SevenZip.SevenZipArchiveEntry item.
             Individual compression settings is ignored in case of solid compression, see Aspose.Zip.Saving.SevenZipEntrySettings.Solid.

`fileInfo` [FileSystemInfo](https://learn.microsoft.com/dotnet/api/system.io.filesysteminfo)

The metadata of file or folder to be compressed.

#### Returns

 [SevenZipArchiveEntry](/zip/aspose.zip.sevenzip.sevenziparchiveentry)

SevenZip entry instance.

#### Examples

<p>Compose archive with LZMA2 compressed encrypted entry.</p>

```csharp
using (FileStream sevenZipFile = File.Open("archive.7z", FileMode.Create))
{
    using (var archive = new SevenZipArchive())
    {
        archive.CreateEntry("entry1.bin", new MemoryStream(new byte[] {0x00, 0xFF}), new SevenZipEntrySettings(new SevenZipLZMA2CompressionSettings(), new SevenZipAESEncryptionSettings("test1")), new FileInfo("data1.bin")); 
        archive.Save(sevenZipFile);
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

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_SevenZip_SevenZipArchive_CreateEntry_System_String_System_IO_Stream_Aspose_Zip_Saving_SevenZipEntrySettings_"></a> CreateEntry\(string, Stream, SevenZipEntrySettings\)

Create a single entry within the archive.

```csharp
public SevenZipArchiveEntry CreateEntry(string name, Stream source, SevenZipEntrySettings newEntrySettings = null)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The input stream for the entry.

`newEntrySettings` [SevenZipEntrySettings](/zip/aspose.zip.saving.sevenzipentrysettings)

Compression and encryption settings used for added Aspose.Zip.SevenZip.SevenZipArchiveEntry item.
             Individual compression settings is ignored in case of solid compression, see Aspose.Zip.Saving.SevenZipEntrySettings.Solid.

#### Returns

 [SevenZipArchiveEntry](/zip/aspose.zip.sevenzip.sevenziparchiveentry)

Zip entry instance.

#### Examples

<p>Compose 7z archive with LZMA2 compression and encryption of all entries.</p>

```csharp
using (var archive = new SevenZipArchive(new SevenZipEntrySettings(new SevenZipLZMA2CompressionSettings(), new SevenZipAESEncryptionSettings("p@s$"))))
{
    archive.CreateEntry("data.bin", new MemoryStream(new byte[] {0x00, 0xFF} ));
    archive.Save("archive.7z");
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_SevenZip_SevenZipArchive_CreateEntry_System_String_System_String_System_Boolean_Aspose_Zip_Saving_SevenZipEntrySettings_"></a> CreateEntry\(string, string, bool, SevenZipEntrySettings\)

Create a single entry within the archive.

```csharp
public SevenZipArchiveEntry CreateEntry(string name, string path, bool openImmediately = false, SevenZipEntrySettings newEntrySettings = null)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The fully qualified name of the new file, or the relative file name to be compressed.

`openImmediately` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

True, if open the file immediately, otherwise open the file on archive saving.

`newEntrySettings` [SevenZipEntrySettings](/zip/aspose.zip.saving.sevenzipentrysettings)

Compression and encryption settings used for added Aspose.Zip.SevenZip.SevenZipArchiveEntry item.
             Individual compression settings is ignored in case of solid compression, see Aspose.Zip.Saving.SevenZipEntrySettings.Solid.

#### Returns

 [SevenZipArchiveEntry](/zip/aspose.zip.sevenzip.sevenziparchiveentry)

Zip entry instance.

#### Examples


```csharp
using (FileStream sevenZipFile = File.Open("archive.7z", FileMode.Create))
{
    using (var archive = new SevenZipArchive(new SevenZipEntrySettings(new SevenZipLZMA2CompressionSettings())))
    {
        archive.CreateEntry("data.bin", "file.dat");
        archive.Save(sevenZipFile);
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

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">path</code> contains a colon (:) in the middle of the string.

### <a id="Aspose_Zip_SevenZip_SevenZipArchive_Dispose"></a> Dispose\(\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_SevenZip_SevenZipArchive_Dispose_System_Boolean_"></a> Dispose\(bool\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
protected virtual void Dispose(bool disposing)
```

#### Parameters

`disposing` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether managed resources should be disposed.

### <a id="Aspose_Zip_SevenZip_SevenZipArchive_ExtractToDirectory_System_String_System_String_"></a> ExtractToDirectory\(string, string\)

Extracts all the files in the archive to the directory provided.

```csharp
public void ExtractToDirectory(string destinationDirectory, string password = null)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory to place the extracted files in.

`password` [string](https://learn.microsoft.com/dotnet/api/system.string)

Optional password for content decryption.

#### Examples


```csharp
using (var archive = new SevenZipArchive("archive.7z")) 
{ 
   archive.ExtractToDirectory("C:\extracted");
}
```

#### Remarks

<p>If the directory does not exist, it will be created.</p>
<p>
  <code class="paramref">password</code> is used for content decryption only. If file names are encrypted provide password in Aspose.Zip.SevenZip.SevenZipArchive.#ctor(System.String,System.String), Aspose.Zip.SevenZip.SevenZipArchive.#ctor(System.IO.Stream,System.String), Aspose.Zip.SevenZip.SevenZipArchive.#ctor(System.IO.Stream,Aspose.Zip.SevenZip.SevenZipLoadOptions) or Aspose.Zip.SevenZip.SevenZipArchive.#ctor(System.IO.Stream,Aspose.Zip.SevenZip.SevenZipLoadOptions) constructor.</p>

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

<code class="paramref">destinationDirectory</code> is a zero-length string, contains only white space, or contains one or more invalid characters. You can query for invalid characters by using the System.IO.Path.GetInvalidPathChars method. -or- path is prefixed with, or contains, only a colon character (:).

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The directory specified by path is a file. -or- The network name is not known.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The archive is corrupted.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

### <a id="Aspose_Zip_SevenZip_SevenZipArchive_Save_System_IO_Stream_"></a> Save\(Stream\)

Saves 7z archive to the stream provided.

```csharp
public void Save(Stream output)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

#### Examples


```csharp
using (FileStream sevenZipFile = File.Open("archive.7z", FileMode.Create))
{
  using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
  {
    using (var archive = new SevenZipArchive())
    {
      archive.CreateEntry("data", source);
      archive.Save(sevenZipFile);
    }
  }
}
```

#### Remarks

<p>
  <code class="paramref">output</code> must be seekable.</p>

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">output</code> does not support seeking.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">output</code> is null.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

Encoder failed to compress data.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_SevenZip_SevenZipArchive_Save_System_String_"></a> Save\(string\)

Saves archive to a destination file provided.

```csharp
public void Save(string destinationFileName)
```

#### Parameters

`destinationFileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

#### Examples


```csharp
using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
{
   using (var archive = new SevenZipArchive(new SevenZipEntrySettings(new SevenZipLZMACompressionSettings())))
   {
      archive.CreateEntry("data", source);
      archive.Save("archive.7z");
   }
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

The specified <code class="paramref">destinationFileName</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">destinationFileName</code> contains a colon (:) in the middle of the string.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_SevenZip_SevenZipArchive_SaveSplit_System_String_Aspose_Zip_Saving_SplitSevenZipArchiveSaveOptions_"></a> SaveSplit\(string, SplitSevenZipArchiveSaveOptions\)

Saves multi-volume archive to destination directory provided.

```csharp
public void SaveSplit(string destinationDirectory, SplitSevenZipArchiveSaveOptions options)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory where archive segments to be created.

`options` [SplitSevenZipArchiveSaveOptions](/zip/aspose.zip.saving.splitsevenziparchivesaveoptions)

Options for archive saving, including file name.

#### Examples


```csharp
using (SevenZipArchive archive = new SevenZipArchive())
{
    archive.CreateEntry("entry.bin", "data.bin");
    archive.SaveSplit(@"C:\Folder",  new SplitSevenZipArchiveSaveOptions("volume", 65536));
}
```

#### Remarks

<p>This method composes several (<code>n</code>) files filename.7z.001, filename.7z.002, ..., filename.7z.(n).</p>
<p>Cannot make existing archive multi-volume.</p>

#### Exceptions

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

This archive was opened from the existing source.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">destinationDirectory</code> is null.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access the directory.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destinationDirectory</code> contains invalid characters such as ", &gt;, &lt;, or |.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified path exceeds the system-defined maximum length.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.
