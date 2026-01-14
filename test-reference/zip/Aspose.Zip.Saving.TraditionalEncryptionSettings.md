---
linkTitle: "Class TraditionalEncryptionSettings"
title: "Class TraditionalEncryptionSettings"
description: "Settings for traditional ZipCrypto algorithm within a ZIP archive."
summary: "Settings for traditional ZipCrypto algorithm within a ZIP archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for traditional ZipCrypto algorithm within a ZIP archive.

```csharp
public class TraditionalEncryptionSettings : EncryptionSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[EncryptionSettings](/zip/aspose.zip.saving.encryptionsettings) ← 
[TraditionalEncryptionSettings](/zip/aspose.zip.saving.traditionalencryptionsettings)

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

## Remarks

See section 6.0 at <a href="https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT">ZIP format description</a>

## Constructors

### <a id="Aspose_Zip_Saving_TraditionalEncryptionSettings__ctor_System_String_"></a> TraditionalEncryptionSettings\(string\)

Initializes a new instance of the Aspose.Zip.Saving.TraditionalEncryptionSettings class.

```csharp
public TraditionalEncryptionSettings(string password)
```

#### Parameters

`password` [string](https://learn.microsoft.com/dotnet/api/system.string)

Password for encryption.

#### Examples


```csharp
using (var archive = new Archive(new ArchiveEntrySettings(null, new TraditionalEncryptionSettings("p@s$"))))
{
    archive.CreateEntry("data.bin", "data.bin");
    archive.Save(zipFile);
}
```

### <a id="Aspose_Zip_Saving_TraditionalEncryptionSettings__ctor_System_String_System_Text_Encoding_"></a> TraditionalEncryptionSettings\(string, Encoding\)

Initializes a new instance of the Aspose.Zip.Saving.TraditionalEncryptionSettings class with user defined encoding.

```csharp
public TraditionalEncryptionSettings(string password, Encoding encoding)
```

#### Parameters

`password` [string](https://learn.microsoft.com/dotnet/api/system.string)

Password for encryption.

`encoding` [Encoding](https://learn.microsoft.com/dotnet/api/system.text.encoding)

Encoding for password characters.

#### Examples


```csharp
using (var archive = new Archive(new ArchiveEntrySettings(null, new TraditionalEncryptionSettings("p£s$", System.Text.Encoding.ASCII))))
{
    archive.CreateEntry("data.bin", "data.bin");
    archive.Save(zipFile);
}
```

#### Remarks

Usage of this constructor is discouraged. Setting the encoding may contradict the standard and produce incompatible archive.

### <a id="Aspose_Zip_Saving_TraditionalEncryptionSettings__ctor"></a> TraditionalEncryptionSettings\(\)

Initializes a new instance of the Aspose.Zip.Saving.TraditionalEncryptionSettings class without a password.

```csharp
public TraditionalEncryptionSettings()
```
