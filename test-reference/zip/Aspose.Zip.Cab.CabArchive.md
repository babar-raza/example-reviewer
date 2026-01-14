---
linkTitle: "Class CabArchive"
title: "Class CabArchive"
description: "This class represents a CAB archive file."
summary: "This class represents a CAB archive file."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Cab](/zip/aspose.zip.cab)  
Assembly: Aspose.Zip.dll (25.12.0)  

This class represents a CAB archive file.

```csharp
public class CabArchive : IArchive, IDisposable
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[CabArchive](/zip/aspose.zip.cab.cabarchive)

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

### <a id="Aspose_Zip_Cab_CabArchive__ctor_Aspose_Zip_Cab_CabEntrySettings_"></a> CabArchive\(CabEntrySettings\)

Initializes a new instance of the Aspose.Zip.Cab.CabArchive class prepared for compressing.

```csharp
public CabArchive(CabEntrySettings settings = null)
```

#### Parameters

`settings` [CabEntrySettings](/zip/aspose.zip.cab.cabentrysettings)

#### Examples

<p>The following example shows how to compress a file.</p>

```csharp
using (var archive = new CabArchive())
{
    archive.CreateEntry("first.bin", "data.bin");
    archive.Save("archive.cab");
}
```

<p>Compress a file using specific compression settings.</p>

```csharp
using (var archive = new CabArchive())
{
    var settings = new CabEntrySettings(new CabStoreCompressionSettings());
    archive.CreateEntry("entry.bin", "data.bin", settings);
    archive.Save("archive.cab");
}
```

### <a id="Aspose_Zip_Cab_CabArchive__ctor_System_IO_Stream_Aspose_Zip_Cab_CabLoadOptions_"></a> CabArchive\(Stream, CabLoadOptions\)

Initializes a new instance of the Aspose.Zip.Cab.CabArchive class and composes an entry list can be extracted from the archive.

```csharp
public CabArchive(Stream sourceStream, CabLoadOptions loadOptions = null)
```

#### Parameters

`sourceStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive. It must be seekable.

`loadOptions` [CabLoadOptions](/zip/aspose.zip.cab.cabloadoptions)

Options to load existing archive with.

#### Examples

<p>The following example shows how to extract all the entries to a directory.</p>

```csharp
using (var archive = new CabArchive(File.OpenRead("archive.cab")))
{ 
   archive.ExtractToDirectory("C:\\extracted");
}
```

#### Remarks

This constructor does not unpack any entry. See Aspose.Zip.Cab.CabEntry.Open method for unpacking.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">sourceStream</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">sourceStream</code> is not seekable.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

<code class="paramref">sourceStream</code> is not valid CAB archive.

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

The stream is too short.

### <a id="Aspose_Zip_Cab_CabArchive__ctor_System_String_Aspose_Zip_Cab_CabLoadOptions_"></a> CabArchive\(string, CabLoadOptions\)

Initializes a new instance of the Aspose.Zip.Cab.CabArchive class and composes an entry list can be extracted from the archive.

```csharp
public CabArchive(string path, CabLoadOptions loadOptions = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

`loadOptions` [CabLoadOptions](/zip/aspose.zip.cab.cabloadoptions)

Options to load existing archive with.

#### Examples

<p>The following example shows how to extract all the entries to a directory.</p>

```csharp
using (var archive = new CabArchive("archive.cab")) hj
{ 
   archive.ExtractToDirectory("C:\\extracted");
}
```

#### Remarks

This constructor does not unpack any entry. See Aspose.Zip.Cab.CabEntry.Open method for unpacking.

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

 [FileNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.filenotfoundexception)

The file is not found.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified path is invalid, such as being on an unmapped drive.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The file is already open.

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

The file is too short.

## Properties

### <a id="Aspose_Zip_Cab_CabArchive_Entries"></a> Entries

Gets entries of Aspose.Zip.Cab.CabEntry type constituting the archive.

```csharp
public ReadOnlyCollection<CabEntry> Entries { get; }
```

#### Property Value

 [ReadOnlyCollection](https://learn.microsoft.com/dotnet/api/system.collections.objectmodel.readonlycollection\-1)<[CabEntry](/zip/aspose.zip.cab.cabentry)\>

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

## Methods

### <a id="Aspose_Zip_Cab_CabArchive_CreateEntries_System_IO_DirectoryInfo_System_Boolean_"></a> CreateEntries\(DirectoryInfo, bool\)

Adds to the archive all files, recursively, from the specified directory.

```csharp
public CabArchive CreateEntries(DirectoryInfo directory, bool includeRootDirectory = true)
```

#### Parameters

`directory` [DirectoryInfo](https://learn.microsoft.com/dotnet/api/system.io.directoryinfo)

Directory to compress.

`includeRootDirectory` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Indicates whether to include the root directory name in entry paths.

#### Returns

 [CabArchive](/zip/aspose.zip.cab.cabarchive)

The current Aspose.Zip.Cab.CabArchive instance.

#### Examples


```csharp
using (var archive = new CabArchive())
{
    var directory = new DirectoryInfo("logs");
    archive.CreateEntries(directory);
    archive.Save("logs.cab");
}
```

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">directory</code> is null.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

<code class="paramref">directory</code> cannot be found.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access <code class="paramref">directory</code> or its content.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to <code class="paramref">directory</code> or one of its files is denied.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

An I/O error occurs while accessing <code class="paramref">directory</code>.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

A generated entry path exceeds the system-defined maximum length.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is prepared for extraction and cannot add entries.

### <a id="Aspose_Zip_Cab_CabArchive_CreateEntries_System_String_System_Boolean_"></a> CreateEntries\(string, bool\)

Adds to the archive all files recursively from the specified directory path.

```csharp
public CabArchive CreateEntries(string sourceDirectory, bool includeRootDirectory = true)
```

#### Parameters

`sourceDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

Directory path to compress.

`includeRootDirectory` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Indicates whether to include the root directory name in entry paths.

#### Returns

 [CabArchive](/zip/aspose.zip.cab.cabarchive)

The current Aspose.Zip.Cab.CabArchive instance.

#### Examples


```csharp
using (var archive = new CabArchive(new CabEntrySettings(new CabStoreCompressionSettings())))
{
    archive.CreateEntries("data", includeRootDirectory: false);
    archive.Save("stored_data.cab");
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">sourceDirectory</code> is null.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

<code class="paramref">sourceDirectory</code> cannot be found.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access <code class="paramref">sourceDirectory</code>.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to <code class="paramref">sourceDirectory</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">sourceDirectory</code> exceeds the system-defined maximum length.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">sourceDirectory</code> is empty, contains only white spaces, or contains invalid characters.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

An I/O error occurs while accessing <code class="paramref">sourceDirectory</code>.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is prepared for extraction and cannot add entries.

### <a id="Aspose_Zip_Cab_CabArchive_CreateEntry_System_String_System_String_Aspose_Zip_Cab_CabEntrySettings_"></a> CreateEntry\(string, string, CabEntrySettings\)

Create a single entry within the archive.

```csharp
public CabEntry CreateEntry(string name, string path, CabEntrySettings newEntrySettings = null)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The fully qualified name of the new file, or the relative file name to be compressed.

`newEntrySettings` [CabEntrySettings](/zip/aspose.zip.cab.cabentrysettings)

Compression and encryption settings used for added Aspose.Zip.Cab.CabEntry item.

#### Returns

 [CabEntry](/zip/aspose.zip.cab.cabentry)

Cab entry instance.

#### Examples


```csharp
using (var archive = new CabArchive())
{
    archive.CreateEntry("entry.bin", "data.bin");
    archive.Save("archive.cab");
}
```

#### Remarks

<p>The entry name is solely set within <code class="paramref">name</code> parameter. The file name provided in <code class="paramref">path</code> parameter does not affect the entry name.</p>

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

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is prepared for extraction and cannot add entries.

### <a id="Aspose_Zip_Cab_CabArchive_CreateEntry_System_String_System_IO_Stream_Aspose_Zip_Cab_CabEntrySettings_"></a> CreateEntry\(string, Stream, CabEntrySettings\)

Create a single entry within the archive.

```csharp
public CabEntry CreateEntry(string name, Stream source, CabEntrySettings newEntrySettings = null)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The input stream for the entry.

`newEntrySettings` [CabEntrySettings](/zip/aspose.zip.cab.cabentrysettings)

Compression and encryption settings used for added Aspose.Zip.Cab.CabEntry item.

#### Returns

 [CabEntry](/zip/aspose.zip.cab.cabentry)

Cab entry instance.

#### Examples


```csharp
using (var archive = new CabArchive())
{
    using (var dataStream = new MemoryStream(File.ReadAllBytes("data.bin")))
    {
        archive.CreateEntry("stream-entry.bin", dataStream);
        archive.Save("archive.cab");
    }
}
```


```csharp
using (var archive = new CabArchive())
{     
    var settings = new CabEntrySettings(new CabStoreCompressionSettings());
    archive.CreateEntry("stream-entry.bin", dataStream, settings);
    archive.Save("archive.cab");     
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is prepared for extraction and cannot add entries.

### <a id="Aspose_Zip_Cab_CabArchive_CreateEntry_System_String_System_IO_FileInfo_Aspose_Zip_Cab_CabEntrySettings_"></a> CreateEntry\(string, FileInfo, CabEntrySettings\)

Create a single entry within the archive.

```csharp
public CabEntry CreateEntry(string name, FileInfo fileInfo, CabEntrySettings newEntrySettings = null)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`fileInfo` [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

The metadata of file to be compressed.

`newEntrySettings` [CabEntrySettings](/zip/aspose.zip.cab.cabentrysettings)

Compression and encryption settings used for added Aspose.Zip.Cab.CabEntry item.

#### Returns

 [CabEntry](/zip/aspose.zip.cab.cabentry)

Cab entry instance.

#### Examples


```csharp
using (var archive = new CabArchive(new CabEntrySettings(new CabMsZipCompressionSettings())))
{
    var sourceFile = new FileInfo("logs\\log.txt");
    archive.CreateEntry("log.txt", sourceFile);
    archive.Save("archive.cab");
}
```

#### Remarks

<p>The entry name is solely set within <code class="paramref">name</code> parameter. The file name provided in <code class="paramref">fileInfo</code> parameter does not affect the entry name.</p>

#### Exceptions

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

<code class="paramref">fileInfo</code> is read-only or is a directory.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified path is invalid, such as being on an unmapped drive.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The file is already open.

 [FileNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.filenotfoundexception)

<code class="paramref">fileInfo</code> represents a file that cannot be found.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access <code class="paramref">fileInfo</code>.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is prepared for extraction and cannot add entries.

### <a id="Aspose_Zip_Cab_CabArchive_Dispose_System_Boolean_"></a> Dispose\(bool\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
protected virtual void Dispose(bool disposing)
```

#### Parameters

`disposing` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether managed resources should be disposed.

### <a id="Aspose_Zip_Cab_CabArchive_Dispose"></a> Dispose\(\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_Cab_CabArchive_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

Extracts all the files in the archive to the directory provided.

```csharp
public void ExtractToDirectory(string destinationDirectory)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory to place the extracted files in.

#### Examples


```csharp
using (var archive = new CabArchive("archive.cab")) 
{ 
   archive.ExtractToDirectory("C:\\extracted");
}
```

#### Remarks

If the directory does not exist, it will be created.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

path is null

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified path, file name, or both exceed the system-defined maximum length.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access the existing directory.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

If the directory does not exist, a path contains a colon character (:) that is not part of a drive label ("C:\").

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

path is a zero-length string, contains only white space, or contains one or more invalid characters. You can query for invalid characters by using the System.IO.Path.GetInvalidPathChars method. -or- path is prefixed with, or contains, only a colon character (:).

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The directory specified by path is a file. -or- The network name is not known.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The archive is corrupted.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is prepared for composition and cannot be extracted.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

### <a id="Aspose_Zip_Cab_CabArchive_Save_System_IO_Stream_Aspose_Zip_Cab_CabSaveOptions_"></a> Save\(Stream, CabSaveOptions\)

Saves archive to the stream provided.

```csharp
public void Save(Stream outputStream, CabSaveOptions saveOptions = null)
```

#### Parameters

`outputStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`saveOptions` [CabSaveOptions](/zip/aspose.zip.cab.cabsaveoptions)

Options for archive saving.

#### Examples


```csharp
using (FileStream cabFile = File.Open("archive.cab", FileMode.Create))
{
    using (var archive = new CabArchive())
    {
        archive.CreateEntry("entry.bin", "data.bin");
        archive.Save(cabFile);
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

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is prepared for extraction and cannot be saved.

### <a id="Aspose_Zip_Cab_CabArchive_Save_System_String_Aspose_Zip_Cab_CabSaveOptions_"></a> Save\(string, CabSaveOptions\)

Saves archive to the destination file provided.

```csharp
public void Save(string destinationFileName, CabSaveOptions saveOptions = null)
```

#### Parameters

`destinationFileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`saveOptions` [CabSaveOptions](/zip/aspose.zip.cab.cabsaveoptions)

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

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is opened for extraction.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

The specified path is invalid, such as being on an unmapped drive.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The file is already open.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.
