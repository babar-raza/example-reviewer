---
linkTitle: "Class AesEcryptionSettings"
title: "Class AesEcryptionSettings"
description: "Settings for AES encryption and decryption algorithms within a ZIP archive."
summary: "Settings for AES encryption and decryption algorithms within a ZIP archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for AES encryption and decryption algorithms within a ZIP archive.

```csharp
public class AesEcryptionSettings : EncryptionSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[EncryptionSettings](/zip/aspose.zip.saving.encryptionsettings) ← 
[AesEcryptionSettings](/zip/aspose.zip.saving.aesecryptionsettings)

#### Inherited Members

[EncryptionSettings.Method](Aspose.Zip.Saving.EncryptionSettings.md\#Aspose\_Zip\_Saving\_EncryptionSettings\_Method), 
[EncryptionSettings.Password](Aspose.Zip.Saving.EncryptionSettings.md\#Aspose\_Zip\_Saving\_EncryptionSettings\_Password), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Saving_AesEcryptionSettings__ctor_System_String_Aspose_Zip_Saving_EncryptionMethod_"></a> AesEcryptionSettings\(string, EncryptionMethod\)

Initializes a new instance of the Aspose.Zip.Saving.AesEcryptionSettings class.

```csharp
public AesEcryptionSettings(string password, EncryptionMethod method)
```

#### Parameters

`password` [string](https://learn.microsoft.com/dotnet/api/system.string)

Password for encryption or decryption.

`method` [EncryptionMethod](/zip/aspose.zip.saving.encryptionmethod)

Algorithm option indicating block size of cipher.

#### Examples


```csharp
using (var archive = new Archive(new ArchiveEntrySettings(null, new AesEcryptionSettings("p@s$", EncryptionMethod.AES256))))
{
   archive.CreateEntry("data.bin", "data.bin");
   archive.Save("archive.zip");
}
```

#### Exceptions

 [NotSupportedException](https://learn.microsoft.com/dotnet/api/system.notsupportedexception)

<code class="paramref">method</code> is not one of Aspose.Zip.Saving.EncryptionMethod.AES128, Aspose.Zip.Saving.EncryptionMethod.AES192, or Aspose.Zip.Saving.EncryptionMethod.AES256.

### <a id="Aspose_Zip_Saving_AesEcryptionSettings__ctor_Aspose_Zip_Saving_EncryptionMethod_"></a> AesEcryptionSettings\(EncryptionMethod\)

Initializes a new instance of the Aspose.Zip.Saving.AesEcryptionSettings class without a password.

```csharp
public AesEcryptionSettings(EncryptionMethod method)
```

#### Parameters

`method` [EncryptionMethod](/zip/aspose.zip.saving.encryptionmethod)

Algorithm option indicating block size of cipher.
