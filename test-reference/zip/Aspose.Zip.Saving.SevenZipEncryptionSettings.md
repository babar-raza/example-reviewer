---
linkTitle: "Class SevenZipEncryptionSettings"
title: "Class SevenZipEncryptionSettings"
description: "Base class for settings for several 7z encryption methods."
summary: "Base class for settings for several 7z encryption methods."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Base class for settings for several 7z encryption methods.

```csharp
public abstract class SevenZipEncryptionSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[SevenZipEncryptionSettings](/zip/aspose.zip.saving.sevenzipencryptionsettings)

#### Derived

[SevenZipAESEncryptionSettings](/zip/aspose.zip.saving.sevenzipaesencryptionsettings)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Remarks

The AES-256 is the only possible encryption method for 7z archive. So the Aspose.Zip.Saving.SevenZipAESEncryptionSettings is the only implementation.

## Constructors

### <a id="Aspose_Zip_Saving_SevenZipEncryptionSettings__ctor_System_String_"></a> SevenZipEncryptionSettings\(string\)

Initializes a new instance of the Aspose.Zip.Saving.SevenZipEncryptionSettings class.

```csharp
protected SevenZipEncryptionSettings(string password)
```

#### Parameters

`password` [string](https://learn.microsoft.com/dotnet/api/system.string)

Password for encryption or decryption.

### <a id="Aspose_Zip_Saving_SevenZipEncryptionSettings__ctor"></a> SevenZipEncryptionSettings\(\)

Initializes a new instance of the Aspose.Zip.Saving.SevenZipEncryptionSettings class.

```csharp
protected SevenZipEncryptionSettings()
```

## Properties

### <a id="Aspose_Zip_Saving_SevenZipEncryptionSettings_EncryptHeader"></a> EncryptHeader

Gets or sets a value indicating header encryption.

```csharp
public bool EncryptHeader { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

#### Remarks

This setting is equivalent <code>-mhe=on</code> switch of 7-Zip tool. Currently, it is incompatible with header compression.

### <a id="Aspose_Zip_Saving_SevenZipEncryptionSettings_Password"></a> Password

Gets or sets password for encryption or decryption.

```csharp
public string Password { get; set; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)
