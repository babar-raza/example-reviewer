---
linkTitle: "Class Bzip2CompressionSettings"
title: "Class Bzip2CompressionSettings"
description: "Settings for Bzip2 compression within a ZIP archive."
summary: "Settings for Bzip2 compression within a ZIP archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for Bzip2 compression within a ZIP archive.

```csharp
public class Bzip2CompressionSettings : CompressionSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[CompressionSettings](/zip/aspose.zip.saving.compressionsettings) ← 
[Bzip2CompressionSettings](/zip/aspose.zip.saving.bzip2compressionsettings)

#### Inherited Members

[CompressionSettings.Bzip2](Aspose.Zip.Saving.CompressionSettings.md\#Aspose\_Zip\_Saving\_CompressionSettings\_Bzip2), 
[CompressionSettings.Deflate](Aspose.Zip.Saving.CompressionSettings.md\#Aspose\_Zip\_Saving\_CompressionSettings\_Deflate), 
[CompressionSettings.EnhancedDeflate](Aspose.Zip.Saving.CompressionSettings.md\#Aspose\_Zip\_Saving\_CompressionSettings\_EnhancedDeflate), 
[CompressionSettings.Store](Aspose.Zip.Saving.CompressionSettings.md\#Aspose\_Zip\_Saving\_CompressionSettings\_Store), 
[CompressionSettings.Lzma](Aspose.Zip.Saving.CompressionSettings.md\#Aspose\_Zip\_Saving\_CompressionSettings\_Lzma), 
[CompressionSettings.Xz](Aspose.Zip.Saving.CompressionSettings.md\#Aspose\_Zip\_Saving\_CompressionSettings\_Xz), 
[CompressionSettings.PPMd](Aspose.Zip.Saving.CompressionSettings.md\#Aspose\_Zip\_Saving\_CompressionSettings\_PPMd), 
[CompressionSettings.Zstd](Aspose.Zip.Saving.CompressionSettings.md\#Aspose\_Zip\_Saving\_CompressionSettings\_Zstd), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Remarks

bzip2 compresses files using the Burrows-Wheeler block sorting text compression algorithm, and Huffman coding.

## Constructors

### <a id="Aspose_Zip_Saving_Bzip2CompressionSettings__ctor_System_Int32_"></a> Bzip2CompressionSettings\(int\)

Initializes a new instance of the Aspose.Zip.Saving.Bzip2CompressionSettings class.

```csharp
public Bzip2CompressionSettings(int blockSize)
```

#### Parameters

`blockSize` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Block size in hundreds of kilobytes.

#### Examples


```csharp
using (Archive archive = new Archive(new ArchiveEntrySettings(new Bzip2CompressionSettings(1))))
{
    archive.CreateEntry("data.bin", "data.bin");
    archive.Save(zipFile);
}
```

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

Block size is not between 1 and 9.

### <a id="Aspose_Zip_Saving_Bzip2CompressionSettings__ctor"></a> Bzip2CompressionSettings\(\)

Initializes a new instance of the Aspose.Zip.Saving.Bzip2CompressionSettings class with default block size, equals to 9 hundred of kilobytes.

```csharp
public Bzip2CompressionSettings()
```

#### Examples


```csharp
using (Archive archive = new Archive(new ArchiveEntrySettings(new Bzip2CompressionSettings())))
{
    archive.CreateEntry("data.bin", "data.bin");
    archive.Save(zipFile);
}
```

## Properties

### <a id="Aspose_Zip_Saving_Bzip2CompressionSettings_BlockSize"></a> BlockSize

Block size in hundreds of kilobytes.

```csharp
public int BlockSize { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)
