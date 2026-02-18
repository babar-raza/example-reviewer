---
linkTitle: "Enum ZipDataDescriptorPolicy"
title: "Enum ZipDataDescriptorPolicy"
description: "Options for the Data Descriptor presence."
summary: "Options for the Data Descriptor presence."
categories:
  - Enum
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options for the Data Descriptor presence.

```csharp
public enum ZipDataDescriptorPolicy : byte
```

## Fields

`Always = 0` 

Data Descriptor is always present for all zip entries.



`ForAllFileEntries = 1` 

Data Descriptor present only for entries with file data; 
omitted for directories. Usage of this option is discouraged.

Can only be applied to non-encrypted archives.
