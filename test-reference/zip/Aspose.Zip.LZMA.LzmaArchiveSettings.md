---
linkTitle: "Class LzmaArchiveSettings"
title: "Class LzmaArchiveSettings"
description: "Settings for lzma archive."
summary: "Settings for lzma archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.LZMA](/zip/aspose.zip.lzma)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for lzma archive.

```csharp
public class LzmaArchiveSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[LzmaArchiveSettings](/zip/aspose.zip.lzma.lzmaarchivesettings)

#### Inherited Members

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

### <a id="Aspose_Zip_LZMA_LzmaArchiveSettings__ctor"></a> LzmaArchiveSettings\(\)

Initializes a new instance of the Aspose.Zip.LZMA.LzmaArchiveSettings class with default dictionary size, equals to 16 megabytes, number of fast bytes equal to 32 and literal context bits equal to 3.

```csharp
public LzmaArchiveSettings()
```

#### Examples


```csharp
using (LzmaArchive archive = new LzmaArchive(new LzmaArchiveSettings() { DictionarySize = 1048576 })
{
    archive.SetSource("data.bin");
    archive.Save(lzmaFile);
}
```

## Properties

### <a id="Aspose_Zip_LZMA_LzmaArchiveSettings_DictionarySize"></a> DictionarySize

Dictionary (history buffer) size indicates how many bytes of the recently processed uncompressed data are kept in memory.
If not set, will be chosen accordingly to entry size.

```csharp
public int DictionarySize { get; set; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Remarks

The bigger the dictionary, usually the better the compression ratio is - but dictionaries larger than the uncompressed data are a waste of RAM.
            <p>The disctionary size of LZMA archive must be either a power of two (2^n) or three times a power of two (3*2^n).</p>

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

The value is too small ot too big.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

The value is not a power of two or three times a power of two.

### <a id="Aspose_Zip_LZMA_LzmaArchiveSettings_LiteralContextBits"></a> LiteralContextBits

Gets or sets the number of literal context bits.

```csharp
public int LiteralContextBits { get; set; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Remarks

Literal Context Bits define how many of the most significant bits of the previous uncompressed byte are used to predict the bits of the next literal byte. Must be from 0 to 8.

### <a id="Aspose_Zip_LZMA_LzmaArchiveSettings_NumberOfFastBytes"></a> NumberOfFastBytes

Gets or sets the number of bytes used for fast match searching in the LZMA algorithm.

```csharp
public int NumberOfFastBytes { get; set; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Remarks

A higher value allows the compressor to search longer matches, which can improve the compression ratio slightly but slows down compression.

### <a id="Aspose_Zip_LZMA_LzmaArchiveSettings_CompressionProgressed"></a> CompressionProgressed

Raises when a portion of raw stream compressed.

```csharp
public event EventHandler<ProgressEventArgs> CompressionProgressed
```

#### Event Type

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[ProgressEventArgs](/zip/aspose.zip.progresseventargs)\>

#### Examples

`lzmaArchiveSettings.CompressionProgressed += (s, e) =&gt; { int percent = (int)((100 * (long)e.ProceededBytes) / entrySourceStream.Length); };`
