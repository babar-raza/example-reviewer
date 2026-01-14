---
linkTitle: "Class XarBzip2CompressionSettings"
title: "Class XarBzip2CompressionSettings"
description: "Settings for Bzip2 compression method."
summary: "Settings for Bzip2 compression method."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Xar](/zip/aspose.zip.xar)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for Bzip2 compression method.

```csharp
public class XarBzip2CompressionSettings : XarCompressionSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[XarCompressionSettings](/zip/aspose.zip.xar.xarcompressionsettings) ← 
[XarBzip2CompressionSettings](/zip/aspose.zip.xar.xarbzip2compressionsettings)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Xar_XarBzip2CompressionSettings__ctor_System_Int32_"></a> XarBzip2CompressionSettings\(int\)

Initializes a new instance of the Aspose.Zip.Xar.XarBzip2CompressionSettings class.

```csharp
public XarBzip2CompressionSettings(int blockSize)
```

#### Parameters

`blockSize` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Block size in hundreds of kilobytes.

#### Examples


```csharp
using (XarArchive archive = new XarArchive())
{
    archive.CreateEntry("data.bin", "data.bin", new XarBzip2CompressionSettings(1));
    archive.Save("archive.xar");
}
```

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

Block size is not between 1 and 9.

### <a id="Aspose_Zip_Xar_XarBzip2CompressionSettings__ctor"></a> XarBzip2CompressionSettings\(\)

Initializes a new instance of the Aspose.Zip.Xar.XarBzip2CompressionSettings class with default block size, equals to 9 hundred of kilobytes.

```csharp
public XarBzip2CompressionSettings()
```

## Properties

### <a id="Aspose_Zip_Xar_XarBzip2CompressionSettings_BlockSize"></a> BlockSize

Block size in hundreds of kilobytes.

```csharp
public int BlockSize { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)
