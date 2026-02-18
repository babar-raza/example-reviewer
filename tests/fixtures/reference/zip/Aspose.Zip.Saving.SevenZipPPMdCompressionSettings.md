---
linkTitle: "Class SevenZipPPMdCompressionSettings"
title: "Class SevenZipPPMdCompressionSettings"
description: "Settings for PPMd compression method within 7z archive."
summary: "Settings for PPMd compression method within 7z archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for PPMd compression method within 7z archive.

```csharp
public sealed class SevenZipPPMdCompressionSettings : SevenZipCompressionSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[SevenZipCompressionSettings](/zip/aspose.zip.saving.sevenzipcompressionsettings) ← 
[SevenZipPPMdCompressionSettings](/zip/aspose.zip.saving.sevenzipppmdcompressionsettings)

#### Inherited Members

[SevenZipCompressionSettings.Method](Aspose.Zip.Saving.SevenZipCompressionSettings.md\#Aspose\_Zip\_Saving\_SevenZipCompressionSettings\_Method), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Saving_SevenZipPPMdCompressionSettings__ctor_System_Byte_System_Int32_"></a> SevenZipPPMdCompressionSettings\(byte, int\)

Instantiates settings for PPMd compression method within 7z archive.

```csharp
public SevenZipPPMdCompressionSettings(byte maxOrder, int suballocatorSize)
```

#### Parameters

`maxOrder` [byte](https://learn.microsoft.com/dotnet/api/system.byte)

Maximum order.

`suballocatorSize` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Memory size in MB suballocator may consume.

#### Examples


```csharp
using (SevenZipArchive archive = new SevenZipArchive(new SevenZipEntrySettings(new SevenZipPPMdCompressionSettings(4, 32))))
{
    archive.CreateEntry("data.bin", "data.bin");                        
    archive.Save(sevenZipFile);
 }
```

#### Remarks

<p>Bigger model orders almost surely results in better compression and surely more memory and CPU usage.</p>
<p>The PPMd algorithm might need a lot of memory, especially when used on large files and/or used with large model order.
        If ppmd needs more memory than you give it, the compression will be worse.</p>

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

<code class="paramref">maxOrder</code> is not between 2 and 32, or <code class="paramref">suballocatorSize</code> is not between 1 and 1024.

### <a id="Aspose_Zip_Saving_SevenZipPPMdCompressionSettings__ctor"></a> SevenZipPPMdCompressionSettings\(\)

Instantiates settings for PPMd compression method within 7z archive with default model order and sub-allocator size.

```csharp
public SevenZipPPMdCompressionSettings()
```

#### Examples


```csharp
using (SevenZipArchive archive = new SevenZipArchive(new SevenZipEntrySettings(new SevenZipPPMdCompressionSettings())))
{
    archive.CreateEntry("data.bin", "data.bin");                        
    archive.Save(sevenZipFile);
 }
```

#### Remarks

The default model order is 6 and sub-allocator size is 16MB.

## Properties

### <a id="Aspose_Zip_Saving_SevenZipPPMdCompressionSettings_MaxOrder"></a> MaxOrder

Gets the maximum order.

```csharp
public byte MaxOrder { get; }
```

#### Property Value

 [byte](https://learn.microsoft.com/dotnet/api/system.byte)

### <a id="Aspose_Zip_Saving_SevenZipPPMdCompressionSettings_Method"></a> Method

Gets compression or decompression method.

```csharp
public override SevenZipCompressionMethod Method { get; }
```

#### Property Value

 [SevenZipCompressionMethod](/zip/aspose.zip.saving.sevenzipcompressionmethod)

### <a id="Aspose_Zip_Saving_SevenZipPPMdCompressionSettings_SuballocatorSize"></a> SuballocatorSize

Gets the sub-allocator size in MB.

```csharp
public int SuballocatorSize { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)
