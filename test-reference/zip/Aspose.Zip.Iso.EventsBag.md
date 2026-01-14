---
linkTitle: "Class EventsBag"
title: "Class EventsBag"
description: "Events container used on  saving."
summary: "Events container used on  saving."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Iso](/zip/aspose.zip.iso)  
Assembly: Aspose.Zip.dll (25.12.0)  

Events container used on Aspose.Zip.Iso.IsoArchive saving.

```csharp
public sealed class EventsBag
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[EventsBag](/zip/aspose.zip.iso.eventsbag)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Iso_EventsBag__ctor"></a> EventsBag\(\)

```csharp
public EventsBag()
```

### <a id="Aspose_Zip_Iso_EventsBag_EntryAccessed"></a> EntryAccessed

Raises before an archive entry is being compressed.

```csharp
public event EventHandler<EntryEventArgs> EntryAccessed
```

#### Event Type

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[EntryEventArgs](/zip/aspose.zip.iso.entryeventargs)\>

### <a id="Aspose_Zip_Iso_EventsBag_EntryCompressed"></a> EntryCompressed

Raises after an archive entry has been compressed.

```csharp
public event EventHandler<EntryEventArgs> EntryCompressed
```

#### Event Type

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[EntryEventArgs](/zip/aspose.zip.iso.entryeventargs)\>

## See Also

[IsoSaveOptions](/zip/aspose.zip.iso.isosaveoptions)
