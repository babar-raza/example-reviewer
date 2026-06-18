---
linkTitle: "Class IsoEntry"
title: "Class IsoEntry"
description: "Represents an entry (file or directory) within an ISO archive."
summary: "Represents an entry (file or directory) within an ISO archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Iso](/zip/aspose.zip.iso)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents an entry (file or directory) within an ISO archive.

```csharp
public abstract class IsoEntry : IArchiveFileEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[IsoEntry](/zip/aspose.zip.iso.isoentry)

#### Implements

[IArchiveFileEntry](/zip/aspose.zip.iarchivefileentry)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Properties

### <a id="Aspose_Zip_Iso_IsoEntry_IsDirectory"></a> IsDirectory

Gets a value indicating whether the entry is a directory.

```csharp
public bool IsDirectory { get; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_Iso_IsoEntry_Length"></a> Length

Gets or sets creation date and time.

```csharp
public long? Length { get; }
```

#### Property Value

 [long](https://learn.microsoft.com/dotnet/api/system.int64)?

### <a id="Aspose_Zip_Iso_IsoEntry_ModificationTime"></a> ModificationTime

Gets or sets last modified date and time.

```csharp
public DateTime ModificationTime { get; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_Iso_IsoEntry_Name"></a> Name

Gets the name of the entry.

```csharp
public string Name { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

## Methods

### <a id="Aspose_Zip_Iso_IsoEntry_Extract_System_String_"></a> Extract\(string\)

Extracts the entry to the filesystem by the path provided.

```csharp
public FileInfo Extract(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to destination file. If the file already exists, it will be overwritten.

#### Returns

 [FileInfo](https://learn.microsoft.com/dotnet/api/system.io.fileinfo)

System.IO.FileInfo instance containing extracted data.

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

### <a id="Aspose_Zip_Iso_IsoEntry_Extract_System_IO_Stream_"></a> Extract\(Stream\)

Extracts the entry to the stream provided.

```csharp
public void Extract(Stream destination)
```

#### Parameters

`destination` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Destination stream. Must be writable.

#### Exceptions

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">destination</code> does not support writing.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

Raises if the entry does not represent a file.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

Supplied stream does not support writing.

### <a id="Aspose_Zip_Iso_IsoEntry_ToString"></a> ToString\(\)

Returns a string that represents the current entry.

```csharp
public override string ToString()
```

#### Returns

 [string](https://learn.microsoft.com/dotnet/api/system.string)

Name of the entry.
