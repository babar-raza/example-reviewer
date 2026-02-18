---
linkTitle: "Class WimEntry"
title: "Class WimEntry"
description: "Represents a single file or directory within wim image."
summary: "Represents a single file or directory within wim image."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Wim](/zip/aspose.zip.wim)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents a single file or directory within wim image.

```csharp
public abstract class WimEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[WimEntry](/zip/aspose.zip.wim.wimentry)

#### Derived

[WimDirectoryEntry](/zip/aspose.zip.wim.wimdirectoryentry), 
[WimFileEntry](/zip/aspose.zip.wim.wimfileentry)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Properties

### <a id="Aspose_Zip_Wim_WimEntry_AlternateDataStreams"></a> AlternateDataStreams

Gets the names of the alternate data streams for a file or directory.

```csharp
public string[] AlternateDataStreams { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)\[\]

### <a id="Aspose_Zip_Wim_WimEntry_Archive"></a> Archive

Gets the archive the entry belongs to.

```csharp
public WimArchive Archive { get; }
```

#### Property Value

 [WimArchive](/zip/aspose.zip.wim.wimarchive)

### <a id="Aspose_Zip_Wim_WimEntry_ChangeTime"></a> ChangeTime

Gets the last time the file or directory was changed.

```csharp
public DateTime ChangeTime { get; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_Wim_WimEntry_CreationTime"></a> CreationTime

Gets the creation time of the file or directory.

```csharp
public DateTime CreationTime { get; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_Wim_WimEntry_FileAttributes"></a> FileAttributes

Gets the file or directory attributes.

```csharp
public FileAttributes FileAttributes { get; }
```

#### Property Value

 [FileAttributes](https://learn.microsoft.com/dotnet/api/system.io.fileattributes)

### <a id="Aspose_Zip_Wim_WimEntry_FullPath"></a> FullPath

Gets a full path of the entry within the image.

```csharp
public string FullPath { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_Wim_WimEntry_HardLink"></a> HardLink

Gets the hardlink id of the file or directory.

```csharp
public long HardLink { get; }
```

#### Property Value

 [long](https://learn.microsoft.com/dotnet/api/system.int64)

### <a id="Aspose_Zip_Wim_WimEntry_HasHardLinks"></a> HasHardLinks

Gets whether the file or directory is known by other names.

```csharp
public bool HasHardLinks { get; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_Wim_WimEntry_Image"></a> Image

Gets the image the entry belongs to.

```csharp
public WimImage Image { get; }
```

#### Property Value

 [WimImage](/zip/aspose.zip.wim.wimimage)

### <a id="Aspose_Zip_Wim_WimEntry_IsDirectory"></a> IsDirectory

Gets a value indicating whether the entry represents a directory.

```csharp
public bool IsDirectory { get; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_Wim_WimEntry_LastAccessTime"></a> LastAccessTime

Gets the last access time of the file or directory.

```csharp
public DateTime LastAccessTime { get; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_Wim_WimEntry_LastWriteTime"></a> LastWriteTime

Gets the modification time of the file or directory.

```csharp
[Obsolete("This property will be removed in a future release. Please use ModificationTime instead.")]
public DateTime LastWriteTime { get; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_Wim_WimEntry_ModificationTime"></a> ModificationTime

Gets the modification time of the file or directory.

```csharp
public DateTime ModificationTime { get; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_Wim_WimEntry_Name"></a> Name

Gets name of the entry within the image.

```csharp
public string Name { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_Wim_WimEntry_Parent"></a> Parent

Gets the parent directory the entry belongs to.

```csharp
public WimDirectoryEntry Parent { get; }
```

#### Property Value

 [WimDirectoryEntry](/zip/aspose.zip.wim.wimdirectoryentry)

### <a id="Aspose_Zip_Wim_WimEntry_ShortName"></a> ShortName

Gets short name of the entry within the image.

```csharp
public string ShortName { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

## Methods

### <a id="Aspose_Zip_Wim_WimEntry_ToString"></a> ToString\(\)

```csharp
public override string ToString()
```

#### Returns

 [string](https://learn.microsoft.com/dotnet/api/system.string)
