---
linkTitle: "Class LzipArchiveSettings"
title: "Class LzipArchiveSettings"
description: "The class contains setting of a particular lzip archive."
summary: "The class contains setting of a particular lzip archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Lzip](/zip/aspose.zip.lzip)  
Assembly: Aspose.Zip.dll (25.12.0)  

The class contains setting of a particular lzip archive.

```csharp
public class LzipArchiveSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[LzipArchiveSettings](/zip/aspose.zip.lzip.lziparchivesettings)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Lzip_LzipArchiveSettings__ctor_System_Int32_System_Int32_"></a> LzipArchiveSettings\(int, int\)

Initializes a new instance of the Aspose.Zip.Lzip.LzipArchiveSettings with particular dictionary size.

```csharp
public LzipArchiveSettings(int dictionarySize, int maxMemberSize = 62914560)
```

#### Parameters

`dictionarySize` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Dictionary size for LZMA compression in bytes.

`maxMemberSize` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Maximum size of one member in lzip archive presented in bytes. The default value is 60 MB.

## Properties

### <a id="Aspose_Zip_Lzip_LzipArchiveSettings_CompressionThreads"></a> CompressionThreads

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

The number of threads is more than 100.

### <a id="Aspose_Zip_Lzip_LzipArchiveSettings_DictionarySize"></a> DictionarySize

Gets the size of dictionary which used by LZMA compression.

```csharp
public int DictionarySize { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

### <a id="Aspose_Zip_Lzip_LzipArchiveSettings_FastSpeed"></a> FastSpeed

Gets the instance of the Aspose.Zip.Lzip.LzipArchiveSettings class
with dictionary size equals to 1 megabyte in LZMA filter.

```csharp
public static LzipArchiveSettings FastSpeed { get; }
```

#### Property Value

 [LzipArchiveSettings](/zip/aspose.zip.lzip.lziparchivesettings)

### <a id="Aspose_Zip_Lzip_LzipArchiveSettings_FastestSpeed"></a> FastestSpeed

Gets the instance of the Aspose.Zip.Lzip.LzipArchiveSettings class
with dictionary size equals to 65536 bytes in LZMA filter.

```csharp
public static LzipArchiveSettings FastestSpeed { get; }
```

#### Property Value

 [LzipArchiveSettings](/zip/aspose.zip.lzip.lziparchivesettings)

### <a id="Aspose_Zip_Lzip_LzipArchiveSettings_HighCompression"></a> HighCompression

Gets the instance of the Aspose.Zip.Lzip.LzipArchiveSettings class
with dictionary size equals to 32 megabytes in LZMA filter.

```csharp
public static LzipArchiveSettings HighCompression { get; }
```

#### Property Value

 [LzipArchiveSettings](/zip/aspose.zip.lzip.lziparchivesettings)

### <a id="Aspose_Zip_Lzip_LzipArchiveSettings_MaxMemberSize"></a> MaxMemberSize

Gets the maximum size of one member in lzip archive presented in bytes.

```csharp
public long MaxMemberSize { get; }
```

#### Property Value

 [long](https://learn.microsoft.com/dotnet/api/system.int64)

### <a id="Aspose_Zip_Lzip_LzipArchiveSettings_MaximumCompression"></a> MaximumCompression

Gets the instance of the Aspose.Zip.Lzip.LzipArchiveSettings class
with dictionary size equals to 64 megabytes in LZMA filter.

```csharp
public static LzipArchiveSettings MaximumCompression { get; }
```

#### Property Value

 [LzipArchiveSettings](/zip/aspose.zip.lzip.lziparchivesettings)

### <a id="Aspose_Zip_Lzip_LzipArchiveSettings_Normal"></a> Normal

Gets the instance of the Aspose.Zip.Lzip.LzipArchiveSettings class
with dictionary size equals to 16 megabytes in LZMA filter.

```csharp
public static LzipArchiveSettings Normal { get; }
```

#### Property Value

 [LzipArchiveSettings](/zip/aspose.zip.lzip.lziparchivesettings)
