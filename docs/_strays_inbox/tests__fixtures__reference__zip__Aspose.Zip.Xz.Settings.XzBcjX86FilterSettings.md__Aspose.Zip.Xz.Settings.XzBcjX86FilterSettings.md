---
linkTitle: "Class XzBcjX86FilterSettings"
title: "Class XzBcjX86FilterSettings"
description: "Settings for xz Bcj X86 filter."
summary: "Settings for xz Bcj X86 filter."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Xz.Settings](/zip/aspose.zip.xz.settings)  
Assembly: Aspose.Zip.dll (25.12.0)  

Settings for xz Bcj X86 filter.

```csharp
public sealed class XzBcjX86FilterSettings : XzFilterSettings
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[XzFilterSettings](/zip/aspose.zip.xz.settings.xzfiltersettings) ← 
[XzBcjX86FilterSettings](/zip/aspose.zip.xz.settings.xzbcjx86filtersettings)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Xz_Settings_XzBcjX86FilterSettings__ctor"></a> XzBcjX86FilterSettings\(\)

Initializes a new instance of the Aspose.Zip.Xz.Settings.XzBcjX86FilterSettings. Use it to compress executable files and libraries within Aspose.Zip.Xz.XzArchive.

```csharp
public XzBcjX86FilterSettings()
```

#### Examples


```csharp
XzLZMA2FilterSettings lzma2 = new XzLZMA2FilterSettings(5242880);
XzBcjX86FilterSettings bcj = new XzBcjX86FilterSettings();
XzArchiveSettings settings = new XzArchiveSettings(new XzFilterSettings[] {bcj,lzma2}, 10485760, XzCheckType.Crc32);
using (XzArchive archive = new XzArchive(settings))
{
    archive.SetSource("data.bin");
    archive.Save("archive.xz");
}
```
