---
linkTitle: "Class ArchiveSaveOptions"
title: "Class ArchiveSaveOptions"
description: "Options for saving a ZIP archive."
summary: "Options for saving a ZIP archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options for saving a ZIP archive.

```csharp
public class ArchiveSaveOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ArchiveSaveOptions](/zip/aspose.zip.saving.archivesaveoptions)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Saving_ArchiveSaveOptions__ctor"></a> ArchiveSaveOptions\(\)

```csharp
public ArchiveSaveOptions()
```

## Properties

### <a id="Aspose_Zip_Saving_ArchiveSaveOptions_ArchiveComment"></a> ArchiveComment

Gets or sets optional comment for the Zip file.

```csharp
public string ArchiveComment { get; set; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Zip_Saving_ArchiveSaveOptions_CloseEntrySource"></a> CloseEntrySource

Gets or sets a value indicating whether entries' sources should be closed right after an entry has been compressed.

```csharp
public bool CloseEntrySource { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_Saving_ArchiveSaveOptions_DataDescriptorPolicy"></a> DataDescriptorPolicy

Gets or sets settings for Data Descriptor emission.

```csharp
public ZipDataDescriptorPolicy DataDescriptorPolicy { get; set; }
```

#### Property Value

 [ZipDataDescriptorPolicy](/zip/aspose.zip.saving.zipdatadescriptorpolicy)

#### Remarks

Default option is always present data descriptor.
<p>Aspose.Zip.Saving.ZipDataDescriptorPolicy.ForAllFileEntries is not compatible with archive encryption.
</p>

### <a id="Aspose_Zip_Saving_ArchiveSaveOptions_Encoding"></a> Encoding

Gets or sets encoding for converting file names and other strings to bytes.

```csharp
public Encoding Encoding { get; set; }
```

#### Property Value

 [Encoding](https://learn.microsoft.com/dotnet/api/system.text.encoding)

#### Remarks

If not set, code page 437 will be used.

### <a id="Aspose_Zip_Saving_ArchiveSaveOptions_EncryptionOptions"></a> EncryptionOptions

Gets of sets encryption settings for saving existing ZIP archive.

```csharp
public EncryptionSettings EncryptionOptions { get; set; }
```

#### Property Value

 [EncryptionSettings](/zip/aspose.zip.saving.encryptionsettings)

#### Examples


```csharp
using (var archive = new Archive("plain.zip"))
{                   
     archive.Save("encrypted.zip", new ArchiveSaveOptions() { EncryptionOptions = new AesEcryptionSettings("p@s$", EncryptionMethod.AES256) });
}
```

#### Remarks

<p>
        Do not use this options for regular composition of encrypted archive, use Aspose.Zip.Saving.ArchiveEntrySettings.EncryptionSettings instead.
        </p>
<p>
        Not compatible with Aspose.Zip.Saving.ArchiveSaveOptions.DataDescriptorPolicy having value Aspose.Zip.Saving.ZipDataDescriptorPolicy.ForAllFileEntries</p>

### <a id="Aspose_Zip_Saving_ArchiveSaveOptions_EventsBag"></a> EventsBag

Gets or sets container of events raising on archive saving.

```csharp
public EventsBag EventsBag { get; set; }
```

#### Property Value

 [EventsBag](/zip/aspose.zip.saving.eventsbag)

### <a id="Aspose_Zip_Saving_ArchiveSaveOptions_ParallelOptions"></a> ParallelOptions

Gets or sets settings for parallel compression.

```csharp
public ParallelOptions ParallelOptions { get; set; }
```

#### Property Value

 [ParallelOptions](/zip/aspose.zip.saving.paralleloptions)

#### Remarks

Assign it if you want to utilize several CPU cores while compressing several archive entries.

### <a id="Aspose_Zip_Saving_ArchiveSaveOptions_SelfExtractorOptions"></a> SelfExtractorOptions

Gets or sets settings for self extracted archive.

```csharp
public SelfExtractorOptions SelfExtractorOptions { get; set; }
```

#### Property Value

 [SelfExtractorOptions](/zip/aspose.zip.saving.selfextractoroptions)

#### Remarks

Assign it if you need to compose executable program to extract an archive without any software installed on the target computer.
