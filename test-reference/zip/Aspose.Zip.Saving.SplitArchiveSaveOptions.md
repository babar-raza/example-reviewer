---
linkTitle: "Class SplitArchiveSaveOptions"
title: "Class SplitArchiveSaveOptions"
description: "Options for saving a multi-volume ZIP archive."
summary: "Options for saving a multi-volume ZIP archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options for saving a multi-volume ZIP archive.

```csharp
public class SplitArchiveSaveOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[SplitArchiveSaveOptions](/zip/aspose.zip.saving.splitarchivesaveoptions)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Saving_SplitArchiveSaveOptions__ctor_System_String_System_UInt32_"></a> SplitArchiveSaveOptions\(string, uint\)

Instantiates settings for saving a multi-volume ZIP archive.

```csharp
public SplitArchiveSaveOptions(string fileName, uint segmentSize)
```

#### Parameters

`fileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

Name for volumes. May be with or without .zip extension.

`segmentSize` [uint](https://learn.microsoft.com/dotnet/api/system.uint32)

Size of volume.

#### Remarks

<p>Some volumes may be less than <code class="paramref">segmentSize</code>. In most cases, the last segment will be less but rarely regular segments might be too.</p>
<p>Names of files will be as follows: <code class="paramref">fileName</code>.z01, <code class="paramref">fileName</code>.z02, ...,  <code class="paramref">fileName</code>.z(n-1),  <code class="paramref">fileName</code>.zip.</p>

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

Segment size is less than 65536 bytes.

## Properties

### <a id="Aspose_Zip_Saving_SplitArchiveSaveOptions_ArchiveComment"></a> ArchiveComment

Gets or sets optional comment for the Zip file.

```csharp
public string ArchiveComment { get; set; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_Saving_SplitArchiveSaveOptions_CloseEntrySource"></a> CloseEntrySource

Gets or sets a value indicating whether entries' sources should be closed right after an entry has been compressed.

```csharp
public bool CloseEntrySource { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_Saving_SplitArchiveSaveOptions_Encoding"></a> Encoding

Gets or sets encoding for converting file names and other strings to bytes.

```csharp
public Encoding Encoding { get; set; }
```

#### Property Value

 [Encoding](https://learn.microsoft.com/dotnet/api/system.text.encoding)

#### Remarks

If not set, code page 437 will be used.

### <a id="Aspose_Zip_Saving_SplitArchiveSaveOptions_EventsBag"></a> EventsBag

Gets or sets container of events raising on archive saving.

```csharp
public EventsBag EventsBag { get; set; }
```

#### Property Value

 [EventsBag](/zip/aspose.zip.saving.eventsbag)

### <a id="Aspose_Zip_Saving_SplitArchiveSaveOptions_FileName"></a> FileName

Gets the name of segments without extension.

```csharp
public string FileName { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_Saving_SplitArchiveSaveOptions_SegmentSize"></a> SegmentSize

Gets the size of the segment.

```csharp
public uint SegmentSize { get; }
```

#### Property Value

 [uint](https://learn.microsoft.com/dotnet/api/system.uint32)
