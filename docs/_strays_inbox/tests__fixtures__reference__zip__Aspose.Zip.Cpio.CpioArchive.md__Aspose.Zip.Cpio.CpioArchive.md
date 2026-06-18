---
linkTitle: "Class CpioArchive"
title: "Class CpioArchive"
description: "This class represents cpio archive file."
summary: "This class represents cpio archive file."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Cpio](/zip/aspose.zip.cpio)  
Assembly: Aspose.Zip.dll (25.12.0)  

This class represents cpio archive file.

```csharp
public class CpioArchive : IArchive, IDisposable
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[CpioArchive](/zip/aspose.zip.cpio.cpioarchive)

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

### <a id="Aspose_Zip_Cpio_CpioArchive__ctor"></a> CpioArchive\(\)

Initializes a new instance of the Aspose.Zip.Cpio.CpioArchive class.

```csharp
public CpioArchive()
```

#### Examples

<p>The following example shows how to compress a file.</p>

```csharp
using (var archive = new CpioArchive())
{
    archive.CreateEntry("first.bin", "data.bin");
    archive.Save("archive.cpio");
}
```

### <a id="Aspose_Zip_Cpio_CpioArchive__ctor_System_IO_Stream_"></a> CpioArchive\(Stream\)

Initializes a new instance of the Aspose.Zip.Cpio.CpioArchive class and composes an entry list can be extracted from the archive.

```csharp
public CpioArchive(Stream sourceStream)
```

#### Parameters

`sourceStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive. It must be seekable.

#### Examples

<p>The following example shows how to extract all the entries to a directory.</p>

```csharp
using (var archive = new CpioArchive(File.OpenRead("archive.cpio")))
{ 
   archive.ExtractToDirectory("C:\extracted");
}
```

#### Remarks

This constructor does not unpack any entry. See Aspose.Zip.Cpio.CpioEntry.Open method for unpacking.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">sourceStream</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">sourceStream</code> is not seekable.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

<code class="paramref">sourceStream</code> is not valid cpio archive.

### <a id="Aspose_Zip_Cpio_CpioArchive__ctor_System_String_"></a> CpioArchive\(string\)

Initializes a new instance of the Aspose.Zip.Cpio.CpioArchive class and composes an entry list can be extracted from the archive.

```csharp
public CpioArchive(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

#### Examples

<p>The following example shows how to extract all the entries to a directory.</p>

```csharp
using (var archive = new CpioArchive("archive.cpio")) 
{ 
   archive.ExtractToDirectory("C:\extracted");
}
```

#### Remarks

This constructor does not unpack any entry. See Aspose.Zip.Cpio.CpioEntry.Open method for unpacking.

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

### <a id="Aspose_Zip_Cpio_CpioArchive_Entries"></a> Entries

Gets entries of Aspose.Zip.Cpio.CpioEntry type constituting the archive.

```csharp
public ReadOnlyCollection<CpioEntry> Entries { get; }
```

#### Property Value

 [ReadOnlyCollection](https://learn.microsoft.com/dotnet/api/system.collections.objectmodel.readonlycollection\-1)<[CpioEntry](/zip/aspose.zip.cpio.cpioentry)\>

## Methods

### <a id="Aspose_Zip_Cpio_CpioArchive_CreateEntries_System_String_System_Boolean_"></a> CreateEntries\(string, bool\)

Adds to the archive all the files and directories recursively in the directory given.

```csharp
public CpioArchive CreateEntries(string sourceDirectory, bool includeRootDirectory = true)
```

#### Parameters

`sourceDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

Directory to compress.

`includeRootDirectory` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Indicates whether to include the root directory itself or not.

#### Returns

 [CpioArchive](/zip/aspose.zip.cpio.cpioarchive)

Cpio entry instance.

#### Examples


```csharp
using (FileStream cpioFile = File.Open("archive.cpio", FileMode.Create))
{
    using (var archive = new CpioArchive())
    {
        archive.CreateEntries("C:\folder", false);
        archive.Save(cpioFile);
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

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

<code class="paramref">sourceDirectory</code> stands for a file, not for a directory.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_CreateEntries_System_IO_DirectoryInfo_System_Boolean_"></a> CreateEntries\(DirectoryInfo, bool\)

Adds to the archive all the files and directories recursively in the directory given.

```csharp
public CpioArchive CreateEntries(DirectoryInfo directory, bool includeRootDirectory = true)
```

#### Parameters

`directory` [DirectoryInfo](https://learn.microsoft.com/dotnet/api/system.io.directoryinfo)

Directory to compress.

`includeRootDirectory` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Indicates whether to include the root directory itself or not.

#### Returns

 [CpioArchive](/zip/aspose.zip.cpio.cpioarchive)

Cpio entry instance.

#### Examples


```csharp
using (FileStream cpioFile = File.Open("archive.cpio", FileMode.Create))
{
    using (var archive = new CpioArchive())
    {
        archive.CreateEntries(new DirectoryInfo("C:\folder"), false);
        archive.Save(cpioFile);
    }
}
```

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">directory</code> is null.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access <code class="paramref">directory</code>.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

<code class="paramref">directory</code> stands for a file, not for a directory.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_CreateEntry_System_String_System_IO_FileInfo_System_Boolean_"></a> CreateEntry\(string, FileInfo, bool\)

Create a single entry within the archive.

```csharp
public CpioEntry CreateEntry(string name, FileInfo fileInfo, bool openImmediately = false)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`fileInfo` [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

The metadata of file or folder to be compressed.

`openImmediately` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

True, if open the file immediately, otherwise open the file on archive saving.

#### Returns

 [CpioEntry](/zip/aspose.zip.cpio.cpioentry)

Cpio entry instance.

#### Examples


```csharp
FileInfo fileInfo = new FileInfo("data.bin");
using (var archive = new CpioArchive())
{
    archive.CreateEntry("test.bin", fileInfo);
    archive.Save("archive.cpio");
}
```

#### Remarks

<p>If the file is opened immediately with <code class="paramref">openImmediately</code> parameter it becomes blocked until archive is disposed.</p>

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">name</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">name</code> is empty.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">fileInfo</code> is null.

### <a id="Aspose_Zip_Cpio_CpioArchive_CreateEntry_System_String_System_String_System_Boolean_"></a> CreateEntry\(string, string, bool\)

Create a single entry within the archive.

```csharp
public CpioEntry CreateEntry(string name, string sourcePath, bool openImmediately = false)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`sourcePath` [string](https://learn.microsoft.com/dotnet/api/system.string)

Path to file to be compressed.

`openImmediately` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

True, if open the file immediately, otherwise open the file on archive saving.

#### Returns

 [CpioEntry](/zip/aspose.zip.cpio.cpioentry)

Cpio entry instance.

#### Examples


```csharp
using (var archive = new CpioArchive())
{
    archive.CreateEntry("first.bin", "data.bin");
    archive.Save("archive.cpio");
}
```

#### Remarks

<p>The entry name is solely set within <code class="paramref">name</code> parameter. The file name provided in <code class="paramref">sourcePath</code> parameter does not affect the entry name.</p>
<p>If the file is opened immediately with <code class="paramref">openImmediately</code> parameter it becomes blocked until archive is disposed.</p>

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">sourcePath</code> is null.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">sourcePath</code> is empty, contains only white spaces, or contains invalid characters. - or - File name, as a part of <code class="paramref">name</code>, exceeds 100 symbols.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">sourcePath</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">sourcePath</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters. - or - <code class="paramref">name</code> is too long for cpio.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">sourcePath</code> contains a colon (:) in the middle of the string.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_CreateEntry_System_String_System_IO_Stream_"></a> CreateEntry\(string, Stream\)

Create a single entry within the archive.

```csharp
public CpioEntry CreateEntry(string name, Stream source)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The input stream for the entry.

#### Returns

 [CpioEntry](/zip/aspose.zip.cpio.cpioentry)

Cpio entry instance.

#### Examples


```csharp
using (var archive = new CpioArchive())
{
    archive.CreateEntry("data.bin", File.OpenRead("data.bin"));
    archive.Save("archive.cpio");
}
```

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">name</code> is null.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">source</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">name</code> is empty.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_DeleteEntry_Aspose_Zip_Cpio_CpioEntry_"></a> DeleteEntry\(CpioEntry\)

Removes the first occurrence of a specific entry from the entry list.

```csharp
public CpioArchive DeleteEntry(CpioEntry entry)
```

#### Parameters

`entry` [CpioEntry](/zip/aspose.zip.cpio.cpioentry)

The entry to remove from the entries list.

#### Returns

 [CpioArchive](/zip/aspose.zip.cpio.cpioarchive)

Cpio entry instance.

#### Examples

<p>Here is how you can remove all entries except the last one:</p>

```csharp
using (var archive = new CpioArchive("archive.cpio"))
{
    while (archive.Entries.Count &gt; 1)
        archive.DeleteEntry(archive.Entries[0]);
    archive.Save(outputCpioFile);
}
```

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">entry</code> is null.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_DeleteEntry_System_Int32_"></a> DeleteEntry\(int\)

Removes the entry from the entry list by index.

```csharp
public CpioArchive DeleteEntry(int entryIndex)
```

#### Parameters

`entryIndex` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The zero-based index of the entry to remove.

#### Returns

 [CpioArchive](/zip/aspose.zip.cpio.cpioarchive)

The archive with the entry deleted.

#### Examples


```csharp
using (var archive = new CpioArchive("two_files.cpio"))
{
    archive.DeleteEntry(0);
    archive.Save("single_file.cpio");
}
```

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

<code class="paramref">entryIndex</code> is less than 0.-or- <code class="paramref">entryIndex</code> is equal to or greater than <code>Entries</code> count.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_Dispose"></a> Dispose\(\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_Cpio_CpioArchive_Dispose_System_Boolean_"></a> Dispose\(bool\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
protected virtual void Dispose(bool disposing)
```

#### Parameters

`disposing` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether managed resources should be disposed.

### <a id="Aspose_Zip_Cpio_CpioArchive_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

Extracts all the files in the archive to the directory provided.

```csharp
public void ExtractToDirectory(string destinationDirectory)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory to place the extracted files in.

#### Examples


```csharp
using (var archive = new CpioArchive("archive.cpio")) 
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

If the directory does not exist, a path contains a colon character (:) that is not part of a drive label ("C:\").

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

Path is a zero-length string, contains only white space, or contains one or more invalid characters. You can query for invalid characters by using the System.IO.Path.GetInvalidPathChars method. -or- path is prefixed with, or contains, only a colon character (:).

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The directory specified by path is a file. -or- The network name is not known.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_Save_System_String_Aspose_Zip_Cpio_CpioFormat_"></a> Save\(string, CpioFormat\)

Saves archive to a destination file provided.

```csharp
public void Save(string destinationFileName, CpioFormat cpioFormat = CpioFormat.OldAscii)
```

#### Parameters

`destinationFileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`cpioFormat` [CpioFormat](/zip/aspose.zip.cpio.cpioformat)

Defines cpio header format.

#### Examples


```csharp
using (var archive = new CpioArchive())
{
    archive.CreateEntry("entry1", "data.bin");        
    archive.Save("archive.cpio");
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

<code class="paramref">destinationFileName</code>Specified a file is read-only and access is not Read.-or- path specified a directory.-or- The caller does not have the required permission.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

<code class="paramref">destinationFileName</code> is in an invalid format.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_Save_System_IO_Stream_Aspose_Zip_Cpio_CpioFormat_"></a> Save\(Stream, CpioFormat\)

Saves archive to the stream provided.

```csharp
public void Save(Stream output, CpioFormat cpioFormat = CpioFormat.OldAscii)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`cpioFormat` [CpioFormat](/zip/aspose.zip.cpio.cpioformat)

Defines cpio header format.

#### Examples


```csharp
using (FileStream cpioFile = File.Open("archive.cpio", FileMode.Create))
{
    using (var archive = new CpioArchive())
    {
        archive.CreateEntry("entry1", "data.bin");        
        archive.Save(cpioFile);
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

<code class="paramref">output</code> is not writable. - or - <code class="paramref">output</code> is the same stream we extract from.
        - OR -
        It is impossible to save archive in <code class="paramref">cpioFormat</code> due to format restrictions.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_SaveGzipped_System_IO_Stream_Aspose_Zip_Cpio_CpioFormat_"></a> SaveGzipped\(Stream, CpioFormat\)

Saves archive to the stream with gzip compression.

```csharp
public void SaveGzipped(Stream output, CpioFormat cpioFormat = CpioFormat.OldAscii)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`cpioFormat` [CpioFormat](/zip/aspose.zip.cpio.cpioformat)

Defines cpio header format.

#### Examples


```csharp
using (FileStream result = File.OpenWrite("result.cpio.gz"))
{
    using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
    {
        using (var archive = new CpioArchive())
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

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_SaveGzipped_System_String_Aspose_Zip_Cpio_CpioFormat_"></a> SaveGzipped\(string, CpioFormat\)

Saves archive to the file by path with gzip compression.

```csharp
public void SaveGzipped(string path, CpioFormat cpioFormat = CpioFormat.OldAscii)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`cpioFormat` [CpioFormat](/zip/aspose.zip.cpio.cpioformat)

Defines cpio header format.

#### Examples


```csharp
using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
{
    using (var archive = new CpioArchive())
    {
        archive.CreateEntry("entry.bin", source);
        archive.SaveGzipped("result.cpio.gz");
    }
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_SaveLZMACompressed_System_IO_Stream_Aspose_Zip_Cpio_CpioFormat_"></a> SaveLZMACompressed\(Stream, CpioFormat\)

Saves the archive to the stream with LZMA compression.

```csharp
public void SaveLZMACompressed(Stream output, CpioFormat cpioFormat = CpioFormat.OldAscii)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`cpioFormat` [CpioFormat](/zip/aspose.zip.cpio.cpioformat)

Defines cpio header format.

#### Examples


```csharp
using (FileStream result = File.OpenWrite("result.cpio.lzma"))
{
    using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
    {
        using (var archive = new CpioArchive())
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
        Important: cpio archive is composed then compressed within this method, its content is kept internally. Beware of memory consumption.

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_SaveLZMACompressed_System_String_Aspose_Zip_Cpio_CpioFormat_"></a> SaveLZMACompressed\(string, CpioFormat\)

Saves the archive to the file by path with lzma compression.

```csharp
public void SaveLZMACompressed(string path, CpioFormat cpioFormat = CpioFormat.OldAscii)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`cpioFormat` [CpioFormat](/zip/aspose.zip.cpio.cpioformat)

Defines cpio header format.

#### Examples


```csharp
using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
{
    using (var archive = new CpioArchive())
    {
        archive.CreateEntry("entry.bin", source);
        archive.SaveLZMACompressed("result.cpio.lzma");
    }
}
```

#### Remarks

Important: cpio archive is composed then compressed within this method, its content is kept internally. Beware of memory consumption.

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_SaveLzipped_System_IO_Stream_Aspose_Zip_Cpio_CpioFormat_"></a> SaveLzipped\(Stream, CpioFormat\)

Saves archive to the stream with lzip compression.

```csharp
public void SaveLzipped(Stream output, CpioFormat cpioFormat = CpioFormat.OldAscii)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`cpioFormat` [CpioFormat](/zip/aspose.zip.cpio.cpioformat)

Defines cpio header format.

#### Examples


```csharp
using (FileStream result = File.OpenWrite("result.cpio.lz"))
{
    using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
    {
        using (var archive = new CpioArchive())
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

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_SaveLzipped_System_String_Aspose_Zip_Cpio_CpioFormat_"></a> SaveLzipped\(string, CpioFormat\)

Saves archive to the file by path with lzip compression.

```csharp
public void SaveLzipped(string path, CpioFormat cpioFormat = CpioFormat.OldAscii)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`cpioFormat` [CpioFormat](/zip/aspose.zip.cpio.cpioformat)

Defines cpio header format.

#### Examples


```csharp
using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
{
    using (var archive = new CpioArchive())
    {
        archive.CreateEntry("entry.bin", source);
        archive.SaveGzipped("result.cpio.lz");
    }
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_SaveXzCompressed_System_IO_Stream_Aspose_Zip_Cpio_CpioFormat_Aspose_Zip_Xz_Settings_XzArchiveSettings_"></a> SaveXzCompressed\(Stream, CpioFormat, XzArchiveSettings\)

Saves archive to the stream with xz compression.

```csharp
public void SaveXzCompressed(Stream output, CpioFormat cpioFormat = CpioFormat.OldAscii, XzArchiveSettings settings = null)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`cpioFormat` [CpioFormat](/zip/aspose.zip.cpio.cpioformat)

Defines cpio header format.

`settings` [XzArchiveSettings](/zip/aspose.zip.xz.settings.xzarchivesettings)

Set of setting particular xz archive: dictionary size, block size, check type.

#### Examples


```csharp
using (FileStream result = File.OpenWrite("result.cpio.xz"))
{
    using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
    {
        using (var archive = new CpioArchive())
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

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_SaveXzCompressed_System_String_Aspose_Zip_Cpio_CpioFormat_Aspose_Zip_Xz_Settings_XzArchiveSettings_"></a> SaveXzCompressed\(string, CpioFormat, XzArchiveSettings\)

Saves archive to the path by path with xz compression.

```csharp
public void SaveXzCompressed(string path, CpioFormat cpioFormat = CpioFormat.OldAscii, XzArchiveSettings settings = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`cpioFormat` [CpioFormat](/zip/aspose.zip.cpio.cpioformat)

Defines cpio header format.

`settings` [XzArchiveSettings](/zip/aspose.zip.xz.settings.xzarchivesettings)

Set of setting particular xz archive: dictionary size, block size, check type.

#### Examples


```csharp
using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
{
    using (var archive = new CpioArchive())
    {
        archive.CreateEntry("entry.bin", source);
        archive.SaveXzCompressed("result.cpio.xz");
    }
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_SaveZCompressed_System_IO_Stream_Aspose_Zip_Cpio_CpioFormat_"></a> SaveZCompressed\(Stream, CpioFormat\)

Saves archive to the stream with Z compression.

```csharp
public void SaveZCompressed(Stream output, CpioFormat cpioFormat = CpioFormat.OldAscii)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`cpioFormat` [CpioFormat](/zip/aspose.zip.cpio.cpioformat)

Defines cpio header format.

#### Examples


```csharp
using (FileStream result = File.OpenWrite("result.cpio.Z"))
{
    using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
    {
        using (var archive = new CpioArchive())
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

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_SaveZCompressed_System_String_Aspose_Zip_Cpio_CpioFormat_"></a> SaveZCompressed\(string, CpioFormat\)

Saves archive to the path by path with Z compression.

```csharp
public void SaveZCompressed(string path, CpioFormat cpioFormat = CpioFormat.OldAscii)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`cpioFormat` [CpioFormat](/zip/aspose.zip.cpio.cpioformat)

Defines cpio header format.

#### Examples


```csharp
using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
{
    using (var archive = new CpioArchive())
    {
        archive.CreateEntry("entry.bin", source);
        archive.SaveZCompressed("result.cpio.Z");
    }
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_SaveZstandard_System_IO_Stream_Aspose_Zip_Cpio_CpioFormat_"></a> SaveZstandard\(Stream, CpioFormat\)

Saves archive to the stream with Zstandard compression.

```csharp
public void SaveZstandard(Stream output, CpioFormat cpioFormat = CpioFormat.OldAscii)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`cpioFormat` [CpioFormat](/zip/aspose.zip.cpio.cpioformat)

Defines cpio header format.

#### Examples


```csharp
using (FileStream result = File.OpenWrite("result.cpio.zst"))
{
    using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
    {
        using (var archive = new CpioArchive())
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

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Cpio_CpioArchive_SaveZstandard_System_String_Aspose_Zip_Cpio_CpioFormat_"></a> SaveZstandard\(string, CpioFormat\)

Saves archive to the file by path with Zstandard compression.

```csharp
public void SaveZstandard(string path, CpioFormat cpioFormat = CpioFormat.OldAscii)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`cpioFormat` [CpioFormat](/zip/aspose.zip.cpio.cpioformat)

Defines cpio header format.

#### Examples


```csharp
using (FileStream source = File.Open("data.bin", FileMode.Open, FileAccess.Read))
{
    using (var archive = new CpioArchive())
    {
        archive.CreateEntry("entry.bin", source);
        archive.SaveZstandard("result.cpio.zst");
    }
}
```

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.
