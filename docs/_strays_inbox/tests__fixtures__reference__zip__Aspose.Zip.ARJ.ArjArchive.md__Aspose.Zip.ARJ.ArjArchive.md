---
linkTitle: "Class ArjArchive"
title: "Class ArjArchive"
description: "This class represents an ARJ archive file."
summary: "This class represents an ARJ archive file."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Arj](/zip/aspose.zip.arj)  
Assembly: Aspose.Zip.dll (25.12.0)  

This class represents an ARJ archive file.

```csharp
public class ArjArchive : IArchive, IDisposable
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ArjArchive](/zip/aspose.zip.arj.arjarchive)

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
            <table><thead><tr><th class="term">Method</th><th class="description">Explanation</th></tr></thead><tbody><tr><td class="term">0</td><td class="description">Uncompressed</td></tr><tr><td class="term">1</td><td class="description">Combination of LZ77 and adaptive Huffman coding. Best ratio.</td></tr><tr><td class="term">2</td><td class="description">Combination of LZ77 and adaptive Huffman coding.</td></tr><tr><td class="term">3</td><td class="description">Combination of LZ77 and adaptive Huffman coding. Best speed.</td></tr></tbody></table>

## Constructors

### <a id="Aspose_Zip_Arj_ArjArchive__ctor_System_IO_Stream_Aspose_Zip_Arj_ArjLoadOptions_"></a> ArjArchive\(Stream, ArjLoadOptions\)

Initializes a new instance of the Aspose.Zip.Arj.ArjArchive class and composes an entry list can be extracted from the archive.

```csharp
public ArjArchive(Stream extractionSource, ArjLoadOptions loadOptions = null)
```

#### Parameters

`extractionSource` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

`loadOptions` [ArjLoadOptions](/zip/aspose.zip.arj.arjloadoptions)

Options to load existing archive with.

#### Remarks

This constructor does not decompress any entry. See Aspose.Zip.Arj.ArjEntryPlain.Extract(System.IO.Stream) method for decompressing.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">extractionSource</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

><code class="paramref">extractionSource</code> does not support seeking.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Wrong signature for archive. - or - The file is not an ARJ archive.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

The archive is garbled.

### <a id="Aspose_Zip_Arj_ArjArchive__ctor_System_String_Aspose_Zip_Arj_ArjLoadOptions_"></a> ArjArchive\(string, ArjLoadOptions\)

Initializes a new instance of the Aspose.Zip.Arj.ArjArchive class and composes an entry list can be extracted from the archive.

```csharp
public ArjArchive(string path, ArjLoadOptions loadOptions = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the archive file.

`loadOptions` [ArjLoadOptions](/zip/aspose.zip.arj.arjloadoptions)

Options to load existing archive with.

#### Examples

<p>The following example shows how to extract all the entries to a directory.</p>

```csharp
using (var archive = new ArjArchive("archive.arj")) 
{ 
   archive.ExtractToDirectory("C:\extracted");
}
```

#### Remarks

This constructor does not unpack any entry. See Aspose.Zip.Arj.ArjEntryPlain.Extract(System.IO.Stream) method for decompressing.

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

### <a id="Aspose_Zip_Arj_ArjArchive_Commentary"></a> Commentary

Gets the commentary.

```csharp
public string Commentary { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Arj_ArjArchive_Entries"></a> Entries

Gets entries of Aspose.Zip.Arj.ArjEntryPlain type constituting the ARJ archive.

```csharp
public ReadOnlyCollection<ArjEntryPlain> Entries { get; }
```

#### Property Value

 [ReadOnlyCollection](https://learn.microsoft.com/dotnet/api/system.collections.objectmodel.readonlycollection\-1)<[ArjEntryPlain](/zip/aspose.zip.arj.arjentryplain)\>

### <a id="Aspose_Zip_Arj_ArjArchive_Name"></a> Name

Gets the original name.

```csharp
public string Name { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

#### Exceptions

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

## Methods

### <a id="Aspose_Zip_Arj_ArjArchive_Dispose"></a> Dispose\(\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_Arj_ArjArchive_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

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
using (var archive = new ArjArchive(File.OpenRead("archive.arj")))
{ 
   archive.ExtractToDirectory("C:\\extracted");
}
```

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

Thrown when the <code class="paramref">destinationDirectory</code> is null.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.
