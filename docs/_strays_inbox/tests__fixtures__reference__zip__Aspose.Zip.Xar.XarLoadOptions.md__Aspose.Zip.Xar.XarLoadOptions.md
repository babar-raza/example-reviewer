---
linkTitle: "Class XarLoadOptions"
title: "Class XarLoadOptions"
description: "Options with which XAR archive is loaded from a compressed file."
summary: "Options with which XAR archive is loaded from a compressed file."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Xar](/zip/aspose.zip.xar)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options with which XAR archive is loaded from a compressed file.

```csharp
public class XarLoadOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[XarLoadOptions](/zip/aspose.zip.xar.xarloadoptions)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Xar_XarLoadOptions__ctor"></a> XarLoadOptions\(\)

```csharp
public XarLoadOptions()
```

## Properties

### <a id="Aspose_Zip_Xar_XarLoadOptions_CancellationToken"></a> CancellationToken

Gets or sets a cancellation token used to cancel the extraction operation.

```csharp
public CancellationToken CancellationToken { get; set; }
```

#### Property Value

 [CancellationToken](https://learn.microsoft.com/dotnet/api/system.threading.cancellationtoken)

#### Examples

Cancel XAR archive extraction after a certain time.

```csharp
using (CancellationTokenSource cts = new CancellationTokenSource())
{
    cts.CancelAfter(TimeSpan.FromSeconds(60)); 
    using (var a = new XarArchive("big.xar", new XarLoadOptions() { CancellationToken = cts.Token }))
    {
        try
        {
             (XarFileEntry)(a.Entries.First()).Extract("data.bin");
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
                                                   var loadOptions = new XarLoadOptions() { CancellationToken = cts.Token };
                                                   using (var a = new XarArchive("big.xar", loadOptions))
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

### <a id="Aspose_Zip_Xar_XarLoadOptions_EntryExtractionProgressed"></a> EntryExtractionProgressed

Gets or sets the delegate invoked when some bytes have been extracted.

```csharp
public EventHandler<ProgressEventArgs> EntryExtractionProgressed { get; set; }
```

#### Property Value

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[ProgressEventArgs](/zip/aspose.zip.progresseventargs)\>

#### Examples


```csharp
XarArchive archive = new XarArchive("archive.xar", 
new XarLoadOptions() { EntryExtractionProgressed = (s, e) =&gt; { int percent = (int)((100 * e.ProceededBytes) / ((XarFileEntry)s).Length); } })
```

#### Remarks

Event sender is the Aspose.Zip.Xar.XarFileEntry instance which extraction is progressed.
