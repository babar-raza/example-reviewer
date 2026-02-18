---
title: "Add Files or Folders to ZIP Archives Programmatically in C#"
seoTitle: "Create ZIP Archive in C# | C# ZIP Single or Multiple Files | ZIP Library"
description: "C# Create ZIP files with the Aspose Plugin. ZIP single or multiple files, create AES encrypted ZIP archives to compress files or folders, and secure your ZIP files with password protection. Explore the powerful Aspose .NET Plugin for efficient ZIP file handling starting at just $99."
date: "2020-04-22T12:48:02+00:00"
draft: false
author: "Usman Aziz"
summary: "Learn how to programmatically create ZIP archives in C# using the Aspose .NET Plugin. Discover best practices for handling large files, securing your ZIP archives, and optimizing your workflow with .NET Plugin features starting at just $99."
tags:
- "Add multiple files to ZIP csharp"
- "Add single file to ZIP csharp"
- "Create AES encrypted ZIP files"
- "Create ZIP Archives in Csharp"
- "Csharp ASP.NET ZIP Library"
categories:
- "Aspose.ZIP Plugin Family"
enhanced: true
lastmod: '2025-04-08'
---
{{< figure align=center src="images/Create-ZIP-in-C.jpg" alt="Create ZIP in C#">}}

## Introduction to ZIP Archives

**[ZIP archives][1]** are crucial for compressing and consolidating multiple files or folders into a single container. This format not only minimizes file size for storage and transmission but also preserves metadata, simplifying file management. ZIP archives are widely utilized in both desktop and web applications for tasks like uploading, downloading, sharing, and securing files through encryption.

In this article, we will delve into various methods for **programmatically creating ZIP archives in C#**. By the end, you'll know how to:

*   [Create a ZIP archive using C#](#Create-a-ZIP-archive-using-CSharp)
*   [Add multiple files to a ZIP archive](#Add-multiple-files-to-a-ZIP-archive)
*   [Add folders to a ZIP archive](#Add-folders-to-a-ZIP-archive)
*   [Create a password-protected ZIP archive using ZipCrypto](#Create-a-Password-Protected-ZIP-Archive-using-ZipCrypto-in-CSharp)
*   [Encrypt a ZIP archive with AES encryption](#Create-AES-Encrypted-ZIP-Archives-in-CSharp)
*   [Set parallel compression mode](#Set-parallel-compression-mode)
*   [How to Zip Files in .NET with C#](#How-to-Zip-Files-in-.NET-with-CSharp)

## C# ZIP Library

The **[Aspose.ZIP for .NET][3]** is a powerful API tailored for zipping and unzipping files and folders within .NET applications. It features AES encryption to secure your files within ZIP archives. You can easily install the API from [NuGet][4] or download the binaries from the [Downloads][5] section.

## Create a ZIP Archive in C# {#Create-a-ZIP-archive-using-CSharp}

To compress a file into a ZIP archive, follow these steps:

1. Create a [FileStream][6] object for the output ZIP archive.
2. Open the source file with a _FileStream_ object.
3. Instantiate the [Archive][7] class.
4. Add the file to the archive using the [Archive.CreateEntry(string, FileStream)][8] method.
5. Save the ZIP archive with the [Archive.Save(FileStream)][9] method.

Here’s a code sample demonstrating how to add a file to a ZIP archive using C#:

{{< gist aspose-com-gists dea0000f742629e43ecc24f5a19ab2ac "create-zip-archive-in-csharp.cs" >}}

## Add Multiple Files to a ZIP Archive in C# {#Add-multiple-files-to-a-ZIP-archive}

To add multiple files to a ZIP archive, you can choose from the following methods:

### Using FileStream

Utilize the _FileStream_ class to **zip files in C#** by adding multiple files to the ZIP archive with the [Archive.CreateEntry(String, FileStream)][10] method. Here’s how:

{{< gist aspose-com-gists dea0000f742629e43ecc24f5a19ab2ac "add-mulitple-files-to-zip.cs" >}}

### Using FileInfo

Alternatively, use the [FileInfo][11] class to add files. This method loads the files using the _FileInfo_ class and adds them to the ZIP archive with the [Archive.CreateEntry(String, FileInfo)][12] method. See the example below:

{{< gist aspose-com-gists dea0000f742629e43ecc24f5a19ab2ac "add-mulitple-files-to-zip-fileinfo.cs" >}}

### Using File Path

You can also add files directly by providing their paths to the [Archive.CreateEntry(String name, String path, Boolean openImmediately, ArchiveEntrySettings newEntrySettings)][13] method. Here’s how to **create a ZIP file in C#**:

{{< gist aspose-com-gists dea0000f742629e43ecc24f5a19ab2ac "add-files-to-zip-filepath.cs" >}}

## Add Folders to a ZIP Archive in C# {#Add-folders-to-a-ZIP-archive}

Adding a folder to a ZIP archive is a convenient way to include multiple files. To **zip files in C#**, follow these steps:

1. Create a [FileStream][14] object for the output ZIP archive.
2. Instantiate the [Archive][15] class.
3. Use the [DirectoryInfo][16] class to specify the folder to be zipped.
4. Add the folder to the ZIP using the [Archive.CreateEntries(DirectoryInfo)][17] method.
5. Save the ZIP archive with the [Archive.Save(FileStream)][18] method.

Here’s a code sample that demonstrates how to add a folder to a ZIP archive in C#:

{{< gist aspose-com-gists dea0000f742629e43ecc24f5a19ab2ac "compress-folder-into-zip.cs" >}}

## Create a Password Protected ZIP using ZipCrypto in C# {#Create-a-Password-Protected-ZIP-Archive-using-ZipCrypto-in-CSharp}

To enhance security, you can create password-protected ZIP archives using **ZipCrypto** encryption. This is achieved by using the [ArchiveEntrySettings][19] class in the constructor of the [Archive][20], which allows you to specify the encryption type.

Here’s an example of how to create a password-protected ZIP archive using ZipCrypto in C#:

{{< gist aspose-com-gists dea0000f742629e43ecc24f5a19ab2ac "create-password-protected-zip.cs" >}}

## Create Password Protected ZIP with AES Encryption {#Create-AES-Encrypted-ZIP-Archives-in-CSharp}

The Aspose.ZIP for .NET library also supports AES encryption for securing ZIP archives. You can choose from the following AES encryption methods:

*   AES128
*   AES192
*   AES256

To apply AES encryption, use the [AesEcryptionSettings][21] class. Here’s how to create a password-protected ZIP with AES encryption in C#:

{{< gist aspose-com-gists dea0000f742629e43ecc24f5a19ab2ac "encrypt-zip-with-aes-encryption.cs" >}}

## Set Parallel Compression Mode {#Set-parallel-compression-mode}

For cases involving multiple entries, configure the API for parallel compression using the [ParallelOptions][22] class. Aspose.ZIP for .NET provides several parallel compression modes:

*   **Never** - Do not compress in parallel.
*   **Always** - Always compress in parallel (be cautious of out-of-memory issues).
*   **Auto** - Automatically decide whether to use parallel compression based on the entries.

Here’s an example demonstrating how to set the parallel compression mode while zipping multiple files:

{{< gist aspose-com-gists 42ee14864d84aeae8619284450c3d628 "Examples-CSharp-CompressingAndDecompressingFiles-UsingParallelismToCompressFiles-UsingParallelismToCompressFiles.cs" >}}

## Learn More About C# .NET ZIP Library 

Dive deeper into our C# .NET ZIP API with the following resources:

*   [Documentation](https://docs.aspose.net/display/zipnet/Getting+Started)
*   [Source code examples](https://github.com/aspose-zip/Aspose.ZIP-for-.NET)

## Try ZIP Archives Online

Explore our [free online application](https://products.aspose.app/zip/compression/zip), based on Aspose.ZIP for .NET, to compress files into ZIP archives effortlessly.

## Conclusion

In this article, you have learned how to **programmatically create ZIP archives in C#**. The provided code samples illustrate how to zip files in C#, add files and folders to ZIP archives, and create password-protected ZIP archives using both ZipCrypto and AES encryption methods. We also discussed parallel compression for efficiently handling large files and even touched upon **how to zip files in .NET with C#**. If you have any questions or need further assistance, feel free to reach out via our [forum][23].

## See Also

|  |  |  |
|----------|----------|----------|
| [Unrar or Extract Files using C#](https://blog.aspose.com/zip/unrar-extract-rar-extractor-opener-in-csharp-asp.net/) | [Unzip Files in ZIP Archives using C#](https://blog.aspose.com/zip/unzip-files-in-password-protected-zip-archives-in-csharp-asp.net/) | [Create 7z (7-Zip) Archives in C# .NET](https://blog.aspose.com/zip/create-7zip-archives-programmatically-using-csharp-asp.net/) | 
| [Open or Extract 7z (7zip) File in C# .NET](https://blog.aspose.com/zip/open-extract-7zip-7z-file-unzip-in-csharp-asp-net/) | [Create and Extract GZip Archives using C#](https://blog.aspose.com/zip/create-and-extract-gzip-archives-using-csharp/) | [Convert RAR Files to ZIP Archive in C#](https://blog.aspose.com/zip/convert-rar-files-to-zip-in-csharp/) |
| [Convert ZIP Archives to TAR in C#](https://blog.aspose.com/zip/convert-zip-to-tar-in-csharp-net/) | [Create a Flat ZIP Archive in C#](https://blog.aspose.com/zip/create-a-flat-zip-archive-in-csharp/) | [Create Executable Self-Extracting Archive in C#](https://blog.aspose.com/zip/create-self-extracting-archive-in-csharp/) |
| [Create TAR.GZ and TAR.XZ Files in C#](https://blog.aspose.com/zip/create-tar-gz-xz-files-in-csharp/) | [Delete Files in a ZIP Archive in C#](https://blog.aspose.com/zip/delete-files-in-zip-archive-csharp-net/) | [Extract Nested ZIP Archives in C#](https://blog.aspose.com/zip/extract-nested-zip-archives-in-csharp-net/) |
| [Merge Multiple ZIP or TAR Archives in C#](https://blog.aspose.com/zip/merge-zip-and-tar-files-in-csharp/) | [How to Create ZIP Files](https://blog.aspose.com/zip/how-to-create-zip-files/) | [Extract 7z Online](https://blog.aspose.com/zip/extract-7z-online/) |

[1]: https://docs.fileformat.com/compression/zip/
[2]: https://docs.fileformat.com/programming/cs/
[3]: https://products.aspose.net/zip/
[4]: https://www.nuget.org/packages/Aspose.ZIP
[5]: https://downloads.aspose.com/zip/net
[6]: https://docs.microsoft.com/en-us/dotnet/api/system.io.filestream?view=netframework-4.8
[7]: https://reference.aspose.com/zip/net/aspose.zip/archive
[8]: https://reference.aspose.com/zip/net/aspose.zip.archive/createentry/methods/1
[9]: https://reference.aspose.com/zip/net/aspose.zip/archive/methods/save
[10]: https://reference.aspose.com/zip/net/aspose.zip.archive/createentry/methods/1
[11]: https://docs.microsoft.com/en-us/dotnet/api/system.io.fileinfo?view=netframework-4.8
[12]: https://reference.aspose.com/zip/net/aspose.zip/archive/methods/createentry
[13]: https://reference.aspose.com/zip/net/aspose.zip.archive/createentry/methods/3
[14]: https://docs.microsoft.com/en-us/dotnet/api/system.io.filestream?view=netframework-4.8
[15]: https://reference.aspose.com/zip/net/aspose.zip/archive
[16]: https://docs.microsoft.com/en-us/dotnet/api/system.io.directoryinfo?view=netframework-4.8
[17]: https://reference.aspose.com/zip/net/aspose.zip/archive/methods/createentries
[18]: https://reference.aspose.com/zip/net/aspose.zip/archive/methods/save
[19]: https://reference.aspose.com/net/zip/aspose.zip.saving/archiveentrysettings
[20]: https://reference.aspose.com/zip/net/aspose.zip/archive
[21]: https://reference.aspose.com/zip/net/aspose.zip.saving/aesecryptionsettings
[22]: https://reference.aspose.com/zip/net/aspose.zip.saving/paralleloptions
[23]: https://forum.aspose.com/