---
linkTitle: "Class SevenZipLZMA2CompressionSettings"
title: "Class SevenZipLZMA2CompressionSettings"
description: "Settings for LZMA2 compression method within 7z archive."
summary: "Settings for LZMA2 compression method within 7z archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for LZMA2 compression method within 7z archive.

```csharp
public class SevenZipLZMA2CompressionSettings : SevenZipCompressionSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[SevenZipCompressionSettings](/zip/aspose.zip.saving.sevenzipcompressionsettings) ← 
[SevenZipLZMA2CompressionSettings](/zip/aspose.zip.saving.sevenziplzma2compressionsettings)

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
        LZMA2 supports multiple runs of compressed LZMA data and uncompressed data.
        </p>
<p>See more: <a href="https://en.wikipedia.org/wiki/Lempel–Ziv–Markov_chain_algorithm">Lempel–Ziv–Markov chain algorithm</a></p>

## Constructors

### <a id="Aspose_Zip_Saving_SevenZipLZMA2CompressionSettings__ctor_System_Int32_"></a> SevenZipLZMA2CompressionSettings\(int\)

Instantiates settings for LZMA2 compression method within 7z archive.

```csharp
public SevenZipLZMA2CompressionSettings(int dictionarySize = 16777216)
```

#### Parameters

`dictionarySize` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The Size of history buffer, must be between 4096 and 1073741824.

#### Remarks

The bigger the dictionary, usually the better the compression ratio is - but dictionaries larger than the uncompressed data are a waste of RAM.

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

<code class="paramref">dictionarySize</code> is too big or too small.

### <a id="Aspose_Zip_Saving_SevenZipLZMA2CompressionSettings__ctor_System_Int32_System_Int32_"></a> SevenZipLZMA2CompressionSettings\(int, int\)

Instantiates settings for LZMA2 compression method within 7z archive.

```csharp
public SevenZipLZMA2CompressionSettings(int dictionarySize, int fastBytes = 32)
```

#### Parameters

`dictionarySize` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The size of history buffer, must be between 4096 and 1073741824.

`fastBytes` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Controls the number of fast bytes used by the LZMA2 compressors. A larger number of fast bytes can provide a better compression ratio at the expense of compression speed.

#### Remarks

The bigger the dictionary, usually the better the compression ratio is - but dictionaries larger than the uncompressed data are a waste of RAM.

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

<code class="paramref">dictionarySize</code> is too big or too small, or <code class="paramref">fastBytes</code> is too big or too small.

## Properties

### <a id="Aspose_Zip_Saving_SevenZipLZMA2CompressionSettings_CompressionThreads"></a> CompressionThreads

Gets or sets compression thread count. If the value is greater than 1, multithreading compression will be used.

```csharp
public int CompressionThreads { get; set; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Remarks

Do not set this number more than CPU cores.

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

The number of threads is higher than 32.

### <a id="Aspose_Zip_Saving_SevenZipLZMA2CompressionSettings_DictionarySize"></a> DictionarySize

Dictionary (history buffer) size indicates how many bytes of the recently processed uncompressed data are kept in memory.

```csharp
public int DictionarySize { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Remarks

The bigger the dictionary, usually the better the compression ratio is - but dictionaries larger than the uncompressed data are a waste of RAM.

### <a id="Aspose_Zip_Saving_SevenZipLZMA2CompressionSettings_FastBytes"></a> FastBytes

Gets the control number of fast bytes used by the LZMA2 compressor.

```csharp
public int FastBytes { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

### <a id="Aspose_Zip_Saving_SevenZipLZMA2CompressionSettings_Method"></a> Method

Gets compression or decompression method.

```csharp
public override SevenZipCompressionMethod Method { get; }
```

#### Property Value

 [SevenZipCompressionMethod](/zip/aspose.zip.saving.sevenzipcompressionmethod)
