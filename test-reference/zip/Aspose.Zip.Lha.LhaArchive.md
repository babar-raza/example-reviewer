---
linkTitle: "Class LhaArchive"
title: "Class LhaArchive"
description: "This class represents a LHA (.lzh) archive file."
summary: "This class represents a LHA (.lzh) archive file."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Lha](/zip/aspose.zip.lha)  
Assembly: Aspose.Zip.dll (25.12.0)  

This class represents a LHA (.lzh) archive file.

```csharp
public class LhaArchive : IArchive, IDisposable
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[LhaArchive](/zip/aspose.zip.lha.lhaarchive)

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

## Remarks

Only the following compression methods are supported:
            <table><thead><tr><th class="term">Method</th><th class="description">Explanation</th></tr></thead><tbody><tr><td class="term">lh0</td><td class="description">Uncompressed</td></tr><tr><td class="term">lh4</td><td class="description">8 KiB sliding dictionary and static Huffman</td></tr><tr><td class="term">lh5</td><td class="description">16 KiB sliding dictionary and static Huffman</td></tr><tr><td class="term">lh6</td><td class="description">64 KiB sliding dictionary and static Huffman</td></tr><tr><td class="term">lh7</td><td class="description">128 KiB sliding dictionary and static Huffman</td></tr><tr><td class="term">lhx</td><td class="description">1 Mib sliding dictionary and static Huffman</td></tr><tr><td class="term">lhd</td><td class="description">Directory</td></tr></tbody></table>

## Constructors

### <a id="Aspose_Zip_Lha_LhaArchive__ctor_System_IO_Stream_Aspose_Zip_Lha_LhaLoadOptions_"></a> LhaArchive\(Stream, LhaLoadOptions\)

Initializes a new instance of the Aspose.Zip.Lha.LhaArchive class and composes an entry list can be extracted from the archive.

```csharp
public LhaArchive(Stream sourceStream, LhaLoadOptions loadOptions = null)
```

#### Parameters

`sourceStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

`loadOptions` [LhaLoadOptions](/zip/aspose.zip.lha.lhaloadoptions)

Options to load existing archive with.

#### Remarks

This constructor does not decompress any entry. See Aspose.Zip.Lha.LhaArchiveEntry.Extract(System.IO.Stream) method for decompressing.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">sourceStream</code> is null

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">sourceStream</code> is unseekable.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Inappropriate data found.

### <a id="Aspose_Zip_Lha_LhaArchive__ctor_System_String_Aspose_Zip_Lha_LhaLoadOptions_"></a> LhaArchive\(string, LhaLoadOptions\)

Initializes a new instance of the Aspose.Zip.Lha.LhaArchive class and composes an entry list can be extracted from the archive.

```csharp
public LhaArchive(string path, LhaLoadOptions loadOptions = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The fully qualified or the relative path to the archive file.

`loadOptions` [LhaLoadOptions](/zip/aspose.zip.lha.lhaloadoptions)

Options to load existing archive with.

#### Examples

<p>The following example extracts an archive, then decompress first entry to a <code>MemoryStream</code>.</p>

```csharp
var extracted = new MemoryStream();
using (LhaArchive archive = new LhaArchive("sample.lzh"))
{
    archive.Entries[0].Extract(extracted);
}
```

#### Remarks

This constructor does not decompress any entry. See Aspose.Zip.Lha.LhaArchiveEntry.Extract(System.IO.Stream) method for decompressing.

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

## Properties

### <a id="Aspose_Zip_Lha_LhaArchive_Entries"></a> Entries

Gets file entries of Aspose.Zip.Lha.LhaArchiveEntry type constituting the archive.

```csharp
public ReadOnlyCollection<LhaArchiveEntry> Entries { get; }
```

#### Property Value

 [ReadOnlyCollection](https://learn.microsoft.com/dotnet/api/system.collections.objectmodel.readonlycollection\-1)<[LhaArchiveEntry](/zip/aspose.zip.lha.lhaarchiveentry)\>

## Methods

### <a id="Aspose_Zip_Lha_LhaArchive_Dispose"></a> Dispose\(\)

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_Lha_LhaArchive_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

Extracts all the files and directories in the archive to the directory provided.

```csharp
public void ExtractToDirectory(string destinationDirectory)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory to place the extracted files in.

#### Examples


```csharp
using (var archive = new LhaArchive("archive.lzh")) 
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

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.
