---
linkTitle: "Class SevenZipBZip2CompressionSettings"
title: "Class SevenZipBZip2CompressionSettings"
description: "Settings for BZip2 compression method within 7z archive."
summary: "Settings for BZip2 compression method within 7z archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for BZip2 compression method within 7z archive.

```csharp
public class SevenZipBZip2CompressionSettings : SevenZipCompressionSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[SevenZipCompressionSettings](/zip/aspose.zip.saving.sevenzipcompressionsettings) ← 
[SevenZipBZip2CompressionSettings](/zip/aspose.zip.saving.sevenzipbzip2compressionsettings)

#### Inherited Members

[SevenZipCompressionSettings.Method](Aspose.Zip.Saving.SevenZipCompressionSettings.md\#Aspose\_Zip\_Saving\_SevenZipCompressionSettings\_Method), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Remarks

<p>
         Bzip2 compresses files using the Burrows-Wheeler block sorting text compression algorithm, and Huffman coding.
        </p>
<p>
        See more: https://en.wikipedia.org/wiki/Bzip2 </p>

## Constructors

### <a id="Aspose_Zip_Saving_SevenZipBZip2CompressionSettings__ctor_System_Int32_"></a> SevenZipBZip2CompressionSettings\(int\)

Initializes a new instance of the Aspose.Zip.Saving.SevenZipBZip2CompressionSettings class.

```csharp
public SevenZipBZip2CompressionSettings(int blockSize)
```

#### Parameters

`blockSize` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Block size in hundreds of kilobytes.

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

<code class="paramref">blockSize</code> is too big or too small.

### <a id="Aspose_Zip_Saving_SevenZipBZip2CompressionSettings__ctor"></a> SevenZipBZip2CompressionSettings\(\)

Initializes a new instance of the Aspose.Zip.Saving.SevenZipBZip2CompressionSettings class with default block size, equals to 9 hundred of kilobytes.

```csharp
public SevenZipBZip2CompressionSettings()
```

## Properties

### <a id="Aspose_Zip_Saving_SevenZipBZip2CompressionSettings_BlockSize"></a> BlockSize

Block size in hundreds of kilobytes.

```csharp
public int BlockSize { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

### <a id="Aspose_Zip_Saving_SevenZipBZip2CompressionSettings_Method"></a> Method

Gets compression or decompression method.

```csharp
public override SevenZipCompressionMethod Method { get; }
```

#### Property Value

 [SevenZipCompressionMethod](/zip/aspose.zip.saving.sevenzipcompressionmethod)
