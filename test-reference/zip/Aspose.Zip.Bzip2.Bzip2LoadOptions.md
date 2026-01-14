---
linkTitle: "Class Bzip2LoadOptions"
title: "Class Bzip2LoadOptions"
description: "Options for loading . Contains event raised on extraction."
summary: "Options for loading . Contains event raised on extraction."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Bzip2](/zip/aspose.zip.bzip2)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options for loading Aspose.Zip.Bzip2.Bzip2Archive. Contains event raised on extraction.

```csharp
public class Bzip2LoadOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[Bzip2LoadOptions](/zip/aspose.zip.bzip2.bzip2loadoptions)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Bzip2_Bzip2LoadOptions__ctor"></a> Bzip2LoadOptions\(\)

```csharp
public Bzip2LoadOptions()
```

## Properties

### <a id="Aspose_Zip_Bzip2_Bzip2LoadOptions_CancellationToken"></a> CancellationToken

Gets or sets a cancellation token used to cancel the extraction operation.

```csharp
public CancellationToken CancellationToken { get; set; }
```

#### Property Value

 [CancellationToken](https://learn.microsoft.com/dotnet/api/system.threading.cancellationtoken)

#### Examples

Cancel Bzip2 archive extraction after a certain time.

```csharp
using (CancellationTokenSource cts = new CancellationTokenSource())
{
    cts.CancelAfter(TimeSpan.FromSeconds(60)); 
    using (var a = new Bzip2Archive("big.bz2", new Bzip2LoadOptions() { CancellationToken = cts.Token }))
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
                                                   var loadOptions = new Bzip2LoadOptions() { CancellationToken = cts.Token };
                                                   using (var a = Bzip2Archive("big.bz2", loadOptions))
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

### <a id="Aspose_Zip_Bzip2_Bzip2LoadOptions_ExtractionProgressed"></a> ExtractionProgressed

Event raised invoked when some bytes have been extracted.

```csharp
public event EventHandler<ProgressEventArgs> ExtractionProgressed
```

#### Event Type

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[ProgressEventArgs](/zip/aspose.zip.progresseventargs)\>

#### Examples


```csharp
Bzip2LoadOptions loadOptions = new Bzip2LoadOptions(); 
loadOptions.ExtractionProgressed += (s, e) =&gt; { percent = (int) ((double)(100 * e.ProceededBytes) / originalFileLength); };
```

#### Remarks

Event sender is the Aspose.Zip.Bzip2.Bzip2Archive instance which extraction is progressed. The Aspose.Zip.ProgressEventArgs.ProceededBytes is the number of bytes after extraction.
