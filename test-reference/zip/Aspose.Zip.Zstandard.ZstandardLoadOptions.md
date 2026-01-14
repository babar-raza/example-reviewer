---
linkTitle: "Class ZstandardLoadOptions"
title: "Class ZstandardLoadOptions"
description: "Options with which  is loaded from a compressed file. Contains event raised on extraction."
summary: "Options with which  is loaded from a compressed file. Contains event raised on extraction."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Zstandard](/zip/aspose.zip.zstandard)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options with which Aspose.Zip.Zstandard.ZstandardArchive is loaded from a compressed file. Contains event raised on extraction.

```csharp
public class ZstandardLoadOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ZstandardLoadOptions](/zip/aspose.zip.zstandard.zstandardloadoptions)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Zstandard_ZstandardLoadOptions__ctor"></a> ZstandardLoadOptions\(\)

```csharp
public ZstandardLoadOptions()
```

## Properties

### <a id="Aspose_Zip_Zstandard_ZstandardLoadOptions_CancellationToken"></a> CancellationToken

Gets or sets a cancellation token used to cancel the extraction operation.

```csharp
public CancellationToken CancellationToken { get; set; }
```

#### Property Value

 [CancellationToken](https://learn.microsoft.com/dotnet/api/system.threading.cancellationtoken)

#### Examples

Cancel Zstandard archive extraction after a certain time.

```csharp
using (CancellationTokenSource cts = new CancellationTokenSource())
{
    cts.CancelAfter(TimeSpan.FromSeconds(60)); 
    using (var a = new ZstandardArchive("big.zstd", new ZStandardLoadOptions() { CancellationToken = cts.Token }))
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
                                                   var loadOptions = new ZStandardLoadOptions() { CancellationToken = cts.Token };
                                                   using (var a = ZstandardArchive("big.zstd", loadOptions))
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

### <a id="Aspose_Zip_Zstandard_ZstandardLoadOptions_ExtractionProgressed"></a> ExtractionProgressed

Gets or sets the delegate invoked when some bytes have been extracted.

```csharp
public event EventHandler<ProgressEventArgs> ExtractionProgressed
```

#### Event Type

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[ProgressEventArgs](/zip/aspose.zip.progresseventargs)\>

#### Examples


```csharp
ZstandardArchive archive = new ZstandardArchive("archive.zst", 
new ZStandardLoadOptions() { EntryExtractionProgressed = (s, e) =&gt; { int percent = (int)((100 * e.ProceededBytes) / length); } })
```

#### Remarks

Event sender is the Aspose.Zip.Zstandard.ZstandardArchive instance which extraction is progressed.
