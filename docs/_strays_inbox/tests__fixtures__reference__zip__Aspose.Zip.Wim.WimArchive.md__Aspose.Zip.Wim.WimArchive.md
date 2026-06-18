---
linkTitle: "Class WimArchive"
title: "Class WimArchive"
description: "This class represents a wim archive file."
summary: "This class represents a wim archive file."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Wim](/zip/aspose.zip.wim)  
Assembly: Aspose.Zip.dll (25.12.0)  

This class represents a wim archive file.

```csharp
public class WimArchive : IArchive, IDisposable
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[WimArchive](/zip/aspose.zip.wim.wimarchive)

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

### <a id="Aspose_Zip_Wim_WimArchive__ctor_System_IO_Stream_Aspose_Zip_Wim_WimLoadOptions_"></a> WimArchive\(Stream, WimLoadOptions\)

Initializes a new instance of the Aspose.Zip.Wim.WimArchive class and composes an entry list can be extracted from the archive.

```csharp
public WimArchive(Stream sourceStream, WimLoadOptions loadOptions = null)
```

#### Parameters

`sourceStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive. It must be seekable.

`loadOptions` [WimLoadOptions](/zip/aspose.zip.wim.wimloadoptions)

Options to load existing archive with.

#### Examples

<p>The following example shows how to extract all the entries to a directory.</p>

```csharp
using (var archive = new WimArchive(File.OpenRead("archive.wim")))
{ 
   archive.Images[0].ExtractToDirectory("C:\\extracted");
}
```

#### Remarks

This constructor does not unpack any entry. See Aspose.Zip.Wim.WimFileEntry.Open method for unpacking.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">sourceStream</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">sourceStream</code> is not seekable.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

<code class="paramref">sourceStream</code> is not valid wim archive.

### <a id="Aspose_Zip_Wim_WimArchive__ctor_System_String_Aspose_Zip_Wim_WimLoadOptions_"></a> WimArchive\(string, WimLoadOptions\)

Initializes a new instance of the Aspose.Zip.Wim.WimArchive class and composes an entry list can be extracted from the archive.

```csharp
public WimArchive(string path, WimLoadOptions loadOptions = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

`loadOptions` [WimLoadOptions](/zip/aspose.zip.wim.wimloadoptions)

Options to load existing archive with.

#### Examples

<p>The following example shows how to extract all the entries to a directory.</p>

```csharp
using (var archive = new WimArchive("archive.wim")) 
{ 
   archive.Images[0].ExtractToDirectory("C:\\extracted");
}
```

#### Remarks

This constructor does not unpack any entry. See Aspose.Zip.Wim.WimFileEntry.Open method for unpacking.

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

### <a id="Aspose_Zip_Wim_WimArchive_BootImageIndex"></a> BootImageIndex

Gets the (zero-based) index of the bootable image.

```csharp
public int BootImageIndex { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Wim_WimArchive_FileFormatVersion"></a> FileFormatVersion

Gets the version of the file format.

```csharp
public int FileFormatVersion { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Wim_WimArchive_Guid"></a> Guid

Gets the identifying GUID for the archive.

```csharp
public Guid Guid { get; }
```

#### Property Value

 [Guid](https://learn.microsoft.com/dotnet/api/system.guid)

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Wim_WimArchive_Images"></a> Images

Gets entries of Aspose.Zip.Wim.WimImage type constituting the archive.

```csharp
public ReadOnlyCollection<WimImage> Images { get; }
```

#### Property Value

 [ReadOnlyCollection](https://learn.microsoft.com/dotnet/api/system.collections.objectmodel.readonlycollection\-1)<[WimImage](/zip/aspose.zip.wim.wimimage)\>

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Wim_WimArchive_Manifest"></a> Manifest

Gets the embedded manifest describing the file and the contained images.

```csharp
public string Manifest { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

## Methods

### <a id="Aspose_Zip_Wim_WimArchive_Dispose_System_Boolean_"></a> Dispose\(bool\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
protected virtual void Dispose(bool disposing)
```

#### Parameters

`disposing` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether managed resources should be disposed.

### <a id="Aspose_Zip_Wim_WimArchive_Dispose"></a> Dispose\(\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_Wim_WimArchive_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

Extracts the archive to the file by path.

```csharp
public void ExtractToDirectory(string destinationDirectory)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory to place the extracted files in.

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">destinationDirectory</code> is null

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified path, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters and file names must be less than 260 characters.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access the existing directory.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

If the directory does not exist, the path contains a colon character (:) that is not part of a drive label ("C:\") - or - WIM archive is multi-part.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

path is a zero-length string, contains only white space, or contains one or more invalid characters. You can query for invalid characters by using the System.IO.Path.GetInvalidPathChars method. -or- path is prefixed with, or contains, only a colon character (:).

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The directory specified by path is a file. -or- The network name is not known.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The archive is corrupted.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.
