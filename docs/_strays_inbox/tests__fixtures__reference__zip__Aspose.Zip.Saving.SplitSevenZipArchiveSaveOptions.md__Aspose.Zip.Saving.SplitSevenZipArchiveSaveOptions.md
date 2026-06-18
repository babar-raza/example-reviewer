---
linkTitle: "Class SplitSevenZipArchiveSaveOptions"
title: "Class SplitSevenZipArchiveSaveOptions"
description: "Options for saving a multi-volume 7-zip archive."
summary: "Options for saving a multi-volume 7-zip archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options for saving a multi-volume 7-zip archive.

```csharp
public class SplitSevenZipArchiveSaveOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[SplitSevenZipArchiveSaveOptions](/zip/aspose.zip.saving.splitsevenziparchivesaveoptions)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Saving_SplitSevenZipArchiveSaveOptions__ctor_System_String_System_UInt32_"></a> SplitSevenZipArchiveSaveOptions\(string, uint\)

Instantiates settings for saving a multi-volume 7z archive.

```csharp
public SplitSevenZipArchiveSaveOptions(string fileName, uint segmentSize)
```

#### Parameters

`fileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

Name for volumes. May be with or without .7z extension.

`segmentSize` [uint](https://learn.microsoft.com/dotnet/api/system.uint32)

Size of volume.

#### Remarks

<p>Some volumes may be less than <code class="paramref">segmentSize</code>. In most cases, the last segment will be less but rarely regular segments might be too.</p>
<p>Names of files will be as follows: <code class="paramref">fileName</code>.7z.001, <code class="paramref">fileName</code>.7z.002, ...,  <code class="paramref">fileName</code>.7z.(n).</p>

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

<code class="paramref">segmentSize</code> is less than 100.

## Properties

### <a id="Aspose_Zip_Saving_SplitSevenZipArchiveSaveOptions_FileName"></a> FileName

Gets the name of segments without extension.

```csharp
public string FileName { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_Saving_SplitSevenZipArchiveSaveOptions_SegmentSize"></a> SegmentSize

Gets the size of the segment.

```csharp
public uint SegmentSize { get; }
```

#### Property Value

 [uint](https://learn.microsoft.com/dotnet/api/system.uint32)
