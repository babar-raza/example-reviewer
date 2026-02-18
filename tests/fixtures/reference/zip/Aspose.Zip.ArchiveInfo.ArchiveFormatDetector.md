---
linkTitle: "Class ArchiveFormatDetector"
title: "Class ArchiveFormatDetector"
description: "Detects an archive format and provides other related information."
summary: "Detects an archive format and provides other related information."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.ArchiveInfo](/zip/aspose.zip.archiveinfo)  
Assembly: Aspose.Zip.dll (25.12.0)  

Detects an archive format and provides other related information.

```csharp
[Obsolete("Use static methods of ArchiveInstanceInfo class instead.")]
public sealed class ArchiveFormatDetector
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ArchiveFormatDetector](/zip/aspose.zip.archiveinfo.archiveformatdetector)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_ArchiveInfo_ArchiveFormatDetector__ctor"></a> ArchiveFormatDetector\(\)

Initializes a new instance of the Aspose.Zip.ArchiveInfo.ArchiveFormatDetector class.

```csharp
[Obsolete("Use static methods of ArchiveInstanceInfo class instead.")]
public ArchiveFormatDetector()
```

## Methods

### <a id="Aspose_Zip_ArchiveInfo_ArchiveFormatDetector_GetFormatInfo_System_String_"></a> GetFormatInfo\(string\)

Gets format info.

```csharp
[Obsolete("Use static methods of ArchiveInstanceInfo class instead.")]
public ArchiveFormatInfo GetFormatInfo(string fileName)
```

#### Parameters

`fileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

The filename of the archive file.

#### Returns

 [ArchiveFormatInfo](/zip/aspose.zip.archiveinfo.archiveformatinfo)

Information about archive format or null if a format was not detected.

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

### <a id="Aspose_Zip_ArchiveInfo_ArchiveFormatDetector_GetFormatInfo_System_IO_Stream_"></a> GetFormatInfo\(Stream\)

Gets format info.

```csharp
[Obsolete("Use static methods of ArchiveInstanceInfo class instead.")]
public ArchiveFormatInfo GetFormatInfo(Stream stream)
```

#### Parameters

`stream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The stream of the archive file.

#### Returns

 [ArchiveFormatInfo](/zip/aspose.zip.archiveinfo.archiveformatinfo)

Information about archive format or null if a format was not detected.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">stream</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">stream</code> is not seekable.
