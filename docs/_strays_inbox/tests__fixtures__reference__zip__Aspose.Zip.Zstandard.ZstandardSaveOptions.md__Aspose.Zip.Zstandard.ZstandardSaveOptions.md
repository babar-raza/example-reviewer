---
linkTitle: "Class ZstandardSaveOptions"
title: "Class ZstandardSaveOptions"
description: "Settings for ZStandard  archive."
summary: "Settings for ZStandard  archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Zstandard](/zip/aspose.zip.zstandard)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for ZStandard  archive.

```csharp
public class ZstandardSaveOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ZstandardSaveOptions](/zip/aspose.zip.zstandard.zstandardsaveoptions)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Zstandard_ZstandardSaveOptions__ctor"></a> ZstandardSaveOptions\(\)

```csharp
public ZstandardSaveOptions()
```

### <a id="Aspose_Zip_Zstandard_ZstandardSaveOptions_CompressionProgressed"></a> CompressionProgressed

Raises when a portion of raw stream compressed.

```csharp
public event EventHandler<ProgressEventArgs> CompressionProgressed
```

#### Event Type

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[ProgressEventArgs](/zip/aspose.zip.progresseventargs)\>

#### Examples

`settings.CompressionProgressed += (s, e) =&gt; { int percent = (int)((100 * e.ProceededBytes) / entrySourceStream.Length); };`
