---
linkTitle: "Class CabEntrySettings"
title: "Class CabEntrySettings"
description: "Settings that control how a CAB entry is written."
summary: "Settings that control how a CAB entry is written."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Cab](/zip/aspose.zip.cab)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings that control how a CAB entry is written.

```csharp
public class CabEntrySettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[CabEntrySettings](/zip/aspose.zip.cab.cabentrysettings)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Cab_CabEntrySettings__ctor_Aspose_Zip_Cab_CabCompressionSettings_"></a> CabEntrySettings\(CabCompressionSettings\)

Initializes settings with a specific compression profile.

```csharp
public CabEntrySettings(CabCompressionSettings compressionSettings)
```

#### Parameters

`compressionSettings` [CabCompressionSettings](/zip/aspose.zip.cab.cabcompressionsettings)

Compression settings to use.
            <p>Can be one of these:</p><ul><li><span class="term">Aspose.Zip.Cab.CabStoreCompressionSettings</span></li><li><span class="term">Aspose.Zip.Cab.CabMsZipCompressionSettings</span></li></ul>

### <a id="Aspose_Zip_Cab_CabEntrySettings__ctor"></a> CabEntrySettings\(\)

Initializes settings with default MSZip compression.

```csharp
public CabEntrySettings()
```

## Properties

### <a id="Aspose_Zip_Cab_CabEntrySettings_CompressionSettings"></a> CompressionSettings

Gets the compression configuration applied to the entry.
<p>Can be one of these:</p><ul><li><span class="term">Aspose.Zip.Cab.CabStoreCompressionSettings</span></li><li><span class="term">Aspose.Zip.Cab.CabMsZipCompressionSettings</span></li></ul>

```csharp
public CabCompressionSettings CompressionSettings { get; }
```

#### Property Value

 [CabCompressionSettings](/zip/aspose.zip.cab.cabcompressionsettings)
