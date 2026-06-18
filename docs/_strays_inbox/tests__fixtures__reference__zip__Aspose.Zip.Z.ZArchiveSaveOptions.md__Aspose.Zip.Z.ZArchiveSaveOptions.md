---
linkTitle: "Class ZArchiveSaveOptions"
title: "Class ZArchiveSaveOptions"
description: "Settings for Zarchive."
summary: "Settings for Zarchive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Z](/zip/aspose.zip.z)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for Zarchive.

```csharp
public class ZArchiveSaveOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ZArchiveSaveOptions](/zip/aspose.zip.z.zarchivesaveoptions)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Z_ZArchiveSaveOptions__ctor"></a> ZArchiveSaveOptions\(\)

```csharp
public ZArchiveSaveOptions()
```

### <a id="Aspose_Zip_Z_ZArchiveSaveOptions_CompressionProgressed"></a> CompressionProgressed

Raises when a portion of raw stream compressed.

```csharp
public event EventHandler<ProgressEventArgs> CompressionProgressed
```

#### Event Type

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[ProgressEventArgs](/zip/aspose.zip.progresseventargs)\>

#### Examples

`settings.CompressionProgressed += (s, e) =&gt; { int percent = (int)((100 * e.ProceededBytes) / entrySourceStream.Length); };`
