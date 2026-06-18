---
linkTitle: "Class XarDirectoryEntry"
title: "Class XarDirectoryEntry"
description: "Represents directory entry within xar archive."
summary: "Represents directory entry within xar archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Xar](/zip/aspose.zip.xar)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents directory entry within xar archive.

```csharp
public sealed class XarDirectoryEntry : XarEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[XarEntry](/zip/aspose.zip.xar.xarentry) ← 
[XarDirectoryEntry](/zip/aspose.zip.xar.xardirectoryentry)

#### Inherited Members

[XarEntry.ToString\(\)](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_ToString), 
[XarEntry.Name](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_Name), 
[XarEntry.FullPath](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_FullPath), 
[XarEntry.IsDirectory](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_IsDirectory), 
[XarEntry.Parent](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_Parent), 
[XarEntry.CreationTime](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_CreationTime), 
[XarEntry.LastAccessTime](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_LastAccessTime), 
[XarEntry.LastWriteTime](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_LastWriteTime), 
[XarEntry.ModificationTime](Aspose.Zip.Xar.XarEntry.md\#Aspose\_Zip\_Xar\_XarEntry\_ModificationTime), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Properties

### <a id="Aspose_Zip_Xar_XarDirectoryEntry_AllEntries"></a> AllEntries

Gets all entries of Aspose.Zip.Xar.XarEntry type constituting the directory recursively.

```csharp
public IEnumerable<XarEntry> AllEntries { get; }
```

#### Property Value

 [IEnumerable](https://learn.microsoft.com/dotnet/api/system.collections.generic.ienumerable\-1)<[XarEntry](/zip/aspose.zip.xar.xarentry)\>

### <a id="Aspose_Zip_Xar_XarDirectoryEntry_Directories"></a> Directories

Gets entries of Aspose.Zip.Xar.XarDirectoryEntry type constituting the directory.

```csharp
public IEnumerable<XarDirectoryEntry> Directories { get; }
```

#### Property Value

 [IEnumerable](https://learn.microsoft.com/dotnet/api/system.collections.generic.ienumerable\-1)<[XarDirectoryEntry](/zip/aspose.zip.xar.xardirectoryentry)\>

### <a id="Aspose_Zip_Xar_XarDirectoryEntry_Files"></a> Files

Gets entries of Aspose.Zip.Xar.XarFileEntry type constituting the directory.

```csharp
public IEnumerable<XarFileEntry> Files { get; }
```

#### Property Value

 [IEnumerable](https://learn.microsoft.com/dotnet/api/system.collections.generic.ienumerable\-1)<[XarFileEntry](/zip/aspose.zip.xar.xarfileentry)\>

### <a id="Aspose_Zip_Xar_XarDirectoryEntry_FilesAndDirectories"></a> FilesAndDirectories

Gets entries of Aspose.Zip.Xar.XarEntry type constituting the directory.

```csharp
public IEnumerable<XarEntry> FilesAndDirectories { get; }
```

#### Property Value

 [IEnumerable](https://learn.microsoft.com/dotnet/api/system.collections.generic.ienumerable\-1)<[XarEntry](/zip/aspose.zip.xar.xarentry)\>

## Methods

### <a id="Aspose_Zip_Xar_XarDirectoryEntry_ExtractToDirectory_System_String_"></a> ExtractToDirectory\(string\)

Extracts all the files in the current directory to the directory provided.

```csharp
public void ExtractToDirectory(string destinationDirectory)
```

#### Parameters

`destinationDirectory` [string](https://learn.microsoft.com/dotnet/api/system.string)

The path to the directory to place the extracted files in.

#### Examples


```csharp
using (var archive = new XarArchive("archive.xar")) 
{
   ((XarDirectoryEntry)archive.Entries[0]).ExtractToDirectory("C:\\extracted");
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
