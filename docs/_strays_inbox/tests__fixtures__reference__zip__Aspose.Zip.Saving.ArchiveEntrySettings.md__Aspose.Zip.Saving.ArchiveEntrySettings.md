---
linkTitle: "Class ArchiveEntrySettings"
title: "Class ArchiveEntrySettings"
description: "Settings used to compress or decompress entries."
summary: "Settings used to compress or decompress entries."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings used to compress or decompress entries.

```csharp
public class ArchiveEntrySettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ArchiveEntrySettings](/zip/aspose.zip.saving.archiveentrysettings)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Saving_ArchiveEntrySettings__ctor_Aspose_Zip_Saving_CompressionSettings_Aspose_Zip_Saving_EncryptionSettings_"></a> ArchiveEntrySettings\(CompressionSettings, EncryptionSettings\)

Initializes a new instance of the Aspose.Zip.Saving.ArchiveEntrySettings class.

```csharp
public ArchiveEntrySettings(CompressionSettings compressionSettings = null, EncryptionSettings encryptionSettings = null)
```

#### Parameters

`compressionSettings` [CompressionSettings](/zip/aspose.zip.saving.compressionsettings)

Settings for compression. Pass null for default deflate settings.
            <p>
            Can be one of these:
            <ul><li><span class="term">Aspose.Zip.Saving.DeflateCompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.StoreCompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.Bzip2CompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.LzmaCompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.PPMdCompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.EnhancedDeflateCompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.XzCompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.ZstandardCompressionSettings</span></li></ul></p>

`encryptionSettings` [EncryptionSettings](/zip/aspose.zip.saving.encryptionsettings)

Settings for encryption. Pass null if no need to encrypt or decrypt.
            <p>Can be one of these:
            <ul><li><span class="term">Aspose.Zip.Saving.TraditionalEncryptionSettings</span></li><li><span class="term">Aspose.Zip.Saving.AesEcryptionSettings</span></li></ul></p>

## Properties

### <a id="Aspose_Zip_Saving_ArchiveEntrySettings_CompressionSettings"></a> CompressionSettings

Gets settings for compression or decompression routine.

```csharp
public CompressionSettings CompressionSettings { get; }
```

#### Property Value

 [CompressionSettings](/zip/aspose.zip.saving.compressionsettings)

#### Remarks

Can be one of these:
<ul><li><span class="term">Aspose.Zip.Saving.DeflateCompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.StoreCompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.Bzip2CompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.LzmaCompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.PPMdCompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.EnhancedDeflateCompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.XzCompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.ZstandardCompressionSettings</span></li></ul>

### <a id="Aspose_Zip_Saving_ArchiveEntrySettings_EncryptionSettings"></a> EncryptionSettings

Gets settings for encryption or decryption. Settings of particular entry may vary.

```csharp
public EncryptionSettings EncryptionSettings { get; }
```

#### Property Value

 [EncryptionSettings](/zip/aspose.zip.saving.encryptionsettings)

#### Remarks

<ul><li><span class="term">
      Aspose.Zip.Saving.TraditionalEncryptionSettings
    </span></li><li><span class="term">
      Aspose.Zip.Saving.AesEcryptionSettings
    </span></li></ul>
