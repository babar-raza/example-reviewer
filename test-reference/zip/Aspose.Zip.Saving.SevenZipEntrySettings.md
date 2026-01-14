---
linkTitle: "Class SevenZipEntrySettings"
title: "Class SevenZipEntrySettings"
description: "Settings used to compress or decompress 7Z entries."
summary: "Settings used to compress or decompress 7Z entries."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings used to compress or decompress 7Z entries.

```csharp
public class SevenZipEntrySettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[SevenZipEntrySettings](/zip/aspose.zip.saving.sevenzipentrysettings)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Saving_SevenZipEntrySettings__ctor_Aspose_Zip_Saving_SevenZipCompressionSettings_Aspose_Zip_Saving_SevenZipEncryptionSettings_"></a> SevenZipEntrySettings\(SevenZipCompressionSettings, SevenZipEncryptionSettings\)

Initializes a new instance of the Aspose.Zip.Saving.SevenZipEntrySettings class.

```csharp
public SevenZipEntrySettings(SevenZipCompressionSettings compressionSettings = null, SevenZipEncryptionSettings encryptionSettings = null)
```

#### Parameters

`compressionSettings` [SevenZipCompressionSettings](/zip/aspose.zip.saving.sevenzipcompressionsettings)

Settings for compression. Pass null for default LZMA settings.
            <p>
            Can be one of these:
            <ul><li><span class="term">Aspose.Zip.Saving.SevenZipLZMACompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.SevenZipLZMA2CompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.SevenZipBZip2CompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.SevenZipStoreCompressionSettings</span></li><li><span class="term">Aspose.Zip.Saving.SevenZipPPMdCompressionSettings</span></li></ul></p>

`encryptionSettings` [SevenZipEncryptionSettings](/zip/aspose.zip.saving.sevenzipencryptionsettings)

Settings for encryption. Pass null if no need to encrypt or decrypt.
            <p>Can be only one:
            <ul><li><span class="term">Aspose.Zip.Saving.SevenZipAESEncryptionSettings</span></li></ul></p>

## Properties

### <a id="Aspose_Zip_Saving_SevenZipEntrySettings_CompressHeader"></a> CompressHeader

Gets or sets value indicating whether to compress archive header.

```csharp
public bool CompressHeader { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

#### Remarks

This setting is equivalent <code>-mhc=on</code> switch of 7-Zip tool. Currently, it is incompatible with header encryption.

### <a id="Aspose_Zip_Saving_SevenZipEntrySettings_CompressionSettings"></a> CompressionSettings

Gets settings for compression or decompression routine.

```csharp
public SevenZipCompressionSettings CompressionSettings { get; }
```

#### Property Value

 [SevenZipCompressionSettings](/zip/aspose.zip.saving.sevenzipcompressionsettings)

### <a id="Aspose_Zip_Saving_SevenZipEntrySettings_EncryptionSettings"></a> EncryptionSettings

Gets settings for encryption or decryption. Settings of particular entry may vary.

```csharp
public SevenZipEncryptionSettings EncryptionSettings { get; }
```

#### Property Value

 [SevenZipEncryptionSettings](/zip/aspose.zip.saving.sevenzipencryptionsettings)

#### Remarks

The Aspose.Zip.Saving.SevenZipAESEncryptionSettings is only option for 7Z archives.

### <a id="Aspose_Zip_Saving_SevenZipEntrySettings_Solid"></a> Solid

Gets or sets value indicating whether to concatenate entries and treat them as a single data block.

```csharp
public bool Solid { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

#### Examples

<p>
        The following example shows how to compress a directory to solid 7z archive with LZMA2 compression without encryption.
        </p>

```csharp
using (FileStream sevenZipFile = File.Open("archive.7z", FileMode.Create))
{
    using (var archive = new SevenZipArchive(new SevenZipEntrySettings(new SevenZipLZMA2CompressionSettings()){ Solid = true }))
    {
        archive.CreateEntries("C:\\Documents");
        archive.Save(sevenZipFile);
    }
}
```

#### Remarks

Provide <code>SevenZipEntrySettings</code> for solid 7z archive on archive instantiation.
