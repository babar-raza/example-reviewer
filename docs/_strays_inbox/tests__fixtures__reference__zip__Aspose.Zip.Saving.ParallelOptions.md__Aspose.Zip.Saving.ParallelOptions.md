---
linkTitle: "Class ParallelOptions"
title: "Class ParallelOptions"
description: "Options for parallel compression."
summary: "Options for parallel compression."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options for parallel compression.

```csharp
public class ParallelOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ParallelOptions](/zip/aspose.zip.saving.paralleloptions)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Examples


```csharp
using (var archive = new Archive())
{
    archive.CreateEntries("DirToCompress");
    archive.Save("archive.zip", new ArchiveSaveOptions() { ParallelOptions = new ParallelOptions { ParallelCompressInMemory = ParallelCompressionMode.Auto, AvailableMemorySize = 4000 } });
}
```

## Remarks

These options manage simultaneous compression by several CPU cores.

## Constructors

### <a id="Aspose_Zip_Saving_ParallelOptions__ctor"></a> ParallelOptions\(\)

```csharp
public ParallelOptions()
```

## Properties

### <a id="Aspose_Zip_Saving_ParallelOptions_AvailableMemorySize"></a> AvailableMemorySize

Gets or sets memory estimate in megabytes available to accomodate compressed entries without a swap to disk.
This value only makes sense if Aspose.Zip.Saving.ParallelOptions.ParallelCompressInMemory setting is in Aspose.Zip.Saving.ParallelCompressionMode.Auto mode.

```csharp
public int AvailableMemorySize { get; set; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Remarks

This value is used to calculate the biggest size of entry that can be compressed in parallel with others. All entries above the calculated threshold will be compressed sequentially.
It is safe to have Aspose.Zip.Saving.ParallelOptions.AvailableMemorySize property as big as free RAM and even bigger. By default, it is assumed you have at least 200MB per CPU core.

### <a id="Aspose_Zip_Saving_ParallelOptions_ParallelCompressInMemory"></a> ParallelCompressInMemory

Gets or sets value indicating how parallel approach to be used.

```csharp
public ParallelCompressionMode ParallelCompressInMemory { get; set; }
```

#### Property Value

 [ParallelCompressionMode](/zip/aspose.zip.saving.parallelcompressionmode)
