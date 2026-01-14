---
linkTitle: "Class SelfExtractorOptions"
title: "Class SelfExtractorOptions"
description: "Options for creation of self-extracting executable archive."
summary: "Options for creation of self-extracting executable archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options for creation of self-extracting executable archive.

```csharp
public class SelfExtractorOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[SelfExtractorOptions](/zip/aspose.zip.saving.selfextractoroptions)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Examples


```csharp
using (FileStream zipFile = File.Open("archive.exe", FileMode.Create))
{
    using (var archive = new Archive())
    {
        archive.CreateEntry("entry.bin", "data.bin");
        var sfxOptions = new SelfExtractorOptions() { ExtractorTitle = "Extractor", CloseWindowOnExtraction = true, TitleIcon = "C:\pictogram.ico" };
        archive.Save(zipFile, new ArchiveSaveOptions() { SelfExtractorOptions = sfxOptions });
    }
}
```

## Constructors

### <a id="Aspose_Zip_Saving_SelfExtractorOptions__ctor"></a> SelfExtractorOptions\(\)

```csharp
public SelfExtractorOptions()
```

## Properties

### <a id="Aspose_Zip_Saving_SelfExtractorOptions_CloseWindowOnExtraction"></a> CloseWindowOnExtraction

Gets or sets a value indicating whether an extractor window must be closed upon extraction or not.

```csharp
public bool CloseWindowOnExtraction { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_Saving_SelfExtractorOptions_ExtractorTitle"></a> ExtractorTitle

Gets or sets the title of extractor's window.

```csharp
public string ExtractorTitle { get; set; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_Saving_SelfExtractorOptions_RunAfterExtraction"></a> RunAfterExtraction

Gets or sets a program to be executed after the archive extraction is completed.

```csharp
public string RunAfterExtraction { get; set; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_Saving_SelfExtractorOptions_TitleIcon"></a> TitleIcon

Gets or sets the path to title icon for main windows of extractor application.

```csharp
public string TitleIcon { get; set; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)
