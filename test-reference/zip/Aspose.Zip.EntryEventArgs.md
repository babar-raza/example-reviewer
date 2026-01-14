---
linkTitle: "Class EntryEventArgs"
title: "Class EntryEventArgs"
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
public class EntryEventArgs : EventArgs
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[EventArgs](https://learn.microsoft.com/dotnet/api/system.eventargs) ← 
[EntryEventArgs](/zip/aspose.zip.entryeventargs)

#### Derived

[CancelEntryEventArgs](/zip/aspose.zip.cancelentryeventargs)

#### Inherited Members

[EventArgs.Empty](https://learn.microsoft.com/dotnet/api/system.eventargs.empty), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_EntryEventArgs__ctor_Aspose_Zip_ArchiveEntry_"></a> EntryEventArgs\(ArchiveEntry\)

Initializes a new instance of the Aspose.Zip.EntryEventArgs class.

```csharp
public EntryEventArgs(ArchiveEntry entry)
```

#### Parameters

`entry` [ArchiveEntry](/zip/aspose.zip.archiveentry)

Archive entry the event is raised for.

## Properties

### <a id="Aspose_Zip_EntryEventArgs_Entry"></a> Entry

Gets the archive entry the event is raised for.

```csharp
public ArchiveEntry Entry { get; }
```

#### Property Value

 [ArchiveEntry](/zip/aspose.zip.archiveentry)

## See Also

[ArchiveLoadOptions](/zip/aspose.zip.archiveloadoptions).[EntryListed](Aspose.Zip.ArchiveLoadOptions.md\#Aspose\_Zip\_ArchiveLoadOptions\_EntryListed)
