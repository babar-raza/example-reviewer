---
linkTitle: "Class XzArchiveSettings"
title: "Class XzArchiveSettings"
description: "The class contains a set of setting particular xz archive."
summary: "The class contains a set of setting particular xz archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Xz.Settings](/zip/aspose.zip.xz.settings)  
Assembly: Aspose.Zip.dll (25.12.0)  

The class contains a set of setting particular xz archive.

```csharp
public class XzArchiveSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[XzArchiveSettings](/zip/aspose.zip.xz.settings.xzarchivesettings)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Xz_Settings_XzArchiveSettings__ctor"></a> XzArchiveSettings\(\)

Initializes a new instance of the Aspose.Zip.Xz.Settings.XzArchiveSettings class using single LZMA2 compression.

```csharp
public XzArchiveSettings()
```

#### Remarks

Default dictionary in LZMA2 filter size equals to 16 megabytes, default block size equals to 64 megabytes, a default checksum type is CRC32.

### <a id="Aspose_Zip_Xz_Settings_XzArchiveSettings__ctor_Aspose_Zip_Xz_Settings_XzFilterSettings___System_Int64_Aspose_Zip_Xz_Settings_XzCheckType_"></a> XzArchiveSettings\(XzFilterSettings\[\], long, XzCheckType\)

Initializes a new instance of the Aspose.Zip.Xz.Settings.XzArchiveSettings class with custom parameters.

```csharp
public XzArchiveSettings(XzFilterSettings[] filters, long blockSize, XzCheckType checkType)
```

#### Parameters

`filters` [XzFilterSettings](/zip/aspose.zip.xz.settings.xzfiltersettings)\[\]

Filters (compressors) to be sequentially applied to create Aspose.Zip.Xz.XzArchive. It can be either single Aspose.Zip.Xz.Settings.XzLZMA2FilterSettings 
            or pair of Aspose.Zip.Xz.Settings.XzBcjX86FilterSettings and Aspose.Zip.Xz.Settings.XzLZMA2FilterSettings

`blockSize` [long](https://learn.microsoft.com/dotnet/api/system.int64)

Size xz archive block.

`checkType` [XzCheckType](/zip/aspose.zip.xz.settings.xzchecktype)

Type of checksum calculation for uncompressed data.

#### Examples


```csharp
using (FileStream xzFile = File.Open("archive.xz", FileMode.Create))
{
    XzLZMA2FilterSettings filter = new XzLZMA2FilterSettings(5242880);
    XzArchiveSettings settings = new XzArchiveSettings(new XzFilterSettings[] {filter}, 10485760, XzCheckType.Crc32);
    using (var archive = new XzArchive(settings))
    {
        archive.SetSource("data.bin");
        archive.Save(xzFile);
     }
}
```

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

<code class="paramref">blockSize</code> is negative.

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">filters</code> is null

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">filters</code> has less than one or more than two filters, or last filter is not Aspose.Zip.Xz.Settings.XzLZMA2FilterSettings.

## Properties

### <a id="Aspose_Zip_Xz_Settings_XzArchiveSettings_CompressionThreads"></a> CompressionThreads

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

### <a id="Aspose_Zip_Xz_Settings_XzArchiveSettings_FastSpeed"></a> FastSpeed

Gets the instance of the Aspose.Zip.Xz.Settings.XzArchiveSettings class
with dictionary size equals to 1 megabyte in LZMA2 filter, block size equals to 4 megabytes and CRC32 checksum.

```csharp
public static XzArchiveSettings FastSpeed { get; }
```

#### Property Value

 [XzArchiveSettings](/zip/aspose.zip.xz.settings.xzarchivesettings)

### <a id="Aspose_Zip_Xz_Settings_XzArchiveSettings_FastestSpeed"></a> FastestSpeed

Gets the instance of the Aspose.Zip.Xz.Settings.XzArchiveSettings class
with dictionary size equals to 65536 bytes in LZMA2 filter, block size equals to 1 megabyte and CRC32 checksum.

```csharp
public static XzArchiveSettings FastestSpeed { get; }
```

#### Property Value

 [XzArchiveSettings](/zip/aspose.zip.xz.settings.xzarchivesettings)

### <a id="Aspose_Zip_Xz_Settings_XzArchiveSettings_HighCompression"></a> HighCompression

Gets the instance of the Aspose.Zip.Xz.Settings.XzArchiveSettings class
with dictionary size equals to 32 megabytes in LZMA2 filter, block size equals to 128 megabytes and CRC32 checksum.

```csharp
public static XzArchiveSettings HighCompression { get; }
```

#### Property Value

 [XzArchiveSettings](/zip/aspose.zip.xz.settings.xzarchivesettings)

### <a id="Aspose_Zip_Xz_Settings_XzArchiveSettings_MaximumCompression"></a> MaximumCompression

Gets the instance of the Aspose.Zip.Xz.Settings.XzArchiveSettings class
with dictionary size equals to 64 megabytes in LZMA2 filter, block size equals to 256 megabytes and CRC32 checksum.

```csharp
public static XzArchiveSettings MaximumCompression { get; }
```

#### Property Value

 [XzArchiveSettings](/zip/aspose.zip.xz.settings.xzarchivesettings)

### <a id="Aspose_Zip_Xz_Settings_XzArchiveSettings_Normal"></a> Normal

Gets the instance of the Aspose.Zip.Xz.Settings.XzArchiveSettings class
with dictionary size equals to 16 megabytes in LZMA2 filter, block size equals to 64 megabytes and CRC32 checksum.

```csharp
public static XzArchiveSettings Normal { get; }
```

#### Property Value

 [XzArchiveSettings](/zip/aspose.zip.xz.settings.xzarchivesettings)
