---
linkTitle: "Class CancelEntryEventArgs"
title: "Class CancelEntryEventArgs"
description: "Event arguments for entry related events."
summary: "Event arguments for entry related events."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip](/zip/)  
Assembly: Aspose.Zip.dll (25.12.0)  

Event arguments for entry related events.

```csharp
public class CancelEntryEventArgs : EntryEventArgs
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[EventArgs](https://learn.microsoft.com/dotnet/api/system.eventargs) ← 
[EntryEventArgs](/zip/aspose.zip.entryeventargs) ← 
[CancelEntryEventArgs](/zip/aspose.zip.cancelentryeventargs)

#### Inherited Members

[EntryEventArgs.Entry](Aspose.Zip.EntryEventArgs.md\#Aspose\_Zip\_EntryEventArgs\_Entry), 
[EventArgs.Empty](https://learn.microsoft.com/dotnet/api/system.eventargs.empty), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_CancelEntryEventArgs__ctor_Aspose_Zip_ArchiveEntry_"></a> CancelEntryEventArgs\(ArchiveEntry\)

Initializes a new instance of the Aspose.Zip.EntryEventArgs class.

```csharp
public CancelEntryEventArgs(ArchiveEntry entry)
```

#### Parameters

`entry` [ArchiveEntry](/zip/aspose.zip.archiveentry)

Archive entry the event is raised for.

## Properties

### <a id="Aspose_Zip_CancelEntryEventArgs_Cancel"></a> Cancel

Gets or sets a value indicating whether the event should be canceled.

```csharp
public bool Cancel { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

## See Also

[ArchiveLoadOptions](/zip/aspose.zip.archiveloadoptions).[EntryListed](Aspose.Zip.ArchiveLoadOptions.md\#Aspose\_Zip\_ArchiveLoadOptions\_EntryListed)
