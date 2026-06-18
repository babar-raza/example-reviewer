---
linkTitle: "Class Lz4ArchiveSetting"
title: "Class Lz4ArchiveSetting"
description: "Settings for LZ4 archive composition."
summary: "Settings for LZ4 archive composition."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Lz4](/zip/aspose.zip.lz4)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for LZ4 archive composition.

```csharp
public class Lz4ArchiveSetting
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[Lz4ArchiveSetting](/zip/aspose.zip.lz4.lz4archivesetting)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Lz4_Lz4ArchiveSetting__ctor"></a> Lz4ArchiveSetting\(\)

Initializes a new instance of the Aspose.Zip.Lz4.Lz4ArchiveSetting with default parameters.

```csharp
public Lz4ArchiveSetting()
```

## Properties

### <a id="Aspose_Zip_Lz4_Lz4ArchiveSetting_IncludeBlockChecksum"></a> IncludeBlockChecksum

Gets or sets a value indicating whether to include compressed xxh32 hash at the end of compressed block.

```csharp
public bool IncludeBlockChecksum { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

#### Remarks

Default is false.

### <a id="Aspose_Zip_Lz4_Lz4ArchiveSetting_IncludeContentChecksum"></a> IncludeContentChecksum

Gets or sets a value indicating whether to include content xxh32 hash at the end of LZ4 archive.

```csharp
public bool IncludeContentChecksum { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

#### Remarks

Default is true.

### <a id="Aspose_Zip_Lz4_Lz4ArchiveSetting_IncludeContentSize"></a> IncludeContentSize

Gets or sets a value indicating whether to include the content size in the frame.

```csharp
public bool IncludeContentSize { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

#### Remarks

Default is false. Applied when the source stream is seekable.
