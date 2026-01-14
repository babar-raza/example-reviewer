---
linkTitle: "Class ArchiveInstanceInfo"
title: "Class ArchiveInstanceInfo"
description: "Represents information about the archive instance."
summary: "Represents information about the archive instance."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.ArchiveInfo](/zip/aspose.zip.archiveinfo)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents information about the archive instance.

```csharp
public sealed class ArchiveInstanceInfo
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ArchiveInstanceInfo](/zip/aspose.zip.archiveinfo.archiveinstanceinfo)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Properties

### <a id="Aspose_Zip_ArchiveInfo_ArchiveInstanceInfo_AreFileNamesEncrypted"></a> AreFileNamesEncrypted

Gets a value indicating whether the names of entries (files) of the archive are encrypted.

```csharp
public bool AreFileNamesEncrypted { get; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_ArchiveInfo_ArchiveInstanceInfo_FormatInfo"></a> FormatInfo

Gets the archive format info.

```csharp
public ArchiveFormatInfo FormatInfo { get; }
```

#### Property Value

 [ArchiveFormatInfo](/zip/aspose.zip.archiveinfo.archiveformatinfo)

### <a id="Aspose_Zip_ArchiveInfo_ArchiveInstanceInfo_IsContentEncrypted"></a> IsContentEncrypted

Gets a value indicating whether the content of the archive is encrypted.

```csharp
public bool IsContentEncrypted { get; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

## Methods

### <a id="Aspose_Zip_ArchiveInfo_ArchiveInstanceInfo_GetArchiveFormatInfo_System_String_"></a> GetArchiveFormatInfo\(string\)

Gets archive format info.

```csharp
public static ArchiveFormatInfo GetArchiveFormatInfo(string fileName)
```

#### Parameters

`fileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

The filename of the archive file.

#### Returns

 [ArchiveFormatInfo](/zip/aspose.zip.archiveinfo.archiveformatinfo)

Information about archive format.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">fileName</code> is null.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">fileName</code> is empty, contains only white spaces, or contains invalid characters.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">fileName</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">fileName</code> exceeds the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">fileName</code> contains a colon (:) in the middle of the string.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

An I/O error occurred while opening the file.

### <a id="Aspose_Zip_ArchiveInfo_ArchiveInstanceInfo_GetArchiveFormatInfo_System_IO_Stream_"></a> GetArchiveFormatInfo\(Stream\)

Gets archive format info.

```csharp
public static ArchiveFormatInfo GetArchiveFormatInfo(Stream stream)
```

#### Parameters

`stream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The stream of the archive file.

#### Returns

 [ArchiveFormatInfo](/zip/aspose.zip.archiveinfo.archiveformatinfo)

Information about archive format.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">stream</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">stream</code> is not seekable.

### <a id="Aspose_Zip_ArchiveInfo_ArchiveInstanceInfo_GetArchiveInstanceInfo_System_String_"></a> GetArchiveInstanceInfo\(string\)

Gets archive instance info.

```csharp
public static ArchiveInstanceInfo GetArchiveInstanceInfo(string fileName)
```

#### Parameters

`fileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

The filename of the archive file.

#### Returns

 [ArchiveInstanceInfo](/zip/aspose.zip.archiveinfo.archiveinstanceinfo)

Information about archive instance or null if format was not detected.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">fileName</code> is null.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The <code class="paramref">fileName</code> is empty, contains only white spaces, or contains invalid characters.

 [UnauthorizedAccessException](https://learn.microsoft.com/dotnet/api/system.unauthorizedaccessexception)

Access to file <code class="paramref">fileName</code> is denied.

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified <code class="paramref">fileName</code> exceeds the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters, and file names must be less than 260 characters.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

File at <code class="paramref">fileName</code> contains a colon (:) in the middle of the string.

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

An I/O error occurred while opening the file.

### <a id="Aspose_Zip_ArchiveInfo_ArchiveInstanceInfo_GetArchiveInstanceInfo_System_IO_Stream_"></a> GetArchiveInstanceInfo\(Stream\)

Gets archive instance info.

```csharp
public static ArchiveInstanceInfo GetArchiveInstanceInfo(Stream stream)
```

#### Parameters

`stream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The stream of the archive file.

#### Returns

 [ArchiveInstanceInfo](/zip/aspose.zip.archiveinfo.archiveinstanceinfo)

Information about archive instance or null if format was not detected.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">stream</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">stream</code> is not seekable.
