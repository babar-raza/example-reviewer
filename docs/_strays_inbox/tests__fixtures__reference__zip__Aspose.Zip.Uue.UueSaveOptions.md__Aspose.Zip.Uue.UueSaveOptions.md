---
linkTitle: "Class UueSaveOptions"
title: "Class UueSaveOptions"
description: "Options for saving an uuencoded file."
summary: "Options for saving an uuencoded file."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Uue](/zip/aspose.zip.uue)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options for saving an uuencoded file.

```csharp
public class UueSaveOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[UueSaveOptions](/zip/aspose.zip.uue.uuesaveoptions)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Uue_UueSaveOptions__ctor_System_String_System_String_"></a> UueSaveOptions\(string, string\)

Initializes the options with user provided file name and new line.

```csharp
public UueSaveOptions(string fileName, string newLine)
```

#### Parameters

`fileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

The file name to be used when recreating the decoded data.

`newLine` [string](https://learn.microsoft.com/dotnet/api/system.string)

The character terminating each line.

### <a id="Aspose_Zip_Uue_UueSaveOptions__ctor_System_String_"></a> UueSaveOptions\(string\)

Initializes the options with user provided file name and the default new line.

```csharp
public UueSaveOptions(string fileName)
```

#### Parameters

`fileName` [string](https://learn.microsoft.com/dotnet/api/system.string)

The file name to be used when recreating the decoded data.

## Properties

### <a id="Aspose_Zip_Uue_UueSaveOptions_FileName"></a> FileName

Gets the file name to be used when recreating the decoded data.

```csharp
public string FileName { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_Uue_UueSaveOptions_NewLine"></a> NewLine

Gets the character terminating each line, usually "\n" or "\r\n".

```csharp
public string NewLine { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_Uue_UueSaveOptions_UnixFilePermissions"></a> UnixFilePermissions

Gets the file's Unix file permissions.

```csharp
public string UnixFilePermissions { get; set; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

#### Remarks

Default is 644.
