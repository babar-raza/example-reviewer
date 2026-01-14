---
linkTitle: "Class SevenZipArchiveEntryEncrypted"
title: "Class SevenZipArchiveEntryEncrypted"
description: "Represents a single file within 7z archive."
summary: "Represents a single file within 7z archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.SevenZip](/zip/aspose.zip.sevenzip)  
Assembly: Aspose.Zip.dll (25.12.0)  

Represents a single file within 7z archive.

```csharp
public class SevenZipArchiveEntryEncrypted : SevenZipArchiveEntry, IArchiveFileEntry
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[SevenZipArchiveEntry](/zip/aspose.zip.sevenzip.sevenziparchiveentry) ← 
[SevenZipArchiveEntryEncrypted](/zip/aspose.zip.sevenzip.sevenziparchiveentryencrypted)

#### Implements

[IArchiveFileEntry](/zip/aspose.zip.iarchivefileentry)

#### Inherited Members

[SevenZipArchiveEntry.GetDestinationStream\(Stream\)](Aspose.Zip.SevenZip.SevenZipArchiveEntry.md\#Aspose\_Zip\_SevenZip\_SevenZipArchiveEntry\_GetDestinationStream\_System\_IO\_Stream\_), 
[SevenZipArchiveEntry.FinalizeCompressedData\(Stream, byte\[\]\)](Aspose.Zip.SevenZip.SevenZipArchiveEntry.md\#Aspose\_Zip\_SevenZip\_SevenZipArchiveEntry\_FinalizeCompressedData\_System\_IO\_Stream\_System\_Byte\_\_\_), 
[SevenZipArchiveEntry.Extract\(string, string\)](Aspose.Zip.SevenZip.SevenZipArchiveEntry.md\#Aspose\_Zip\_SevenZip\_SevenZipArchiveEntry\_Extract\_System\_String\_System\_String\_), 
[SevenZipArchiveEntry.Extract\(Stream, string\)](Aspose.Zip.SevenZip.SevenZipArchiveEntry.md\#Aspose\_Zip\_SevenZip\_SevenZipArchiveEntry\_Extract\_System\_IO\_Stream\_System\_String\_), 
[SevenZipArchiveEntry.Open\(string\)](Aspose.Zip.SevenZip.SevenZipArchiveEntry.md\#Aspose\_Zip\_SevenZip\_SevenZipArchiveEntry\_Open\_System\_String\_), 
[SevenZipArchiveEntry.Name](Aspose.Zip.SevenZip.SevenZipArchiveEntry.md\#Aspose\_Zip\_SevenZip\_SevenZipArchiveEntry\_Name), 
[SevenZipArchiveEntry.ModificationTime](Aspose.Zip.SevenZip.SevenZipArchiveEntry.md\#Aspose\_Zip\_SevenZip\_SevenZipArchiveEntry\_ModificationTime), 
[SevenZipArchiveEntry.UncompressedSize](Aspose.Zip.SevenZip.SevenZipArchiveEntry.md\#Aspose\_Zip\_SevenZip\_SevenZipArchiveEntry\_UncompressedSize), 
[SevenZipArchiveEntry.CompressedSize](Aspose.Zip.SevenZip.SevenZipArchiveEntry.md\#Aspose\_Zip\_SevenZip\_SevenZipArchiveEntry\_CompressedSize), 
[SevenZipArchiveEntry.IsDirectory](Aspose.Zip.SevenZip.SevenZipArchiveEntry.md\#Aspose\_Zip\_SevenZip\_SevenZipArchiveEntry\_IsDirectory), 
[SevenZipArchiveEntry.CompressionSettings](Aspose.Zip.SevenZip.SevenZipArchiveEntry.md\#Aspose\_Zip\_SevenZip\_SevenZipArchiveEntry\_CompressionSettings), 
[SevenZipArchiveEntry.Source](Aspose.Zip.SevenZip.SevenZipArchiveEntry.md\#Aspose\_Zip\_SevenZip\_SevenZipArchiveEntry\_Source), 
[SevenZipArchiveEntry.FileAttributes](Aspose.Zip.SevenZip.SevenZipArchiveEntry.md\#Aspose\_Zip\_SevenZip\_SevenZipArchiveEntry\_FileAttributes), 
[SevenZipArchiveEntry.CompressionProgressed](Aspose.Zip.SevenZip.SevenZipArchiveEntry.md\#Aspose\_Zip\_SevenZip\_SevenZipArchiveEntry\_CompressionProgressed), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Remarks

Cast an Aspose.Zip.SevenZip.SevenZipArchiveEntry instance to Aspose.Zip.SevenZip.SevenZipArchiveEntryEncrypted to determine whether the entry encrypted or not.

## Methods

### <a id="Aspose_Zip_SevenZip_SevenZipArchiveEntryEncrypted_FinalizeCompressedData_System_IO_Stream_System_Byte___"></a> FinalizeCompressedData\(Stream, byte\[\]\)

Write to output stream any headers that follow compressed data.

```csharp
protected override int FinalizeCompressedData(Stream outputStream, byte[] encoderProperties)
```

#### Parameters

`outputStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Output stream for the entry.

`encoderProperties` [byte](https://learn.microsoft.com/dotnet/api/system.byte)\[\]

Properties of compressor.

#### Returns

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

Number of "technical" bytes that were added after entry significant data block.

#### Exceptions

 [CryptographicException](https://learn.microsoft.com/dotnet/api/system.security.cryptography.cryptographicexception)

The key is corrupt that can cause invalid padding to the stream.

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

The final block has already been transformed.

### <a id="Aspose_Zip_SevenZip_SevenZipArchiveEntryEncrypted_GetDestinationStream_System_IO_Stream_"></a> GetDestinationStream\(Stream\)

Destination stream for the entry, may be decorated.

```csharp
protected override Stream GetDestinationStream(Stream outputStream)
```

#### Parameters

`outputStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

Output stream for the entry.

#### Returns

 [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The destination stream for entry compression.
