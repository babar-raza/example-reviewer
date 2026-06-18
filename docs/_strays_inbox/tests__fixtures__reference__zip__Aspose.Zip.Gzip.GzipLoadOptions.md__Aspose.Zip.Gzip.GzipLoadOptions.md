---
linkTitle: "Class GzipLoadOptions"
title: "Class GzipLoadOptions"
description: "Options for loading ."
summary: "Options for loading ."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Gzip](/zip/aspose.zip.gzip)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options for loading Aspose.Zip.Gzip.GzipArchive.

```csharp
public class GzipLoadOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[GzipLoadOptions](/zip/aspose.zip.gzip.gziploadoptions)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Remarks

In the .NET Framework 4.0 and above, can be used to cancel extraction.

## Constructors

### <a id="Aspose_Zip_Gzip_GzipLoadOptions__ctor"></a> GzipLoadOptions\(\)

```csharp
public GzipLoadOptions()
```

## Properties

### <a id="Aspose_Zip_Gzip_GzipLoadOptions_CancellationToken"></a> CancellationToken

Gets or sets a cancellation token used to cancel the extraction operation.

```csharp
public CancellationToken CancellationToken { get; set; }
```

#### Property Value

 [CancellationToken](https://learn.microsoft.com/dotnet/api/system.threading.cancellationtoken)

#### Examples

Cancel gzip archive extraction after a certain time.

```csharp
using (CancellationTokenSource cts = new CancellationTokenSource())
{
    cts.CancelAfter(TimeSpan.FromSeconds(60)); 
    using (var a = new GzipArchive("big.gz", new GzipLoadOptions() { CancellationToken = cts.Token }))
    {
        try
        {
             a.Extract("data.bin");
        }
        catch(OperationCanceledException)
        {
            Console.WriteLine("Extraction was cancelled after 60 seconds");
        }
    }
}
```<p>
Using with <code>Task</code>
```csharp
CancellationTokenSource cts = new CancellationTokenSource();
                                               cts.CancelAfter(TimeSpan.FromSeconds(60));
                                               Task t = Task.Run(delegate()
                                               {
                                                   var loadOptions = new GzipLoadOptions() { CancellationToken = cts.Token };
                                                   using (var a = GzipArchive("big.gz", loadOptions))
                                                   {
                                                        a.ExtractToDirectory("destination");
                                                   }
                                               }, cts.Token);

                                               t.ContinueWith(delegate(Task antecedent)
                                               {
                                                    if (antecedent.IsCanceled)
                                                    {
                                                        Console.WriteLine("Extraction was cancelled after 60 seconds");
                                                    }

                                                    cts.Dispose();
                                               });
```</p>
Cancellation mostly results in some data not being extracted.

#### Remarks

This property exists for .NET Framework 4.0 and above.

### <a id="Aspose_Zip_Gzip_GzipLoadOptions_ParseHeader"></a> ParseHeader

Gets or sets the value indicating whether to parse stream header to figure out properties, including name. Makes sense for seekable stream only.

```csharp
public bool ParseHeader { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)
