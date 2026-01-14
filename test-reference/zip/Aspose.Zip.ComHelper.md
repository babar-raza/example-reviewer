---
linkTitle: "Class ComHelper"
title: "Class ComHelper"
description: "Provides methods for COM clients to load archives into Aspose.Zip."
summary: "Provides methods for COM clients to load archives into Aspose.Zip."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip](/zip/)  
Assembly: Aspose.Zip.dll (25.12.0)  

Provides methods for COM clients to load archives into Aspose.Zip.

```csharp
public class ComHelper
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ComHelper](/zip/aspose.zip.comhelper)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Remarks

Use the ComHelper class to load an archive from a file or stream.
Particular classes provide a default constructor to create a new archive
and also provides overloaded constructors to load an archive from a file or stream.
If you are using Aspose.Zip from a .NET application, you can use all the archive
constructors directly, but if you are using Aspose.Zip from a COM application,
only the default archive constructor is available.

## Constructors

### <a id="Aspose_Zip_ComHelper__ctor"></a> ComHelper\(\)

Initializes a new instance of this class.

```csharp
public ComHelper()
```

## Methods

### <a id="Aspose_Zip_ComHelper_OpenBzip2_System_IO_Stream_"></a> OpenBzip2\(Stream\)

Allows a COM application to load a bzip2 archive from a stream.

```csharp
public Bzip2Archive OpenBzip2(Stream stream)
```

#### Parameters

`stream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

A .NET stream object that contains the archive to load.

#### Returns

 [Bzip2Archive](/zip/aspose.zip.bzip2.bzip2archive)

A Aspose.Zip.Bzip2.Bzip2Archive object that represents the archive.

### <a id="Aspose_Zip_ComHelper_OpenBzip2_System_String_"></a> OpenBzip2\(string\)

Allows a COM application to load a bzip2 archive from a file.

```csharp
public Bzip2Archive OpenBzip2(string fileName)
```

#### Parameters

`fileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

Filename of the archive to load.

#### Returns

 [Bzip2Archive](/zip/aspose.zip.bzip2.bzip2archive)

A Aspose.Zip.Bzip2.Bzip2Archive object that represents the archive.

### <a id="Aspose_Zip_ComHelper_OpenGzip_System_IO_Stream_"></a> OpenGzip\(Stream\)

Allows a COM application to load a gzip archive from a stream.

```csharp
public GzipArchive OpenGzip(Stream stream)
```

#### Parameters

`stream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

A .NET stream object that contains the archive to load.

#### Returns

 [GzipArchive](/zip/aspose.zip.gzip.gziparchive)

A Aspose.Zip.Gzip.GzipArchive object that represents the archive.

### <a id="Aspose_Zip_ComHelper_OpenGzip_System_String_"></a> OpenGzip\(string\)

Allows a COM application to load a gzip archive from a file.

```csharp
public GzipArchive OpenGzip(string fileName)
```

#### Parameters

`fileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

Filename of the archive to load.

#### Returns

 [GzipArchive](/zip/aspose.zip.gzip.gziparchive)

A Aspose.Zip.Gzip.GzipArchive object that represents the archive.

### <a id="Aspose_Zip_ComHelper_OpenRar_System_IO_Stream_"></a> OpenRar\(Stream\)

Allows a COM application to load a rar archive from a stream.

```csharp
public RarArchive OpenRar(Stream stream)
```

#### Parameters

`stream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

A .NET stream object that contains the archive to load.

#### Returns

 [RarArchive](/zip/aspose.zip.rar.rararchive)

A Aspose.Zip.Rar.RarArchive object that represents the archive.

### <a id="Aspose_Zip_ComHelper_OpenRar_System_String_"></a> OpenRar\(string\)

Allows a COM application to load a rar archive from a file.

```csharp
public RarArchive OpenRar(string fileName)
```

#### Parameters

`fileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

Filename of the archive to load.

#### Returns

 [RarArchive](/zip/aspose.zip.rar.rararchive)

A Aspose.Zip.Rar.RarArchive object that represents the archive.

### <a id="Aspose_Zip_ComHelper_OpenZip_System_IO_Stream_"></a> OpenZip\(Stream\)

Allows a COM application to load a ZIP archive from a stream.

```csharp
public Archive OpenZip(Stream stream)
```

#### Parameters

`stream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

A .NET stream object that contains the archive to load.

#### Returns

 [Archive](/zip/aspose.zip.archive)

A Aspose.Zip.Archive object that represents the archive.

### <a id="Aspose_Zip_ComHelper_OpenZip_System_String_"></a> OpenZip\(string\)

Allows a COM application to load a ZIP archive from a file.

```csharp
public Archive OpenZip(string fileName)
```

#### Parameters

`fileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

Filename of the archive to load.

#### Returns

 [Archive](/zip/aspose.zip.archive)

A Aspose.Zip.Archive object that represents the archive.
