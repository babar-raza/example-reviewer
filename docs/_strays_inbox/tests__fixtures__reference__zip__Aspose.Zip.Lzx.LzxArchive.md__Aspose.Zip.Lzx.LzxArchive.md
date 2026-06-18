---
linkTitle: "Class LzxArchive"
title: "Class LzxArchive"
description: "This class represents a LZX (.lzx) archive file."
summary: "This class represents a LZX (.lzx) archive file."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Lzx](/zip/aspose.zip.lzx)  
Assembly: Aspose.Zip.dll (25.12.0)  

This class represents a LZX (.lzx) archive file.

```csharp
public class LzxArchive : IArchive, IDisposable
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[LzxArchive](/zip/aspose.zip.lzx.lzxarchive)

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

### <a id="Aspose_Zip_Lzx_LzxArchive__ctor_System_IO_Stream_Aspose_Zip_Lzx_LzxLoadOptions_"></a> LzxArchive\(Stream, LzxLoadOptions\)

Initializes a new instance of the Aspose.Zip.Lzx.LzxArchive class and composes an entry list can be extracted from the archive.

```csharp
public LzxArchive(Stream extractionSource, LzxLoadOptions loadOptions = null)
```

#### Parameters

`extractionSource` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

`loadOptions` [LzxLoadOptions](/zip/aspose.zip.lzx.lzxloadoptions)

Options to load existing archive with.

#### Remarks

This constructor does not decompress any entry. See Aspose.Zip.Lzx.LzxArchiveEntry.Extract(System.IO.Stream) method for decompressing.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">extractionSource</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">extractionSource</code> does not support seeking.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Wrong signature for archive. - or - The file is not a LZX archive.

 [NotImplementedException](https://learn.microsoft.com/dotnet/api/system.notimplementedexception)

Lzx archive contains merged entries.

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

The <code class="paramref">extractionSource</code> stream is too short.

### <a id="Aspose_Zip_Lzx_LzxArchive__ctor_System_String_Aspose_Zip_Lzx_LzxLoadOptions_"></a> LzxArchive\(string, LzxLoadOptions\)

Initializes a new instance of the Aspose.Zip.Lzx.LzxArchive class and composes an entry list can be extracted from the archive.

```csharp
public LzxArchive(string path, LzxLoadOptions loadOptions = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The fully qualified or the relative path to the archive file.

`loadOptions` [LzxLoadOptions](/zip/aspose.zip.lzx.lzxloadoptions)

Options to load existing archive with.

#### Examples

<p>The following example extracts an archive, then decompress first entry to a <code>MemoryStream</code>.</p>

```csharp
var extracted = new MemoryStream();
using (LzxArchive archive = new LzxArchive("sample.lzx"))
{
    archive.Entries[0].Extract(extracted);
}
```

#### Remarks

This constructor does not decompress any entry. See Aspose.Zip.Lzx.LzxArchiveEntry.Extract(System.IO.Stream) method for decompressing.

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

 [NotImplementedException](https://learn.microsoft.com/dotnet/api/system.notimplementedexception)

Lzx archive contains merged entries.

 [EndOfStreamException](https://learn.microsoft.com/dotnet/api/system.io.endofstreamexception)

The file is too short.

## Properties

### <a id="Aspose_Zip_Lzx_LzxArchive_Entries"></a> Entries

Gets file entries of Aspose.Zip.Lzx.LzxArchiveEntry type constituting the archive.

```csharp
public ReadOnlyCollection<LzxArchiveEntry> Entries { get; }
```

#### Property Value

 [ReadOnlyCollection](https://learn.microsoft.com/dotnet/api/system.collections.objectmodel.readonlycollection\-1)<[LzxArchiveEntry](/zip/aspose.zip.lzx.lzxarchiveentry)\>

## Methods

### <a id="Aspose_Zip_Lzx_LzxArchive_Dispose"></a> Dispose\(\)

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_Lzx_LzxArchive_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

Extracts all the files and directories in the archive to the directory provided.

```csharp
public void ExtractToDirectory(string destinationDirectory)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory to place the extracted files in.

#### Examples


```csharp
using (var archive = new LzxArchive("archive.lzx")) 
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

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Wrong password has been supplied. - or - Archive is corrupted.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

Invalid compression method.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.
