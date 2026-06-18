---
linkTitle: "Class ArchiveLoadOptions"
title: "Class ArchiveLoadOptions"
description: "Options with which archive is loaded from a compressed file."
summary: "Options with which archive is loaded from a compressed file."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip](/zip/)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options with which archive is loaded from a compressed file.

```csharp
public class ArchiveLoadOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[ArchiveLoadOptions](/zip/aspose.zip.archiveloadoptions)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_ArchiveLoadOptions__ctor"></a> ArchiveLoadOptions\(\)

```csharp
public ArchiveLoadOptions()
```

## Properties

### <a id="Aspose_Zip_ArchiveLoadOptions_CancellationToken"></a> CancellationToken

Gets or sets a cancellation token used to cancel the extraction operation.

```csharp
public CancellationToken CancellationToken { get; set; }
```

#### Property Value

 [CancellationToken](https://learn.microsoft.com/dotnet/api/system.threading.cancellationtoken)

#### Examples

Cancel ZIP archive extraction after a certain time.

```csharp
using (CancellationTokenSource cts = new CancellationTokenSource())
{
    cts.CancelAfter(TimeSpan.FromSeconds(60)); 
    using (var a = new SevenZipArchive("big.zip", new SevenZipLoadOptions() { CancellationToken = cts.Token }))
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
                                                   using (var a = Archive("big.zip", loadOptions))
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

### <a id="Aspose_Zip_ArchiveLoadOptions_DecryptionPassword"></a> DecryptionPassword

Gets or sets the password to decrypt entries.

```csharp
public string DecryptionPassword { get; set; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

#### Examples

<p>You can provide decryption password once on archive extraction.</p>

```csharp
using (FileStream fs = File.OpenRead("encrypted_archive.zip"))
{
    using (var extracted = File.Create("extracted.bin"))
    {
        using (var archive = new Archive(fs, new ArchiveLoadOptions() { DecryptionPassword = "p@s$" }))
        {
            using (var decompressed = archive.Entries[0].Open())
            {
                byte[] b = new byte[8192];
                int bytesRead;
                while (0 &lt; (bytesRead = decompressed.Read(b, 0, b.Length)))
                    extracted.Write(b, 0, bytesRead);

            }
        }
    }
}
```

#### See Also

[ArchiveEntry](/zip/aspose.zip.archiveentry).[Open](Aspose.Zip.ArchiveEntry.md\#Aspose\_Zip\_ArchiveEntry\_Open\_System\_String\_)\([string](https://learn.microsoft.com/dotnet/api/system.string)\)

### <a id="Aspose_Zip_ArchiveLoadOptions_Encoding"></a> Encoding

Gets or sets the encoding for entries' names.

```csharp
public Encoding Encoding { get; set; }
```

#### Property Value

 [Encoding](https://learn.microsoft.com/dotnet/api/system.text.encoding)

#### Examples

<p>Entry name composed using specified encoding regardless of zip file properties.</p>

```csharp
using (FileStream fs = File.OpenRead("archive.zip"))
{      
    using (var archive = new Archive(fs, new ArchiveLoadOptions() { Encoding = System.Text.Encoding.GetEncoding(932) }))
    {
        string name = archive.Entries[0].Name;
    }    
}
```

### <a id="Aspose_Zip_ArchiveLoadOptions_EntryExtractionProgressed"></a> EntryExtractionProgressed

Gets or sets the delegate invoked when some bytes have been extracted.

```csharp
public EventHandler<ProgressCancelEventArgs> EntryExtractionProgressed { get; set; }
```

#### Property Value

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[ProgressCancelEventArgs](/zip/aspose.zip.progresscanceleventargs)\>

#### Examples

Track the progress of an entry extraction.

```csharp
var archive = new Archive("archive.zip", 
new ArchiveLoadOptions() { EntryExtractionProgressed = (s, e) =&gt; { int percent = (int)((100 * e.ProceededBytes) / ((ArchiveEntry)s).UncompressedSize); } })
```

<p>Cancel an entry extraction after a certain time.</p>

```csharp
Stopwatch watch = Stopwatch.StartNew();
using (Archive a = new Archive("big.zip", new ArchiveLoadOptions() {
    EntryExtractionProgressed = (s, e) =&gt; { if (watch.ElapsedMilliseconds &gt; 1000) e.Cancel = true; } }))
{
    a.Entries[0].Extract("first.bin");
}
```

#### Remarks

Event sender is the Aspose.Zip.ArchiveEntry instance which extraction is progressed.

### <a id="Aspose_Zip_ArchiveLoadOptions_EntryListed"></a> EntryListed

Gets or sets the delegate invoked when an entry listed within table of content.

```csharp
public EventHandler<EntryEventArgs> EntryListed { get; set; }
```

#### Property Value

 [EventHandler](https://learn.microsoft.com/dotnet/api/system.eventhandler\-1)<[EntryEventArgs](/zip/aspose.zip.entryeventargs)\>

#### Examples

`var archive = new Archive("archive.zip", new ArchiveLoadOptions() { EntryListed = (s, e) =&gt; { Console.WriteLine(e.Entry.Name); } });`

### <a id="Aspose_Zip_ArchiveLoadOptions_SkipChecksumVerification"></a> SkipChecksumVerification

Get or set a value indicating whether checksum verification of ZIP entries be skipped and mismatch ignored. Default is false.

```csharp
public bool SkipChecksumVerification { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)
