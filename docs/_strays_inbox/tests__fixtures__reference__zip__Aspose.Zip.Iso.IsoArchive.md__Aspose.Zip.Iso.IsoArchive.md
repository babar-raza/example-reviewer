---
linkTitle: "Class IsoArchive"
title: "Class IsoArchive"
description: "Represents an ISO archive (ISO 9660)."
summary: "Represents an ISO archive (ISO 9660)."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Iso](/zip/aspose.zip.iso)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents an ISO archive (ISO 9660).

```csharp
public sealed class IsoArchive : IArchive, IDisposable
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[IsoArchive](/zip/aspose.zip.iso.isoarchive)

#### Implements

[IArchive](/zip/aspose.zip.iarchive), 
[IDisposable](https://learn.microsoft.com/dotnet/api/system.idisposable)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Iso_IsoArchive__ctor"></a> IsoArchive\(\)

Initializes a new instance of the Aspose.Zip.Iso.IsoArchive class and creates an empty ISO archive
for adding new files and directories.

```csharp
public IsoArchive()
```

#### Examples

The following example shows how to create a new empty ISO archive and add files to it:

```csharp
// Create a new empty ISO archive
using(IsoArchive isoArchive = new IsoArchive())
{
    // Add files to the ISO archive
    isoArchive.CreateEntry("example_file.txt", "path_to_file.txt");

    // Save the ISO archive to a file
    isoArchive.Save("new_archive.iso");
}
```

### <a id="Aspose_Zip_Iso_IsoArchive__ctor_System_IO_Stream_Aspose_Zip_Iso_IsoLoadOptions_"></a> IsoArchive\(Stream, IsoLoadOptions\)

Initializes a new instance of the Aspose.Zip.Iso.IsoArchive class and composes an entry list that can be extracted from the archive.

```csharp
public IsoArchive(Stream sourceStream, IsoLoadOptions loadOptions = null)
```

#### Parameters

`sourceStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive. It must be seekable.

`loadOptions` [IsoLoadOptions](/zip/aspose.zip.iso.isoloadoptions)

The options to load archive with.

#### Examples

<p>The following example shows how to extract all the entries to a directory.</p>

```csharp
using (var archive = new IsoArchive(File.OpenRead("archive.iso")))
{ 
   archive.ExtractToDirectory("C:\\extracted");
}
```

#### Remarks

This constructor does not unpack any entry.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">sourceStream</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">sourceStream</code> is not seekable.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

<code class="paramref">sourceStream</code> is not a valid ISO archive.

### <a id="Aspose_Zip_Iso_IsoArchive__ctor_System_String_Aspose_Zip_Iso_IsoLoadOptions_"></a> IsoArchive\(string, IsoLoadOptions\)

Initializes a new instance of the Aspose.Zip.Iso.IsoArchive class and composes an entry list that can be extracted from the archive.

```csharp
public IsoArchive(string path, IsoLoadOptions loadOptions = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

`loadOptions` [IsoLoadOptions](/zip/aspose.zip.iso.isoloadoptions)

The options to load archive with.

#### Examples

<p>The following example shows how to extract all the entries to a directory.</p>

```csharp
using (var archive = new IsoArchive("archive.iso")) 
{ 
   archive.ExtractToDirectory("C:\\extracted");
}
```

#### Remarks

This constructor does not unpack any entry.

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

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

The file is too short.

## Properties

### <a id="Aspose_Zip_Iso_IsoArchive_Entries"></a> Entries

Gets entries of Aspose.Zip.Iso.IsoEntry type constituting the archive.

```csharp
public ReadOnlyCollection<IsoEntry> Entries { get; }
```

#### Property Value

 [ReadOnlyCollection](https://learn.microsoft.com/dotnet/api/system.collections.objectmodel.readonlycollection\-1)<[IsoEntry](/zip/aspose.zip.iso.isoentry)\>

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

## Methods

### <a id="Aspose_Zip_Iso_IsoArchive_CreateDirectory_System_String_"></a> CreateDirectory\(string\)

Adds a directory to the ISO image.

```csharp
public IsoEntry CreateDirectory(string name)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

Path of the directory in the ISO.

#### Returns

 [IsoEntry](/zip/aspose.zip.iso.isoentry)

The ISO entry composed.

#### Exceptions

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is opened for extraction.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code>name</code> is null or empty.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Iso_IsoArchive_CreateEntry_System_String_System_String_"></a> CreateEntry\(string, string\)

Adds a file to the ISO image.

```csharp
public IsoEntry CreateEntry(string name, string filePath)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

Path of the file in the ISO.

`filePath` [string](https://learn.microsoft.com/dotnet/api/system.string)

Path of the file.

#### Returns

 [IsoEntry](/zip/aspose.zip.iso.isoentry)

The ISO entry composed.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

The <code class="paramref">filePath</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">filePath</code> is empty, contains only white spaces, or contains invalid characters.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">filePath</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">filePath</code> exceeds the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">filePath</code> contains a colon (:) in the middle of the string.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

An I/O error occurred while opening the file.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Iso_IsoArchive_CreateEntry_System_String_System_IO_Stream_"></a> CreateEntry\(string, Stream\)

Adds a file to the ISO image.

```csharp
public IsoEntry CreateEntry(string name, Stream source)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

Path of the file in the ISO.

`source` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Stream containing the file data.

#### Returns

 [IsoEntry](/zip/aspose.zip.iso.isoentry)

The ISO entry composed.

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Iso_IsoArchive_CreateEntry_System_String_"></a> CreateEntry\(string\)

Adds a file to the ISO image.

```csharp
public IsoEntry CreateEntry(string name)
```

#### Parameters

`name` [string](https://learn.microsoft.com/dotnet/api/system.string)

Path of the directory in the ISO.

#### Returns

 [IsoEntry](/zip/aspose.zip.iso.isoentry)

The ISO entry composed.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code>name</code> is null or empty.

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

The archive is opened for extraction.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Iso_IsoArchive_Dispose"></a> Dispose\(\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_Iso_IsoArchive_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

Extracts all entries to the specified directory.

```csharp
public void ExtractToDirectory(string destinationDirectory)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The directory to extract the entries to.

#### Examples

The following example shows how to extract all entries to a directory:

```csharp
using (var archive = new IsoArchive(File.OpenRead("archive.iso")))
{ 
   archive.ExtractToDirectory("C:\\extracted");
}
```

#### Exceptions

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

Thrown when the archive is in editing mode.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

Thrown when the <code class="paramref">destinationDirectory</code> is null.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Iso_IsoArchive_Save_System_String_Aspose_Zip_Iso_IsoSaveOptions_"></a> Save\(string, IsoSaveOptions\)

Saves the ISO image to the specified path.

```csharp
public void Save(string path, IsoSaveOptions saveOptions = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path where the ISO image will be saved.

`saveOptions` [IsoSaveOptions](/zip/aspose.zip.iso.isosaveoptions)

Options to save ISO archive with.

#### Examples

The following example shows how to save an ISO archive to a file:

```csharp
// Create a new empty ISO archive
using(IsoArchive isoArchive = new IsoArchive())
{
    // Add files to the ISO archive
    isoArchive.CreateEntry("example_file.txt", "path_to_file.txt");

    // Save the ISO archive to a file
    isoArchive.Save("new_archive.iso");
}
```

#### Exceptions

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

Thrown when the archive is not in editing mode.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

Thrown when the <code class="paramref">path</code> is null.

 [DirectoryNotFoundException](https://learn.microsoft.com/dotnet/api/system.io.directorynotfoundexception)

Thrown when the specified path is invalid, such as being on an unmapped drive.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

Thrown when the file is already open.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Thrown when access to the file <code class="paramref">path</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

Thrown when the specified <code class="paramref">path</code> exceeds the system-defined maximum length.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Iso_IsoArchive_Save_System_IO_Stream_Aspose_Zip_Iso_IsoSaveOptions_"></a> Save\(Stream, IsoSaveOptions\)

Saves the ISO image to the specified stream.

```csharp
public void Save(Stream stream, IsoSaveOptions saveOptions = null)
```

#### Parameters

`stream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The stream where the ISO image will be saved.

`saveOptions` [IsoSaveOptions](/zip/aspose.zip.iso.isosaveoptions)

Options to save ISO archive with.

#### Examples

The following example shows how to save an ISO archive to a memory stream:

```csharp
// Create a new empty ISO archive
using(IsoArchive isoArchive = new IsoArchive())
{
    // Add files to the ISO archive
    isoArchive.CreateEntry("example_file.txt", "path_to_file.txt");

    // Save the ISO archive to a memory stream
    isoArchive.Save(memoryStream);
}
```

#### Exceptions

 [InvalidOperationException](https://learn.microsoft.com/dotnet/api/system.invalidoperationexception)

Thrown when the archive is not in editing mode.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

Thrown when the <code class="paramref">stream</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

Thrown when the <code class="paramref">stream</code> is not writable.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.
