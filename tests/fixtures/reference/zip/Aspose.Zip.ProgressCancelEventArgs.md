---
linkTitle: "Class ProgressCancelEventArgs"
title: "Class ProgressCancelEventArgs"
description: "Class for cancelable event data containing the number of bytes proceeded."
summary: "Class for cancelable event data containing the number of bytes proceeded."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip](/zip/)  
Assembly: Aspose.Zip.dll (25.12.0)  

Class for cancelable event data containing the number of bytes proceeded.

```csharp
public class ProgressCancelEventArgs : ProgressEventArgs
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[EventArgs](https://learn.microsoft.com/dotnet/api/system.eventargs) ← 
[ProgressEventArgs](/zip/aspose.zip.progresseventargs) ← 
[ProgressCancelEventArgs](/zip/aspose.zip.progresscanceleventargs)

#### Inherited Members

[ProgressEventArgs.ProceededBytes](Aspose.Zip.ProgressEventArgs.md\#Aspose\_Zip\_ProgressEventArgs\_ProceededBytes), 
[EventArgs.Empty](https://learn.microsoft.com/dotnet/api/system.eventargs.empty), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_ProgressCancelEventArgs__ctor_System_UInt64_"></a> ProgressCancelEventArgs\(ulong\)

Initializes a new instance of the Aspose.Zip.ProgressCancelEventArgs class.

```csharp
public ProgressCancelEventArgs(ulong proceededBytes)
```

#### Parameters

`proceededBytes` [ulong](https://learn.microsoft.com/dotnet/api/system.uint64)

The number of bytes proceeded.

## Properties

### <a id="Aspose_Zip_ProgressCancelEventArgs_Cancel"></a> Cancel

Gets or sets a value indicating whether the event should be canceled.

```csharp
public bool Cancel { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)
