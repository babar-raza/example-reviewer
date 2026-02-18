---
linkTitle: "Class IsoLoadOptions"
title: "Class IsoLoadOptions"
description: "Options with which  is loaded from a compressed file. Contains event raised on extraction."
summary: "Options with which  is loaded from a compressed file. Contains event raised on extraction."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Iso](/zip/aspose.zip.iso)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options with which Aspose.Zip.Iso.IsoArchive is loaded from a compressed file. Contains event raised on extraction.

```csharp
public class IsoLoadOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[IsoLoadOptions](/zip/aspose.zip.iso.isoloadoptions)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Iso_IsoLoadOptions__ctor"></a> IsoLoadOptions\(\)

```csharp
public IsoLoadOptions()
```

## Properties

### <a id="Aspose_Zip_Iso_IsoLoadOptions_CancellationToken"></a> CancellationToken

Gets or sets a cancellation token used to cancel the extraction operation.

```csharp
public CancellationToken CancellationToken { get; set; }
```

#### Property Value

 [CancellationToken](https://learn.microsoft.com/dotnet/api/system.threading.cancellationtoken)

#### Examples

Cancel ISO archive extraction after a certain time.

```csharp
using (CancellationTokenSource cts = new CancellationTokenSource())
{
    cts.CancelAfter(TimeSpan.FromSeconds(60)); 
    using (var a = new IsoArchive("big.iso", new IsoLoadOptions() { CancellationToken = cts.Token }))
    {
        try
        {
             a.Entries[0].Extract("data.bin");
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
                                                   var loadOptions = new ArchiveLoadOptions() { CancellationToken = cts.Token };
                                                   using (var a = Archive("big.iso", loadOptions))
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

### <a id="Aspose_Zip_Iso_IsoLoadOptions_EntryExtractionProgressed"></a> EntryExtractionProgressed

Gets or sets the delegate invoked when some bytes have been extracted.

```csharp
public EventHandler<ProgressEventArgs> EntryExtractionProgressed { get; set; }
```

#### Property Value

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[ProgressEventArgs](/zip/aspose.zip.progresseventargs)\>

#### Examples


```csharp
IsoArchive archive = new IsoArchive("archive.iso", 
new IsoLoadOptions() { EntryExtractionProgressed = (s, e) =&gt; { int percent = (int)((100 * e.ProceededBytes) / length); } })
```

#### Remarks

Event sender is the Aspose.Zip.Iso.IsoEntry instance which extraction is progressed.
