---
linkTitle: "Class RarArchive"
title: "Class RarArchive"
description: "This class represents RAR archive file. Use it to extract RAR archives."
summary: "This class represents RAR archive file. Use it to extract RAR archives."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Rar](/zip/aspose.zip.rar)  
Assembly: Aspose.Zip.dll (25.12.0)  

This class represents RAR archive file. Use it to extract RAR archives.

```csharp
public class RarArchive : IArchive, IDisposable
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[RarArchive](/zip/aspose.zip.rar.rararchive)

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

### <a id="Aspose_Zip_Rar_RarArchive__ctor_System_String_Aspose_Zip_Rar_RarArchiveLoadOptions_"></a> RarArchive\(string, RarArchiveLoadOptions\)

Initializes a new instance of the Aspose.Zip.Rar.RarArchive class and composes an entry list can be extracted from the archive.

```csharp
public RarArchive(string path, RarArchiveLoadOptions loadOptions = null)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The fully qualified or the relative path to the archive file.

`loadOptions` [RarArchiveLoadOptions](/zip/aspose.zip.rar.rararchiveloadoptions)

Options to load existing archive with.

#### Examples

<p>The following example extracts an archive, then decompress first entry to a <code>MemoryStream</code>.</p>

```csharp
var extracted = new MemoryStream();
using (RarArchive archive = new RarArchive("data.rar"))
{
    using (var decompressed = archive.Entries[0].Open())
    {
        byte[] b = new byte[8192];
        int bytesRead;
        while (0 &lt; (bytesRead = decompressed.Read(b, 0, b.Length)))
            extracted.Write(b, 0, bytesRead);
    }
}
```

#### Remarks

This constructor does not decompress any entry. See Aspose.Zip.Rar.RarArchiveEntry.Open(System.String) method for decompressing.

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

### <a id="Aspose_Zip_Rar_RarArchive__ctor_System_IO_Stream_Aspose_Zip_Rar_RarArchiveLoadOptions_"></a> RarArchive\(Stream, RarArchiveLoadOptions\)

Initializes a new instance of the Aspose.Zip.Rar.RarArchive class and composes an entry list can be extracted from the archive.

```csharp
public RarArchive(Stream sourceStream, RarArchiveLoadOptions loadOptions = null)
```

#### Parameters

`sourceStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The source of the archive.

`loadOptions` [RarArchiveLoadOptions](/zip/aspose.zip.rar.rararchiveloadoptions)

Options to load existing archive with.

#### Examples

<p>The following example decipher and decompress first entry to a <code>MemoryStream</code>.</p>

```csharp
var fs = File.OpenRead("encrypted.rar");
var extracted = new MemoryStream();
using (RarArchive archive = new RarArchive(fs, new RarArchiveLoadOptions() { DecryptionPassword = "p@s$" }))
{
    using (var decompressed = archive.Entries[0].Open())
    {
        byte[] b = new byte[8192];
        int bytesRead;
        while (0 &lt; (bytesRead = decompressed.Read(b, 0, b.Length)))
            extracted.Write(b, 0, bytesRead);
    }
}
```

#### Remarks

This constructor does not decompress any entry. See Aspose.Zip.Rar.RarArchiveEntry.Open(System.String) method for decompressing.

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">sourceStream</code> is not seekable.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

Wrong signature for archive. - or - The file is not a RAR archive.

## Properties

### <a id="Aspose_Zip_Rar_RarArchive_Entries"></a> Entries

Gets entries of Aspose.Zip.Rar.RarArchiveEntry type constituting the rar archive.

```csharp
public ReadOnlyCollection<RarArchiveEntry> Entries { get; }
```

#### Property Value

 [ReadOnlyCollection](https://learn.microsoft.com/dotnet/api/system.collections.objectmodel.readonlycollection\-1)<[RarArchiveEntry](/zip/aspose.zip.rar.rararchiveentry)\>

## Methods

### <a id="Aspose_Zip_Rar_RarArchive_Dispose_System_Boolean_"></a> Dispose\(bool\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
protected virtual void Dispose(bool disposing)
```

#### Parameters

`disposing` [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether managed resources should be disposed.

### <a id="Aspose_Zip_Rar_RarArchive_Dispose"></a> Dispose\(\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
public void Dispose()
```

### <a id="Aspose_Zip_Rar_RarArchive_ExtractToDirectory_System_String_System_String_"></a> ExtractToDirectory\(string, string\)

Extracts all the files in the archive to the directory provided.

```csharp
[Obsolete("For extraction encrypted RAR archive please provide password in constructor with Aspose.Zip.Rar.RarArchiveLoadOptions.DecryptionPassword")]
public void ExtractToDirectory(string destinationDirectory, string password = null)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory to place the extracted files in.

`password` [string](https://learn.microsoft.com/dotnet/api/system.string)

Optional password for decryption.

#### Examples


```csharp
using (var archive = new RarArchive("archive.rar")) 
{ 
   archive.ExtractToDirectory("C:\extracted", "$ecRet");
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

<code class="paramref">destinationDirectory</code> is a zero-length string, contains only white space, or contains one or more invalid characters. You can query for invalid characters by using the System.IO.Path.GetInvalidPathChars method. -or- path is prefixed with, or contains, only a colon character (:).

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The directory specified by path is a file. -or- The network name is not known.

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.

### <a id="Aspose_Zip_Rar_RarArchive_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

Extracts all the files in the archive to the directory provided.

```csharp
public void ExtractToDirectory(string destinationDirectory)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory to place the extracted files in.

#### Examples


```csharp
using (var archive = new RarArchive("archive.rar")) 
{ 
   archive.ExtractToDirectory("C:\extracted");
}
```

#### Remarks

<p>If the directory does not exist, it will be created.</p>
<p>For extraction encrypted <code>RarArchive</code> use Aspose.Zip.Rar.RarArchiveLoadOptions.DecryptionPassword</p>

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

 [ObjectDisposedException](https://learn.microsoft.com/dotnet/api/system.objectdisposedexception)

Archive has been disposed and cannot be used.
