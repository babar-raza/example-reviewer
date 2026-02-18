---
linkTitle: "Class XarArchive"
title: "Class XarArchive"
description: "This class represents a xar archive file."
summary: "This class represents a xar archive file."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Xar](/zip/aspose.zip.xar)  
Assembly: Aspose.Zip.dll (25.12.0)  

This class represents a xar archive file.

```csharp
public class XarArchive : IArchive, IDisposable
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[XarArchive](/zip/aspose.zip.xar.xararchive)

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

### <a id="Aspose_Zip_Xar_XarArchive__ctor_Aspose_Zip_Xar_XarCompressionSettings_"></a> XarArchive\(XarCompressionSettings\)

Initializes a new instance of the Aspose.Zip.Xar.XarArchive class.

```csharp
public XarArchive(XarCompressionSettings defaultCompressionSettings = null)
```

#### Parameters

`defaultCompressionSettings` [XarCompressionSettings](/zip/aspose.zip.xar.xarcompressionsettings)

The default compression settings, applyed to all entries of the archive.

#### Examples

<p>The following example shows how to compress a file.</p>

```csharp
using (var archive = new XarArchive())
{
    archive.CreateEntry("first.bin", "data.bin");
    archive.Save("archive.xar");
}
```

### <a id="Aspose_Zip_Xar_XarArchive__ctor_System_IO_Stream_Aspose_Zip_Xar_XarLoadOptions_"></a> XarArchive\(Stream, XarLoadOptions\)

Initializes a new instance of the Aspose.Zip.Xar.XarArchive class and composes an entry list can be extracted from the archive.

```csharp
public XarArchive(Stream sourceStream, XarLoadOptions loadOptions = null)
```

#### Parameters

`sourceStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive. It must be seekable.

`loadOptions` [XarLoadOptions](/zip/aspose.zip.xar.xarloadoptions)

The options to load archive with.

#### Examples

<p>The following example shows how to extract all the entries to a directory.</p>

```csharp
using (var archive = new XarArchive(File.OpenRead("archive.xar")))
{
   archive.ExtractToDirectory("C:\\extracted");
}
```

#### Remarks

This constructor does not unpack any entry. See Aspose.Zip.Xar.XarFileEntry.Open method for unpacking.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">sourceStream</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">sourceStream</code> is not seekable.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

<code class="paramref">sourceStream</code> is not valid xar archive.

### <a id="Aspose_Zip_Xar_XarArchive__ctor_System_String_Aspose_Zip_Xar_XarLoadOptions_"></a> XarArchive\(string, XarLoadOptions\)

Initializes a new instance of the Aspose.Zip.Xar.XarArchive class and composes an entry list can be extracted from the archive.

```csharp
public XarArchive(string path, XarLoadOptions loadOptions = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

`loadOptions` [XarLoadOptions](/zip/aspose.zip.xar.xarloadoptions)

The options to load archive with.

#### Examples

<p>The following example shows how to extract all the entries to a directory.</p>

```csharp
using (var archive = new XarArchive("archive.xar")) 
{
   archive.ExtractToDirectory("C:\\extracted");
}
```

#### Remarks

This constructor does not unpack any entry. See Aspose.Zip.Xar.XarFileEntry.Open method for unpacking.

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

File at <code class="paramref">path</code> is not valid xar archive.

## Properties

### <a id="Aspose_Zip_Xar_XarArchive_Entries"></a> Entries

Gets entries of Aspose.Zip.Xar.XarEntry type constituting the archive.

```csharp
public IEnumerable<XarEntry> Entries { get; }
```

#### Property Value

 [IEnumerable](https://learn.microsoft.com/dotnet/api/system.collections.generic.ienumerable\-1)<[XarEntry](/zip/aspose.zip.xar.xarentry)\>

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

## Methods

### <a id="Aspose_Zip_Xar_XarArchive_CreateEntries_System_String_System_Boolean_Aspose_Zip_Xar_XarCompressionSettings_"></a> CreateEntries\(string, bool, XarCompressionSettings\)

Adds to the archive all the files and directories recursively in the directory given.

```csharp
public XarArchive CreateEntries(string sourceDirectory, bool includeRootDirectory = true, XarCompressionSettings compressionSettings = null)
```

#### Parameters

`sourceDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

Directory to compress.

`includeRootDirectory` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Indicates whether to include the root directory itself or not.

`compressionSettings` [XarCompressionSettings](/zip/aspose.zip.xar.xarcompressionsettings)

The compression settings used for added Aspose.Zip.Xar.XarEntry items.

#### Returns

 [XarArchive](/zip/aspose.zip.xar.xararchive)

Xar entry instance.

#### Examples


```csharp
using (FileStream xarFile = File.Open("archive.xar", FileMode.Create))
{
    using (var archive = new XarArchive())
    {
        archive.CreateEntries(@"C:\folder", false);
        archive.Save(xarFile);
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

### <a id="Aspose_Zip_Xar_XarArchive_CreateEntries_System_IO_DirectoryInfo_System_Boolean_Aspose_Zip_Xar_XarCompressionSettings_"></a> CreateEntries\(DirectoryInfo, bool, XarCompressionSettings\)

Adds to the archive all the files and directories recursively in the directory given.

```csharp
public XarArchive CreateEntries(DirectoryInfo directory, bool includeRootDirectory = true, XarCompressionSettings compressionSettings = null)
```

#### Parameters

`directory` [DirectoryInfo](https://learn.microsoft.com/dotnet/api/system.io.directoryinfo)

Directory to compress.

`includeRootDirectory` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Indicates whether to include the root directory itself or not.

`compressionSettings` [XarCompressionSettings](/zip/aspose.zip.xar.xarcompressionsettings)

The compression settings used for added Aspose.Zip.Xar.XarEntry items.

#### Returns

 [XarArchive](/zip/aspose.zip.xar.xararchive)

Xar entry instance.

#### Examples


```csharp
using (FileStream xarFile = File.Open("archive.xar", FileMode.Create))
{
    using (var archive = new XarArchive())
    {
        archive.CreateEntries(new DirectoryInfo(@"C:\folder"), false);
        archive.Save(xarFile);
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

### <a id="Aspose_Zip_Xar_XarArchive_CreateEntry_System_String_System_IO_FileInfo_System_Boolean_Aspose_Zip_Xar_XarCompressionSettings_"></a> CreateEntry\(string, FileInfo, bool, XarCompressionSettings\)

Create a single entry within the archive.

```csharp
public XarEntry CreateEntry(string name, FileInfo fileInfo, bool openImmediately = false, XarCompressionSettings compressionSettings = null)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`fileInfo` [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

The metadata of file or folder to be compressed.

`openImmediately` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

True, if open the file immediately, otherwise open the file on archive saving.

`compressionSettings` [XarCompressionSettings](/zip/aspose.zip.xar.xarcompressionsettings)

The compression settings used for added Aspose.Zip.Xar.XarEntry item.

#### Returns

 [XarEntry](/zip/aspose.zip.xar.xarentry)

Xar entry instance.

#### Examples


```csharp
FileInfo fileInfo = new FileInfo("data.bin");
using (var archive = new XarArchive())
{
    archive.CreateEntry("test.bin", fileInfo);
    archive.Save("archive.xar");
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

### <a id="Aspose_Zip_Xar_XarArchive_CreateEntry_System_String_System_String_System_Boolean_Aspose_Zip_Xar_XarCompressionSettings_"></a> CreateEntry\(string, string, bool, XarCompressionSettings\)

Create a single entry within the archive.

```csharp
public XarEntry CreateEntry(string name, string sourcePath, bool openImmediately = false, XarCompressionSettings compressionSettings = null)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`sourcePath` [string](https://learn.microsoft.com/dotnet/api/system.string)

Path to file to be compressed.

`openImmediately` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

True, if open the file immediately, otherwise open the file on archive saving.

`compressionSettings` [XarCompressionSettings](/zip/aspose.zip.xar.xarcompressionsettings)

The compression settings used for added Aspose.Zip.Xar.XarEntry item.

#### Returns

 [XarEntry](/zip/aspose.zip.xar.xarentry)

Xar entry instance.

#### Examples


```csharp
using (var archive = new XarArchive())
{
    archive.CreateEntry("first.bin", "data.bin");
    archive.Save("archive.xar");
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

The specified <code class="paramref">sourcePath</code>, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters. - or - <code class="paramref">name</code> is too long for xar.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">sourcePath</code> contains a colon (:) in the middle of the string.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

Impossible to modify xar archive.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Xar_XarArchive_CreateEntry_System_String_System_IO_Stream_Aspose_Zip_Xar_XarCompressionSettings_"></a> CreateEntry\(string, Stream, XarCompressionSettings\)

Create a single entry within the archive.

```csharp
public XarEntry CreateEntry(string name, Stream source, XarCompressionSettings compressionSettings = null)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name of the entry.

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The input stream for the entry.

`compressionSettings` [XarCompressionSettings](/zip/aspose.zip.xar.xarcompressionsettings)

The compression settings used for added Aspose.Zip.Xar.XarEntry item.

#### Returns

 [XarEntry](/zip/aspose.zip.xar.xarentry)

Xar entry instance.

#### Examples


```csharp
using (var archive = new XarArchive())
{
    archive.CreateEntry("data.bin", File.OpenRead("data.bin"));
    archive.Save("archive.xar");
}
```

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">name</code> is null.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">source</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">name</code> is empty.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

Impossible to modify xar archive.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Xar_XarArchive_DeleteEntry_Aspose_Zip_Xar_XarEntry_"></a> DeleteEntry\(XarEntry\)

Removes the first occurrence of a specific entry from the entry list.

```csharp
public XarArchive DeleteEntry(XarEntry entry)
```

#### Parameters

`entry` [XarEntry](/zip/aspose.zip.xar.xarentry)

The entry to remove from the entries list.

#### Returns

 [XarArchive](/zip/aspose.zip.xar.xararchive)

Xar entry instance.

#### Examples

<p>Here is how you can remove all entries except the last one:</p>

```csharp
using (var archive = new XarArchive("archive.xar"))
{
    while (archive.Entries.Count &gt; 1)
        archive.DeleteEntry(archive.Entries.FirstOrDefault());
    archive.Save(outputXarFile);
}
```

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">entry</code> is null.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Xar_XarArchive_Dispose"></a> Dispose\(\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_Xar_XarArchive_Dispose_System_Boolean_"></a> Dispose\(bool\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
protected virtual void Dispose(bool disposing)
```

#### Parameters

`disposing` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether managed resources should be disposed.

### <a id="Aspose_Zip_Xar_XarArchive_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

Extracts all the files in the archive to the directory provided.

```csharp
public void ExtractToDirectory(string destinationDirectory)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory to place the extracted files in.

#### Examples


```csharp
using (var archive = new XarArchive("archive.xar")) 
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

The specified path, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters and file names must be less than 260 characters.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access the existing directory.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

If the directory does not exist, the path contains a colon character (:) that is not part of a drive label ("C:\").

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

path is a zero-length string, contains only white space, or contains one or more invalid characters. You can query for invalid characters by using the System.IO.Path.GetInvalidPathChars method. -or- path is prefixed with, or contains, only a colon character (:).

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The directory specified by path is a file. -or- The network name is not known.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The archive is corrupted.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Xar_XarArchive_Save_System_String_Aspose_Zip_Xar_XarSaveOptions_"></a> Save\(string, XarSaveOptions\)

Saves archive to the destination file provided.

```csharp
public void Save(string destinationFileName, XarSaveOptions saveOptions = null)
```

#### Parameters

`destinationFileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of the archive to be created. If the specified file name points to an existing file, it will be overwritten.

`saveOptions` [XarSaveOptions](/zip/aspose.zip.xar.xarsaveoptions)

Options to save xar archive with.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">destinationFileName</code> is null.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

Impossible to modify xar archive.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Xar_XarArchive_Save_System_IO_Stream_Aspose_Zip_Xar_XarSaveOptions_"></a> Save\(Stream, XarSaveOptions\)

Saves archive to the stream provided.

```csharp
public void Save(Stream output, XarSaveOptions saveOptions = null)
```

#### Parameters

`output` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream.

`saveOptions` [XarSaveOptions](/zip/aspose.zip.xar.xarsaveoptions)

Options to save xar archive with.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">output</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">output</code>Is not writable/readable or not seekable.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

Impossible to modify xar archive.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.
