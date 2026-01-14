---
linkTitle: "Class SevenZipLZMACompressionSettings"
title: "Class SevenZipLZMACompressionSettings"
description: "Settings for LZMA compression method within 7z archive."
summary: "Settings for LZMA compression method within 7z archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for LZMA compression method within 7z archive.

```csharp
public class SevenZipLZMACompressionSettings : SevenZipCompressionSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[SevenZipCompressionSettings](/zip/aspose.zip.saving.sevenzipcompressionsettings) ← 
[SevenZipLZMACompressionSettings](/zip/aspose.zip.saving.sevenziplzmacompressionsettings)

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
        The Lempel–Ziv–Markov chain algorithm (LZMA) is an algorithm used to perform lossless data compression.
        This algorithm uses a dictionary compression scheme somewhat similar to the LZ77 algorithm and features a high compression ratio and a variable compression-dictionary size.
        </p>
<p>See more: <a href="https://en.wikipedia.org/wiki/Lempel–Ziv–Markov_chain_algorithm">Lempel–Ziv–Markov chain algorithm</a></p>

## Constructors

### <a id="Aspose_Zip_Saving_SevenZipLZMACompressionSettings__ctor"></a> SevenZipLZMACompressionSettings\(\)

Initializes a new instance of the Aspose.Zip.Saving.SevenZipLZMACompressionSettings class with default parameters.

```csharp
public SevenZipLZMACompressionSettings()
```

#### Examples


```csharp
using (var archive = new SevenZipArchive(new SevenZipEntrySettings(new SevenZipLZMACompressionSettings())))
{
    archive.CreateEntry("data.bin", "data.bin");
    archive.Save("result.7z");
}
```

### <a id="Aspose_Zip_Saving_SevenZipLZMACompressionSettings__ctor_System_Int32_System_Int32_System_Int32_"></a> SevenZipLZMACompressionSettings\(int, int, int\)

Initializes a new instance of the Aspose.Zip.Saving.SevenZipLZMACompressionSettings class with specified dictionary size, number of fast bytes and number of literal context bits.

```csharp
public SevenZipLZMACompressionSettings(int dictionarySize, int numberOfFastBytes, int literalContextBits)
```

#### Parameters

`dictionarySize` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Dictionary (history buffer) size in bytes. Must be between 4096 and 1073741824, or equal to zero for automatic detection based on entry size.

`numberOfFastBytes` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The number of bytes used for fast match searching in the LZMA algorithm. Can be in the range from 5 to 273.

`literalContextBits` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Sets the number of literal context bits (high bits of previous literal). It can be in range from 0 to 8.

### <a id="Aspose_Zip_Saving_SevenZipLZMACompressionSettings__ctor_System_Int32_"></a> SevenZipLZMACompressionSettings\(int\)

Initializes a new instance of the Aspose.Zip.Saving.SevenZipLZMACompressionSettings class with specified dictionary size, number of fast bytes equal to 32, number of literal context bits equal to 3.

```csharp
public SevenZipLZMACompressionSettings(int dictionarySize)
```

#### Parameters

`dictionarySize` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Dictionary (history buffer) size in bytes. Must be between 4096 and 1073741824, or equal to zero for automatic detection based on entry size.

## Properties

### <a id="Aspose_Zip_Saving_SevenZipLZMACompressionSettings_DictionarySize"></a> DictionarySize

Dictionary (history buffer) size indicates how many bytes of the recently processed uncompressed data is kept in memory.
If not set, will be chosen accordingly to entry size.  Must be between 4096 and 1073741824, or equal to zero for automatic detection based on entry size.

```csharp
public int DictionarySize { get; set; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Remarks

The bigger the dictionary, usually the better the compression ratio is - but dictionaries larger than the uncompressed data are a waste of RAM.

### <a id="Aspose_Zip_Saving_SevenZipLZMACompressionSettings_LiteralContextBits"></a> LiteralContextBits

Gets the number of literal context bits.

```csharp
public int LiteralContextBits { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Remarks

Literal Context Bits define how many of the most significant bits of the previous uncompressed byte are used to predict the bits of the next literal byte. Must be from 0 to 8.

### <a id="Aspose_Zip_Saving_SevenZipLZMACompressionSettings_Method"></a> Method

Gets compression or decompression method.

```csharp
public override SevenZipCompressionMethod Method { get; }
```

#### Property Value

 [SevenZipCompressionMethod](/zip/aspose.zip.saving.sevenzipcompressionmethod)

### <a id="Aspose_Zip_Saving_SevenZipLZMACompressionSettings_NumberOfFastBytes"></a> NumberOfFastBytes

Gets the number of bytes used for fast match searching in the LZMA algorithm.

```csharp
public int NumberOfFastBytes { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Remarks

A higher value allows the compressor to search longer matches, which can improve the compression ratio slightly but slows down compression.
