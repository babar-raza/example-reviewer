---
linkTitle: "Class XzLZMA2FilterSettings"
title: "Class XzLZMA2FilterSettings"
description: "Set of settings for xz LZMA2 filter."
summary: "Set of settings for xz LZMA2 filter."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Xz.Settings](/zip/aspose.zip.xz.settings)  
Assembly: Aspose.Zip.dll (25.12.0)  

Set of settings for xz LZMA2 filter.

```csharp
public sealed class XzLZMA2FilterSettings : XzFilterSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[XzFilterSettings](/zip/aspose.zip.xz.settings.xzfiltersettings) ← 
[XzLZMA2FilterSettings](/zip/aspose.zip.xz.settings.xzlzma2filtersettings)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Xz_Settings_XzLZMA2FilterSettings__ctor_System_UInt32_"></a> XzLZMA2FilterSettings\(uint\)

Initializes a new instance of the Aspose.Zip.Xz.Settings.XzLZMA2FilterSettings.

```csharp
public XzLZMA2FilterSettings(uint dictionarySize = 16777216)
```

#### Parameters

`dictionarySize` [uint](https://learn.microsoft.com/dotnet/api/system.uint32)

Size of dictionary are used by LZMA2 filter, must be between 4096 and 1073741824.

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

Dictionary size is not in valid range.

## Properties

### <a id="Aspose_Zip_Xz_Settings_XzLZMA2FilterSettings_DictionarySize"></a> DictionarySize

Size of dictionary are used by LZMA2 filter.

```csharp
public uint DictionarySize { get; }
```

#### Property Value

 [uint](https://learn.microsoft.com/dotnet/api/system.uint32)
