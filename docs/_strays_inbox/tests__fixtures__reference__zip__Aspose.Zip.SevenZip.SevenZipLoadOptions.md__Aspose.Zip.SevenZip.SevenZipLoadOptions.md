---
linkTitle: "Class SevenZipLoadOptions"
title: "Class SevenZipLoadOptions"
description: "Options with which  is loaded from a compressed file."
summary: "Options with which  is loaded from a compressed file."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.SevenZip](/zip/aspose.zip.sevenzip)  
Assembly: Aspose.Zip.dll (25.12.0)  

Options with which Aspose.Zip.SevenZip.SevenZipArchive is loaded from a compressed file.

```csharp
public class SevenZipLoadOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[SevenZipLoadOptions](/zip/aspose.zip.sevenzip.sevenziploadoptions)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_SevenZip_SevenZipLoadOptions__ctor"></a> SevenZipLoadOptions\(\)

```csharp
public SevenZipLoadOptions()
```

## Properties

### <a id="Aspose_Zip_SevenZip_SevenZipLoadOptions_CancellationToken"></a> CancellationToken

Gets or sets a cancellation token used to cancel the extraction operation.

```csharp
public CancellationToken CancellationToken { get; set; }
```

#### Property Value

 [CancellationToken](https://learn.microsoft.com/dotnet/api/system.threading.cancellationtoken)

#### Examples

Cancel 7Z archive extraction after a certain time.

```csharp
using (CancellationTokenSource cts = new CancellationTokenSource())
{
    cts.CancelAfter(TimeSpan.FromSeconds(60)); 
    using (var a = new SevenZipArchive("big.7z", new SevenZipLoadOptions() { CancellationToken = cts.Token }))
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
                                                   var loadOptions = new SevenZipLoadOptions() { CancellationToken = cts.Token };
                                                   using (var a = new SevenZipArchive("big.7z", loadOptions))
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

### <a id="Aspose_Zip_SevenZip_SevenZipLoadOptions_DecryptionPassword"></a> DecryptionPassword

Gets or sets the password to decrypt entries and entry names.

```csharp
public string DecryptionPassword { get; set; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

#### Examples

<p>You can provide decryption password once on archive extraction.</p>

```csharp
using (FileStream fs = File.OpenRead("encrypted_archive.7z"))
{
    using (var extracted = File.Create("extracted.bin"))
    {
        using (SevenZipArchive archive = new SevenZipArchive(fs, new SevenZipLoadOptions() { DecryptionPassword = "p@s$" }))
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

[SevenZipArchiveEntry](/zip/aspose.zip.sevenzip.sevenziparchiveentry).[Open](Aspose.Zip.SevenZip.SevenZipArchiveEntry.md\#Aspose\_Zip\_SevenZip\_SevenZipArchiveEntry\_Open\_System\_String\_)\([string](https://learn.microsoft.com/dotnet/api/system.string)\)
