---
linkTitle: "Class PPMdCompressionSettings"
title: "Class PPMdCompressionSettings"
description: "Settings for PPMd compression within a ZIP archive."
summary: "Settings for PPMd compression within a ZIP archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for PPMd compression within a ZIP archive.

```csharp
public class PPMdCompressionSettings : CompressionSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[CompressionSettings](/zip/aspose.zip.saving.compressionsettings) ← 
[PPMdCompressionSettings](/zip/aspose.zip.saving.ppmdcompressionsettings)

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
        PPMd is a data compression algorithm developed by Dmitry Shkarin.
        This algorithm is based on predictive phrase matching on multiple order contexts.
        </p>

## Constructors

### <a id="Aspose_Zip_Saving_PPMdCompressionSettings__ctor_System_Int32_System_Int32_"></a> PPMdCompressionSettings\(int, int\)

Initializes a new instance of the Aspose.Zip.Saving.PPMdCompressionSettings class.

```csharp
public PPMdCompressionSettings(int modelOrder, int suballocatorSize)
```

#### Parameters

`modelOrder` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Order of the model.

`suballocatorSize` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Memory size in MB suballocator may consume.

#### Examples


```csharp
using (Archive archive = new Archive(new ArchiveEntrySettings(new PPMdCompressionSettings(4, 10))))
{
    archive.CreateEntry("data.bin", "data.bin");                   
    archive.Save(zipFile);
}
```

#### Remarks

<p>Bigger model orders almost surely results in better compression and surely more memory and CPU usage.</p>
<p>The PPMd algorithm might need a lot of memory, especially when used on large files and/or used with large model order.
        If ppmd needs more memory than you give it, the compression will be worse.</p>

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

<code class="paramref">modelOrder</code> is not between 2 and 16. - or - <code class="paramref">suballocatorSize</code> is not between 1 and 256.

### <a id="Aspose_Zip_Saving_PPMdCompressionSettings__ctor"></a> PPMdCompressionSettings\(\)

Initializes a new instance of the Aspose.Zip.Saving.PPMdCompressionSettings class with default model order and sub-allocator size.

```csharp
public PPMdCompressionSettings()
```

#### Examples


```csharp
using (Archive archive = new Archive(new ArchiveEntrySettings(new PPMdCompressionSettings())))
{
    archive.CreateEntry("data.bin", "data.bin");                   
    archive.Save(zipFile);
}
```

#### Remarks

The default model order is 8, and the sub-allocator size is 50MB.

## Properties

### <a id="Aspose_Zip_Saving_PPMdCompressionSettings_ModelOrder"></a> ModelOrder

Gets the order of the model.

```csharp
public int ModelOrder { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

### <a id="Aspose_Zip_Saving_PPMdCompressionSettings_SuballocatorSize"></a> SuballocatorSize

Gets the sub-allocator size in MB.

```csharp
public int SuballocatorSize { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)
