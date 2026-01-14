---
linkTitle: "Class ArjLoadOptions"
title: "Class ArjLoadOptions"
description: "Options with which archive is loaded from a compressed file."
summary: "Options with which archive is loaded from a compressed file."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Arj](/zip/aspose.zip.arj)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options with which archive is loaded from a compressed file.

```csharp
public class ArjLoadOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ArjLoadOptions](/zip/aspose.zip.arj.arjloadoptions)

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

### <a id="Aspose_Zip_Arj_ArjLoadOptions__ctor"></a> ArjLoadOptions\(\)

```csharp
public ArjLoadOptions()
```

## Properties

### <a id="Aspose_Zip_Arj_ArjLoadOptions_CancellationToken"></a> CancellationToken

Gets or sets a cancellation token used to cancel the extraction operation.

```csharp
public CancellationToken CancellationToken { get; set; }
```

#### Property Value

 [CancellationToken](https://learn.microsoft.com/dotnet/api/system.threading.cancellationtoken)

#### Examples

Cancel ARJ archive extraction after a certain time.

```csharp
using (CancellationTokenSource cts = new CancellationTokenSource())
{
    cts.CancelAfter(TimeSpan.FromSeconds(60)); 
    using (var a = new ArjArchive("big.arj", new ArjLoadOptions() { CancellationToken = cts.Token }))
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
                                                   ArjLoadOptions loadOptions = new ArjLoadOptions() { CancellationToken = cts.Token };
                                                   using (ArjArchive a = new ArjArchive("big.arj", loadOptions))
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
