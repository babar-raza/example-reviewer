---
linkTitle: "Class SharArchive"
title: "Class SharArchive"
description: "This class represents a shar archive file."
summary: "This class represents a shar archive file."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Shar](/zip/aspose.zip.shar)  
Assembly: Aspose.Zip.dll (25.12.0)  

This class represents a shar archive file.

```csharp
public class SharArchive : IDisposable
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[SharArchive](/zip/aspose.zip.shar.shararchive)

#### Implements

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

### <a id="Aspose_Zip_Shar_SharArchive__ctor"></a> SharArchive\(\)

Initializes a new instance of the Aspose.Zip.Shar.SharArchive class.

```csharp
public SharArchive()
```

#### Examples

<p>The following example shows how to compress a file.</p>

```csharp
using (var archive = new SharArchive())
{
    archive.CreateEntry("first.bin", "data.bin");
    archive.Save("archive.shar");
}
```

### <a id="Aspose_Zip_Shar_SharArchive__ctor_System_String_"></a> SharArchive\(string\)

Initializes a new instance of the Aspose.Zip.Shar.SharArchive class prepared for decompressing.

```csharp
public SharArchive(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

Path to the source of the archive.

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

### <a id="Aspose_Zip_Shar_SharArchive_Entries"></a> Entries

Gets entries of Aspose.Zip.Shar.SharEntry type constituting the archive.

```csharp
public ReadOnlyCollection<SharEntry> Entries { get; }
```

#### Property Value

 [ReadOnlyCollection](https://learn.microsoft.com/dotnet/api/system.collections.objectmodel.readonlycollection\-1)<[SharEntry](/zip/aspose.zip.shar.sharentry)\>

## Methods

### <a id="Aspose_Zip_Shar_SharArchive_CreateEntries_System_String_System_Boolean_"></a> CreateEntries\(string, bool\)

Adds to the archive all the files and directories recursively in the directory given.

```csharp
public SharArchive CreateEntries(string sourceDirectory, bool includeRootDirectory = true)
```

#### Parameters

`sourceDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

Directory to compress.

`includeRootDirectory` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Indicates whether to include the root directory itself or not.

#### Returns

 [SharArchive](/zip/aspose.zip.shar.shararchive)

Shar entry instance.

#### Examples


```csharp
using (FileStream sharFile = File.Open("archive.shar", FileMode.Create))
{
    using (var archive = new SharArchive())
    {
        archive.CreateEntries("C:\folder", false);
        archive.Save(sharFile);
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

### <a id="Aspose_Zip_Shar_SharArchive_CreateEntries_System_IO_DirectoryInfo_System_Boolean_"></a> CreateEntries\(DirectoryInfo, bool\)

Adds to the archive all the files and directories recursively in the directory given.

```csharp
public SharArchive CreateEntries(DirectoryInfo directory, bool includeRootDirectory = true)
```

#### Parameters

`directory` [DirectoryInfo](https://learn.microsoft.com/dotnet/api/system.io.directoryinfo)

Directory to compress.

`includeRootDirectory` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Indicates whether to include the root directory itself or not.

#### Returns

 [SharArchive](/zip/aspose.zip.shar.shararchive)

Shar entry instance.

#### Examples


```csharp
using (FileStream sharFile = File.Open("archive.shar", FileMode.Create))
{
    using (var archive = new SharArchive())
    {
        archive.CreateEntries(new DirectoryInfo("C:\folder"), false);
        archive.Save(sharFile);
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

### <a id="Aspose_Zip_Shar_SharArchive_CreateEntry_System_String_System_IO_FileInfo_System_Boolean_"></a> CreateEntry\(string, FileInfo, bool\)

Create a single entry within the archive.

```csharp
public SharEntry CreateEntry(string name, FileInfo fileInfo, bool openImmediately = false)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`fileInfo` [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

The metadata of file or folder to be compressed.

`openImmediately` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

True, if open the file immediately, otherwise open the file on archive saving.

#### Returns

 [SharEntry](/zip/aspose.zip.shar.sharentry)

Shar entry instance.

#### Examples


```csharp
FileInfo fileInfo = new FileInfo("data.bin");
using (var archive = new SharArchive())
{
    archive.CreateEntry("test.bin", fileInfo);
    archive.Save("archive.shar");
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

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Shar_SharArchive_CreateEntry_System_String_System_String_System_Boolean_"></a> CreateEntry\(string, string, bool\)

Create a single entry within the archive.

```csharp
public SharEntry CreateEntry(string name, string sourcePath, bool openImmediately = false)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`sourcePath` [string](https://learn.microsoft.com/dotnet/api/system.string)

Path to file to be compressed.

`openImmediately` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

True, if open the file immediately, otherwise open the file on archive saving.

#### Returns

 [SharEntry](/zip/aspose.zip.shar.sharentry)

Shar entry instance.

#### Examples


```csharp
using (var archive = new SharArchive())
{
    archive.CreateEntry("first.bin", "data.bin");
    archive.Save("archive.shar");
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

The specified <code class="paramref">sourcePath</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters. - or - <code class="paramref">name</code> is too long for shar.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">sourcePath</code> contains a colon (:) in the middle of the string.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Shar_SharArchive_CreateEntry_System_String_System_IO_Stream_"></a> CreateEntry\(string, Stream\)

Create a single entry within the archive.

```csharp
public SharEntry CreateEntry(string name, Stream source)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The input stream for the entry.

#### Returns

 [SharEntry](/zip/aspose.zip.shar.sharentry)

Shar entry instance.

#### Examples


```csharp
using (var archive = new SharArchive())
{
    archive.CreateEntry("data.bin", File.OpenRead("data.bin"));
    archive.Save("archive.shar");
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

### <a id="Aspose_Zip_Shar_SharArchive_DeleteEntry_Aspose_Zip_Shar_SharEntry_"></a> DeleteEntry\(SharEntry\)

Removes the first occurrence of a specific entry from the entry list.

```csharp
public SharArchive DeleteEntry(SharEntry entry)
```

#### Parameters

`entry` [SharEntry](/zip/aspose.zip.shar.sharentry)

The entry to remove from the entries list.

#### Returns

 [SharArchive](/zip/aspose.zip.shar.shararchive)

Shar entry instance.

#### Examples

<p>Here is how you can remove all entries except the last one:</p>

```csharp
using (var archive = new SharArchive("archive.shar"))
{
    while (archive.Entries.Count &gt; 1)
        archive.DeleteEntry(archive.Entries[0]);
    archive.Save(outputSharFile);
}
```

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">entry</code> is null.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Shar_SharArchive_DeleteEntry_System_Int32_"></a> DeleteEntry\(int\)

Removes the entry from the entry list by index.

```csharp
public SharArchive DeleteEntry(int entryIndex)
```

#### Parameters

`entryIndex` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The zero-based index of the entry to remove.

#### Returns

 [SharArchive](/zip/aspose.zip.shar.shararchive)

The archive with the entry deleted.

#### Examples


```csharp
using (var archive = new SharArchive("two_files.shar"))
{
    archive.DeleteEntry(0);
    archive.Save("single_file.shar");
}
```

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

<code class="paramref">entryIndex</code> is less than 0.-or- <code class="paramref">entryIndex</code> is equal to or greater than <code>Entries</code> count.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Shar_SharArchive_Dispose_System_Boolean_"></a> Dispose\(bool\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
protected virtual void Dispose(bool disposing)
```

#### Parameters

`disposing` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether managed resources should be disposed.

### <a id="Aspose_Zip_Shar_SharArchive_Dispose"></a> Dispose\(\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_Shar_SharArchive_Save_System_String_"></a> Save\(string\)

Saves archive to a destination file provided.

```csharp
public void Save(string destinationFileName)
```

#### Parameters

`destinationFileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

#### Examples


```csharp
using (var archive = new SharArchive())
{
    archive.CreateEntry("entry1", "data.bin");        
    archive.Save("archive.shar");
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

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Shar_SharArchive_Save_System_IO_Stream_"></a> Save\(Stream\)

Saves archive to the stream provided.

```csharp
public void Save(Stream output)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

#### Examples


```csharp
using (FileStream sharFile = File.Open("archive.shar", FileMode.Create))
{
    using (var archive = new SharArchive())
    {
        archive.CreateEntry("entry1", "data.bin");        
        archive.Save(sharFile);
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

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.
