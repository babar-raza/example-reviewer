---
linkTitle: "Class SevenZipAESEncryptionSettings"
title: "Class SevenZipAESEncryptionSettings"
description: "Settings for AES encryption or decryption algorithm within 7z archive."
summary: "Settings for AES encryption or decryption algorithm within 7z archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for AES encryption or decryption algorithm within 7z archive.

```csharp
public class SevenZipAESEncryptionSettings : SevenZipEncryptionSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[SevenZipEncryptionSettings](/zip/aspose.zip.saving.sevenzipencryptionsettings) ← 
[SevenZipAESEncryptionSettings](/zip/aspose.zip.saving.sevenzipaesencryptionsettings)

#### Inherited Members

[SevenZipEncryptionSettings.Password](Aspose.Zip.Saving.SevenZipEncryptionSettings.md\#Aspose\_Zip\_Saving\_SevenZipEncryptionSettings\_Password), 
[SevenZipEncryptionSettings.EncryptHeader](Aspose.Zip.Saving.SevenZipEncryptionSettings.md\#Aspose\_Zip\_Saving\_SevenZipEncryptionSettings\_EncryptHeader), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Saving_SevenZipAESEncryptionSettings__ctor_System_String_"></a> SevenZipAESEncryptionSettings\(string\)

Initializes a new instance of the Aspose.Zip.Saving.SevenZipAESEncryptionSettings class.

```csharp
public SevenZipAESEncryptionSettings(string password)
```

#### Parameters

`password` [string](https://learn.microsoft.com/dotnet/api/system.string)

Password for encryption or decryption.

#### Examples


```csharp
using (var archive = new SevenZipArchive(new SevenZipEntrySettings(null, new SevenZipAESEncryptionSettings("p@s$"))))
{
   archive.CreateEntry("data.bin", "data.bin");
   archive.Save("archive.7z");
}
```

### <a id="Aspose_Zip_Saving_SevenZipAESEncryptionSettings__ctor_Aspose_Zip_Crypto_SevenZipCipher_"></a> SevenZipAESEncryptionSettings\(SevenZipCipher\)

Initializes a new instance of the Aspose.Zip.Saving.SevenZipAESEncryptionSettings class with external cipher.

```csharp
public SevenZipAESEncryptionSettings(SevenZipCipher cipher)
```

#### Parameters

`cipher` [SevenZipCipher](/zip/aspose.zip.crypto.sevenzipcipher)

Custom AES implementation.

#### Examples


```csharp
SevenZipCipher cipher = ComposeMyCipher();
using (var archive = new SevenZipArchive(new SevenZipEntrySettings(null, new SevenZipAESEncryptionSettings(cipher))))
{
   archive.CreateEntry("data.bin", "data.bin");
   archive.Save("archive.7z");
}
```
