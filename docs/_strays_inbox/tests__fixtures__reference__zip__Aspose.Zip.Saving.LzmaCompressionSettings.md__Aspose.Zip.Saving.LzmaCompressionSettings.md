---
linkTitle: "Class LzmaCompressionSettings"
title: "Class LzmaCompressionSettings"
description: "Settings for LZMA compression within a ZIP archive."
summary: "Settings for LZMA compression within a ZIP archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for LZMA compression within a ZIP archive.

```csharp
public class LzmaCompressionSettings : CompressionSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[CompressionSettings](/zip/aspose.zip.saving.compressionsettings) ← 
[LzmaCompressionSettings](/zip/aspose.zip.saving.lzmacompressionsettings)

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

<p>
        The Lempel–Ziv–Markov chain algorithm (LZMA) is an algorithm used to perform lossless data compression.
        This algorithm uses a dictionary compression scheme somewhat similar to the LZ77 algorithm and features a high compression ratio and a variable compression-dictionary size.
        </p>
<p>See more: <a href="https://en.wikipedia.org/wiki/Lempel–Ziv–Markov_chain_algorithm">Lempel–Ziv–Markov chain algorithm</a></p>

## Constructors

### <a id="Aspose_Zip_Saving_LzmaCompressionSettings__ctor"></a> LzmaCompressionSettings\(\)

Initializes a new instance of the Aspose.Zip.Saving.LzmaCompressionSettings class with default parameters.

```csharp
public LzmaCompressionSettings()
```

#### Examples


```csharp
using (Archive archive = new Archive(new ArchiveEntrySettings(new LzmaCompressionSettings())))
{
    archive.CreateEntry("data.bin", "data.bin");
    archive.Save(zipFile);
}
```

### <a id="Aspose_Zip_Saving_LzmaCompressionSettings__ctor_System_Int32_System_Int32_System_Int32_"></a> LzmaCompressionSettings\(int, int, int\)

Initializes a new instance of the Aspose.Zip.Saving.LzmaCompressionSettings class with specified dictionary size, number of fast bytes and number of literal context bits.

```csharp
public LzmaCompressionSettings(int dictionarySize, int numberOfFastBytes, int literalContextBits)
```

#### Parameters

`dictionarySize` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Dictionary (history buffer) size in bytes. Must be between 4096 and 1073741824.

`numberOfFastBytes` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The number of bytes used for fast match searching in the LZMA algorithm. Can be in the range from 5 to 273.

`literalContextBits` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Sets the number of literal context bits (high bits of previous literal). It can be in range from 0 to 8.

### <a id="Aspose_Zip_Saving_LzmaCompressionSettings__ctor_System_Int32_"></a> LzmaCompressionSettings\(int\)

Initializes a new instance of the Aspose.Zip.Saving.LzmaCompressionSettings class with specified dictionary size, default number of fast bytes equal to 32 and number of literal context bits equal to 3.

```csharp
public LzmaCompressionSettings(int dictionarySize)
```

#### Parameters

`dictionarySize` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Dictionary (history buffer) size in bytes. Must be between 4096 and 1073741824.

## Properties

### <a id="Aspose_Zip_Saving_LzmaCompressionSettings_DictionarySize"></a> DictionarySize

Dictionary (history buffer) size indicates how many bytes of the recently processed uncompressed data are kept in memory.

```csharp
public int DictionarySize { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Remarks

The bigger the dictionary, usually the better the compression ratio is - but dictionaries larger than the uncompressed data are a waste of RAM.

### <a id="Aspose_Zip_Saving_LzmaCompressionSettings_LiteralContextBits"></a> LiteralContextBits

Gets the number of literal context bits.

```csharp
public int LiteralContextBits { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Remarks

Literal Context Bits define how many of the most significant bits of the previous uncompressed byte are used to predict the bits of the next literal byte. Must be from 0 to 8.

### <a id="Aspose_Zip_Saving_LzmaCompressionSettings_NumberOfFastBytes"></a> NumberOfFastBytes

Gets the number of bytes used for fast match searching in the LZMA algorithm.

```csharp
public int NumberOfFastBytes { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Remarks

A higher value allows the compressor to search longer matches, which can improve the compression ratio slightly but slows down compression.
