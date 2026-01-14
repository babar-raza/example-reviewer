---
linkTitle: "Enum ParallelCompressionMode"
title: "Enum ParallelCompressionMode"
description: "Options of usage parallel compression facility."
summary: "Options of usage parallel compression facility."
categories:
  - Enum
layout: "reference-single"
---

Namespace: [Aspose.Zip.Saving](/zip/aspose.zip.saving)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options of usage parallel compression facility.

```csharp
public enum ParallelCompressionMode
```

## Fields

`Always = 1` 

Do compress in parallel. Beware of a drain on memory.



`Auto = 2` 

Decide whether parallel compression will be used based on the entries.
This option may compress in parallel some entries only.



`Never = 0` 

Do not compress in parallel.


