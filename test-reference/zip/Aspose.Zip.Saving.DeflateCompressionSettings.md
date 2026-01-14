---
linkTitle: "Class DeflateCompressionSettings"
title: "Class DeflateCompressionSettings"
description: "Settings for Deflate compression within a ZIP archive."
summary: "Settings for Deflate compression within a ZIP archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for Deflate compression within a ZIP archive.

```csharp
public class DeflateCompressionSettings : CompressionSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[CompressionSettings](/zip/aspose.zip.saving.compressionsettings) ← 
[DeflateCompressionSettings](/zip/aspose.zip.saving.deflatecompressionsettings)

#### Inherited Members

[CompressionSettings.Bzip2](Aspose.Zip.Saving.CompressionSettings.md\#Aspose\_Zip\_Saving\_CompressionSettings\_Bzip2), 
[CompressionSettings.Deflate](Aspose.Zip.Saving.CompressionSettings.md\#Aspose\_Zip\_Saving\_CompressionSettings\_Deflate), 
[CompressionSettings.EnhancedDeflate](Aspose.Zip.Saving.CompressionSettings.md\#Aspose\_Zip\_Saving\_CompressionSettings\_EnhancedDeflate), 
[CompressionSettings.Store](Aspose.Zip.Saving.CompressionSettings.md\#Aspose\_Zip\_Saving\_CompressionSettings\_Store), 
[CompressionSettings.Lzma](Aspose.Zip.Saving.CompressionSettings.md\#Aspose\_Zip\_Saving\_CompressionSettings\_Lzma), 
[CompressionSettings.Xz](Aspose.Zip.Saving.CompressionSettings.md\#Aspose\_Zip\_Saving\_CompressionSettings\_Xz), 
[CompressionSettings.PPMd](Aspose.Zip.Saving.CompressionSettings.md\#Aspose\_Zip\_Saving\_CompressionSettings\_PPMd), 
[CompressionSettings.Zstd](Aspose.Zip.Saving.CompressionSettings.md\#Aspose\_Zip\_Saving\_CompressionSettings\_Zstd), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Remarks

<p>
         Deflate is a lossless data compression algorithm that uses a combination of the LZ77 algorithm and Huffman coding.
        </p>

## Constructors

### <a id="Aspose_Zip_Saving_DeflateCompressionSettings__ctor"></a> DeflateCompressionSettings\(\)

Initializes a new instance of the Aspose.Zip.Saving.DeflateCompressionSettings class.

```csharp
public DeflateCompressionSettings()
```

#### Examples


```csharp
using (Archive archive = new Archive(new ArchiveEntrySettings(new DeflateCompressionSettings())))
{
    archive.CreateEntry("data.bin", "data.bin");                   
    archive.Save(zipFile);
}
```

## See Also

[https://tools.ietf.org/html/rfc1951](https://tools.ietf.org/html/rfc1951)
