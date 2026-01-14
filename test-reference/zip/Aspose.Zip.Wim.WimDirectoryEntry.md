---
linkTitle: "Class WimDirectoryEntry"
title: "Class WimDirectoryEntry"
description: "Represents a single directory within wim archive."
summary: "Represents a single directory within wim archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Wim](/zip/aspose.zip.wim)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents a single directory within wim archive.

```csharp
public sealed class WimDirectoryEntry : WimEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[WimEntry](/zip/aspose.zip.wim.wimentry) ← 
[WimDirectoryEntry](/zip/aspose.zip.wim.wimdirectoryentry)

#### Inherited Members

[WimEntry.ToString\(\)](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_ToString), 
[WimEntry.Archive](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_Archive), 
[WimEntry.Image](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_Image), 
[WimEntry.Parent](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_Parent), 
[WimEntry.Name](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_Name), 
[WimEntry.ShortName](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_ShortName), 
[WimEntry.FullPath](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_FullPath), 
[WimEntry.ChangeTime](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_ChangeTime), 
[WimEntry.CreationTime](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_CreationTime), 
[WimEntry.LastAccessTime](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_LastAccessTime), 
[WimEntry.LastWriteTime](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_LastWriteTime), 
[WimEntry.ModificationTime](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_ModificationTime), 
[WimEntry.FileAttributes](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_FileAttributes), 
[WimEntry.AlternateDataStreams](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_AlternateDataStreams), 
[WimEntry.HardLink](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_HardLink), 
[WimEntry.HasHardLinks](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_HasHardLinks), 
[WimEntry.IsDirectory](Aspose.Zip.Wim.WimEntry.md\#Aspose\_Zip\_Wim\_WimEntry\_IsDirectory), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Properties

### <a id="Aspose_Zip_Wim_WimDirectoryEntry_AllEntries"></a> AllEntries

Gets all entries of Aspose.Zip.Wim.WimEntry type constituting the directory recursively.

```csharp
public IEnumerable<WimEntry> AllEntries { get; }
```

#### Property Value

 [IEnumerable](https://learn.microsoft.com/dotnet/api/system.collections.generic.ienumerable\-1)<[WimEntry](/zip/aspose.zip.wim.wimentry)\>

### <a id="Aspose_Zip_Wim_WimDirectoryEntry_Directories"></a> Directories

Gets entries of Aspose.Zip.Wim.WimDirectoryEntry type constituting the directory.

```csharp
public ReadOnlyCollection<WimDirectoryEntry> Directories { get; }
```

#### Property Value

 [ReadOnlyCollection](https://learn.microsoft.com/dotnet/api/system.collections.objectmodel.readonlycollection\-1)<[WimDirectoryEntry](/zip/aspose.zip.wim.wimdirectoryentry)\>

### <a id="Aspose_Zip_Wim_WimDirectoryEntry_Files"></a> Files

Gets entries of Aspose.Zip.Wim.WimFileEntry type constituting the directory.

```csharp
public ReadOnlyCollection<WimFileEntry> Files { get; }
```

#### Property Value

 [ReadOnlyCollection](https://learn.microsoft.com/dotnet/api/system.collections.objectmodel.readonlycollection\-1)<[WimFileEntry](/zip/aspose.zip.wim.wimfileentry)\>

### <a id="Aspose_Zip_Wim_WimDirectoryEntry_FilesAndDirectories"></a> FilesAndDirectories

Gets entries of Aspose.Zip.Wim.WimEntry type constituting the directory.

```csharp
public IEnumerable<WimEntry> FilesAndDirectories { get; }
```

#### Property Value

 [IEnumerable](https://learn.microsoft.com/dotnet/api/system.collections.generic.ienumerable\-1)<[WimEntry](/zip/aspose.zip.wim.wimentry)\>

## Methods

### <a id="Aspose_Zip_Wim_WimDirectoryEntry_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

Extracts all the files in the current directory to the directory provided.

```csharp
public void ExtractToDirectory(string destinationDirectory)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory to place the extracted files in.

#### Examples


```csharp
using (var archive = new WimArchive("archive.wim")) 
{ 
   archive.Images[0].RootDirectory.ExtractToDirectory(@"C:\\extracted");
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

 [OperationCanceledException](https://learn.microsoft.com/dotnet/api/system.operationcanceledexception)

In .NET Framework 4.0 and above: Thrown when the extraction is canceled via the provided cancellation token.
