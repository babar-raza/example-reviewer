---
linkTitle: "Class ArchiveEntryEncrypted"
title: "Class ArchiveEntryEncrypted"
description: "Represents single file within archive."
summary: "Represents single file within archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip](/zip/)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents single file within archive.

```csharp
public sealed class ArchiveEntryEncrypted : ArchiveEntry, IArchiveFileEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ArchiveEntry](/zip/aspose.zip.archiveentry) ← 
[ArchiveEntryEncrypted](/zip/aspose.zip.archiveentryencrypted)

#### Implements

[IArchiveFileEntry](/zip/aspose.zip.iarchivefileentry)

#### Inherited Members

[ArchiveEntry.Open\(string\)](Aspose.Zip.ArchiveEntry.md\#Aspose\_Zip\_ArchiveEntry\_Open\_System\_String\_), 
[ArchiveEntry.Extract\(string, string\)](Aspose.Zip.ArchiveEntry.md\#Aspose\_Zip\_ArchiveEntry\_Extract\_System\_String\_System\_String\_), 
[ArchiveEntry.Extract\(Stream, string\)](Aspose.Zip.ArchiveEntry.md\#Aspose\_Zip\_ArchiveEntry\_Extract\_System\_IO\_Stream\_System\_String\_), 
[ArchiveEntry.CompressedSize](Aspose.Zip.ArchiveEntry.md\#Aspose\_Zip\_ArchiveEntry\_CompressedSize), 
[ArchiveEntry.Name](Aspose.Zip.ArchiveEntry.md\#Aspose\_Zip\_ArchiveEntry\_Name), 
[ArchiveEntry.Comment](Aspose.Zip.ArchiveEntry.md\#Aspose\_Zip\_ArchiveEntry\_Comment), 
[ArchiveEntry.UncompressedSize](Aspose.Zip.ArchiveEntry.md\#Aspose\_Zip\_ArchiveEntry\_UncompressedSize), 
[ArchiveEntry.ModificationTime](Aspose.Zip.ArchiveEntry.md\#Aspose\_Zip\_ArchiveEntry\_ModificationTime), 
[ArchiveEntry.IsDirectory](Aspose.Zip.ArchiveEntry.md\#Aspose\_Zip\_ArchiveEntry\_IsDirectory), 
[ArchiveEntry.DataSource](Aspose.Zip.ArchiveEntry.md\#Aspose\_Zip\_ArchiveEntry\_DataSource), 
[ArchiveEntry.CompressionSettings](Aspose.Zip.ArchiveEntry.md\#Aspose\_Zip\_ArchiveEntry\_CompressionSettings), 
[ArchiveEntry.CompressionProgressed](Aspose.Zip.ArchiveEntry.md\#Aspose\_Zip\_ArchiveEntry\_CompressionProgressed), 
[ArchiveEntry.ExtractionProgressed](Aspose.Zip.ArchiveEntry.md\#Aspose\_Zip\_ArchiveEntry\_ExtractionProgressed), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Remarks

Cast an Aspose.Zip.ArchiveEntry instance to Aspose.Zip.ArchiveEntryEncrypted to determine whether the entry encrypted or not.

## Properties

### <a id="Aspose_Zip_ArchiveEntryEncrypted_EncryptionSettings"></a> EncryptionSettings

Gets settings for encryption or decryption.

```csharp
public EncryptionSettings EncryptionSettings { get; }
```

#### Property Value

 [EncryptionSettings](/zip/aspose.zip.saving.encryptionsettings)
