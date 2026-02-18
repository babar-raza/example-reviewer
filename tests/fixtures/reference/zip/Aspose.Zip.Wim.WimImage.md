---
linkTitle: "Class WimImage"
title: "Class WimImage"
description: "Represents a single image within wim archive."
summary: "Represents a single image within wim archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Wim](/zip/aspose.zip.wim)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents a single image within wim archive.

```csharp
public sealed class WimImage
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[WimImage](/zip/aspose.zip.wim.wimimage)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Properties

### <a id="Aspose_Zip_Wim_WimImage_AllEntries"></a> AllEntries

Gets entries of Aspose.Zip.Wim.WimEntry type constituting the image recursively.

```csharp
public IEnumerable<WimEntry> AllEntries { get; }
```

#### Property Value

 [IEnumerable](https://learn.microsoft.com/dotnet/api/system.collections.generic.ienumerable\-1)<[WimEntry](/zip/aspose.zip.wim.wimentry)\>

### <a id="Aspose_Zip_Wim_WimImage_Parent"></a> Parent

Gets the archive the image belongs to.

```csharp
public WimArchive Parent { get; }
```

#### Property Value

 [WimArchive](/zip/aspose.zip.wim.wimarchive)

### <a id="Aspose_Zip_Wim_WimImage_RootDirectory"></a> RootDirectory

Gets the root directory entry of the image.

```csharp
public WimDirectoryEntry RootDirectory { get; }
```

#### Property Value

 [WimDirectoryEntry](/zip/aspose.zip.wim.wimdirectoryentry)

## Methods

### <a id="Aspose_Zip_Wim_WimImage_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

Extracts all the files in the image to the directory provided.

```csharp
public void ExtractToDirectory(string destinationDirectory)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory to place the extracted files in.

#### Examples


```csharp
using (var archive = new WimArchive("install.wim")) 
{ 
   archive.Images[0].ExtractToDirectory("C:\\extracted");
}
```

#### Remarks

If the directory does not exist, it will be created.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

path is null

 [PathTooLongException](https://learn.microsoft.com/dotnet/api/system.io.pathtoolongexception)

The specified path, file name, or both exceed the system-defined maximum length. For example, on Windows-based platforms, paths must be less than 248 characters and file names must be less than 260 characters.

 [SecurityException](https://learn.microsoft.com/dotnet/api/system.security.securityexception)

The caller does not have the required permission to access the existing directory.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

If the directory does not exist, the path contains a colon character (:) that is not part of a drive label ("C:\").

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

path is a zero-length string, contains only white space, or contains one or more invalid characters. You can query for invalid characters by using the System.IO.Path.GetInvalidPathChars method. -or- path is prefixed with, or contains, only a colon character (:).

 [IOException](https://learn.microsoft.com/dotnet/api/system.io.ioexception)

The directory specified by path is a file. -or- The network name is not known.

 [InvalidDataException](https://learn.microsoft.com/dotnet/api/system.io.invaliddataexception)

The archive is corrupted.

### <a id="Aspose_Zip_Wim_WimImage_GetEntry_System_String_"></a> GetEntry\(string\)

Gets the entry of Aspose.Zip.Wim.WimEntry type for a given path.

```csharp
public WimEntry GetEntry(string path)
```

#### Parameters

`path` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path of file or directory.

#### Returns

 [WimEntry](/zip/aspose.zip.wim.wimentry)

The entry of Aspose.Zip.Wim.WimEntry type.
