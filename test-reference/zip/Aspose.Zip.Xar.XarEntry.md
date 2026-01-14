---
linkTitle: "Class XarEntry"
title: "Class XarEntry"
description: "Represents a single entry within xar archive."
summary: "Represents a single entry within xar archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Xar](/zip/aspose.zip.xar)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents a single entry within xar archive.

```csharp
public abstract class XarEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[XarEntry](/zip/aspose.zip.xar.xarentry)

#### Derived

[XarDirectoryEntry](/zip/aspose.zip.xar.xardirectoryentry), 
[XarFileEntry](/zip/aspose.zip.xar.xarfileentry)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Properties

### <a id="Aspose_Zip_Xar_XarEntry_CreationTime"></a> CreationTime

Gets the creation time of the file or directory.

```csharp
public DateTime CreationTime { get; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_Xar_XarEntry_FullPath"></a> FullPath

Gets a full path of the entry within the archive.

```csharp
public string FullPath { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_Xar_XarEntry_IsDirectory"></a> IsDirectory

Gets a value indicating whether the entry represents a directory.

```csharp
public bool IsDirectory { get; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_Xar_XarEntry_LastAccessTime"></a> LastAccessTime

Gets the last access time of the file or directory.

```csharp
public DateTime LastAccessTime { get; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_Xar_XarEntry_LastWriteTime"></a> LastWriteTime

Gets the modification time of the file or directory.

```csharp
[Obsolete("This property will be removed in a future release. Please use ModificationTime instead.")]
public DateTime LastWriteTime { get; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_Xar_XarEntry_ModificationTime"></a> ModificationTime

Gets the modification time of the file or directory.

```csharp
public DateTime ModificationTime { get; }
```

#### Property Value

 [DateTime](https://learn.microsoft.com/dotnet/api/system.datetime)

### <a id="Aspose_Zip_Xar_XarEntry_Name"></a> Name

Gets name of the entry within the archive.

```csharp
public string Name { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_Xar_XarEntry_Parent"></a> Parent

Gets the parent directory the entry belongs to.

```csharp
public XarDirectoryEntry Parent { get; }
```

#### Property Value

 [XarDirectoryEntry](/zip/aspose.zip.xar.xardirectoryentry)

## Methods

### <a id="Aspose_Zip_Xar_XarEntry_ToString"></a> ToString\(\)

```csharp
public override string ToString()
```

#### Returns

 [string](https://learn.microsoft.com/dotnet/api/system.string)
