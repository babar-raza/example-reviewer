---
linkTitle: "Class ProgressEventArgs"
title: "Class ProgressEventArgs"
description: "Class for event data containing the number of bytes proceeded."
summary: "Class for event data containing the number of bytes proceeded."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip](/zip/)  
Assembly: Aspose.Zip.dll (25.12.0)  

Class for event data containing the number of bytes proceeded.

```csharp
public class ProgressEventArgs : EventArgs
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[EventArgs](https://learn.microsoft.com/dotnet/api/system.eventargs) ← 
[ProgressEventArgs](/zip/aspose.zip.progresseventargs)

#### Derived

[ProgressCancelEventArgs](/zip/aspose.zip.progresscanceleventargs)

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

### <a id="Aspose_Zip_ProgressEventArgs__ctor_System_UInt64_"></a> ProgressEventArgs\(ulong\)

Initializes a new instance of the Aspose.Zip.ProgressEventArgs class.

```csharp
public ProgressEventArgs(ulong proceededBytes)
```

#### Parameters

`proceededBytes` [ulong](https://learn.microsoft.com/dotnet/api/system.uint64)

The number of bytes proceeded.

## Properties

### <a id="Aspose_Zip_ProgressEventArgs_ProceededBytes"></a> ProceededBytes

Gets the number of bytes proceeded.

```csharp
public ulong ProceededBytes { get; }
```

#### Property Value

 [ulong](https://learn.microsoft.com/dotnet/api/system.uint64)
