---
linkTitle: "Class Bzip2SaveOptions"
title: "Class Bzip2SaveOptions"
description: "Options for saving a bzip2 archive."
summary: "Options for saving a bzip2 archive."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Bzip2](/zip/aspose.zip.bzip2)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options for saving a bzip2 archive.

```csharp
public class Bzip2SaveOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[Bzip2SaveOptions](/zip/aspose.zip.bzip2.bzip2saveoptions)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Bzip2_Bzip2SaveOptions__ctor_System_Int32_"></a> Bzip2SaveOptions\(int\)

Initializes a new instance of the Aspose.Zip.Bzip2.Bzip2SaveOptions class.

```csharp
public Bzip2SaveOptions(int blockSize)
```

#### Parameters

`blockSize` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Block size in hundreds of kilobytes.

#### Examples


```csharp
using (FileStream result = File.Open("archive.bz2"))
{
    using (Bzip2Archive archive = new Bzip2Archive())
    {
        archive.SetSource("data.bin");
        archive.Save(result, new Bzip2SaveOptions(9));
    }
}
```

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

Block size is not in valid range.

### <a id="Aspose_Zip_Bzip2_Bzip2SaveOptions__ctor"></a> Bzip2SaveOptions\(\)

Initializes a new instance of the Aspose.Zip.Bzip2.Bzip2SaveOptions class with default block size, equals to 9 hundred of kilobytes.

```csharp
public Bzip2SaveOptions()
```

#### Examples


```csharp
using (FileStream result = File.Open("archive.bz2"))
{
    using (Bzip2Archive archive = new Bzip2Archive())
    {
        archive.SetSource("data.bin");
        archive.Save(result, new Bzip2SaveOptions());
    }
}
```

## Properties

### <a id="Aspose_Zip_Bzip2_Bzip2SaveOptions_BlockSize"></a> BlockSize

Block size in hundreds of kilobytes.

```csharp
public int BlockSize { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

### <a id="Aspose_Zip_Bzip2_Bzip2SaveOptions_CompressionThreads"></a> CompressionThreads

Gets or sets compression thread count. If the value is greater than 1, multithreading compression will be used.

```csharp
public int CompressionThreads { get; set; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Exceptions

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

The number of threads is more than 100 or less than 1.

### <a id="Aspose_Zip_Bzip2_Bzip2SaveOptions_CompressionProgressed"></a> CompressionProgressed

Raises when a portion of raw stream compressed.

```csharp
public event EventHandler<ProgressEventArgs> CompressionProgressed
```

#### Event Type

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[ProgressEventArgs](/zip/aspose.zip.progresseventargs)\>

#### Examples

`settings.CompressionProgressed += (s, e) =&gt; { int percent = (int)((100 * e.ProceededBytes) / entrySourceStream.Length); };`

#### Remarks

This event won't be raised when compressing in multithreaded mode.
