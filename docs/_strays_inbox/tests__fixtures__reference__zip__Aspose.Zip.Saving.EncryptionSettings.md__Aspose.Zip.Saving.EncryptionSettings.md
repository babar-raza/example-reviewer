---
linkTitle: "Class EncryptionSettings"
title: "Class EncryptionSettings"
description: "Base class for settings for several ZIP encryption methods."
summary: "Base class for settings for several ZIP encryption methods."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Base class for settings for several ZIP encryption methods.

```csharp
public abstract class EncryptionSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[EncryptionSettings](/zip/aspose.zip.saving.encryptionsettings)

#### Derived

[AesEcryptionSettings](/zip/aspose.zip.saving.aesecryptionsettings), 
[TraditionalEncryptionSettings](/zip/aspose.zip.saving.traditionalencryptionsettings)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Saving_EncryptionSettings__ctor_System_String_Aspose_Zip_Saving_EncryptionMethod_"></a> EncryptionSettings\(string, EncryptionMethod\)

Initializes a new instance of the Aspose.Zip.Saving.EncryptionSettings class.

```csharp
protected EncryptionSettings(string password, EncryptionMethod method)
```

#### Parameters

`password` [string](https://learn.microsoft.com/dotnet/api/system.string)

Password for encryption or decryption.

`method` [EncryptionMethod](/zip/aspose.zip.saving.encryptionmethod)

Method to encrypt or decrypt with.

## Properties

### <a id="Aspose_Zip_Saving_EncryptionSettings_Method"></a> Method

Gets the encryption algorithm.

```csharp
public EncryptionMethod Method { get; }
```

#### Property Value

 [EncryptionMethod](/zip/aspose.zip.saving.encryptionmethod)

### <a id="Aspose_Zip_Saving_EncryptionSettings_Password"></a> Password

Gets or sets password for encryption or decryption.

```csharp
public string Password { get; set; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)
