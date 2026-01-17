---
author: Usman Aziz
categories:
- Aspose.ZIP Plugin Family
date: 2023-11-09
description: C# Create ZIP files. ZIP single or multiple files. Create AES encrypted ZIP archives to compress files or folders. Create password-protected ZIP files in C#. Explore the $99 Aspose Plugin for enhanced .NET zip file manipulation.
draft: false
lastmod: '2025-04-08'
seoTitle: Create ZIP Archive in C# | ZIP Single or Multiple Files | ZIP Library
summary: Learn how to efficiently handle ZIP archives in C# using .NET file compression methods. Discover the powerful Aspose Plugin for managing large files, encrypting ZIPs, and creating self-extracting archives.
tags:
- C# ZIP File Handling
- C# Archive Compression
- AES Encryption in ZIP
- ZIP Multiple Files in C#
- Aspose.ZIP for .NET
- File Compression
- Password-Protected ZIP
title: Add Files or Folders to ZIP Archives Programmatically in C#
enhanced: true
---
{{< figure align=center src="images/Create-ZIP-in-C.jpg" alt="Create ZIP in C#">}}

## Introduction to ZIP Archives in C#

**ZIP archives** are essential for compressing and organizing files and folders into a single, manageable container. They not only reduce file sizes for efficient storage and transmission but also preserve metadata and can be encrypted for enhanced security. In this article, we will explore various methods to **programmatically create ZIP files in C#**, including how to add files and folders, create password-protected archives, and apply AES encryption.

### What You Will Learn

In this article, you will discover how to:

*   [Create a ZIP Archive using C#](#Create-a-ZIP-archive-using-CSharp)
*   [Add multiple files to a ZIP archive](#Add-multiple-files-to-a-ZIP-archive)
*   [Add folders to a ZIP archive](#Add-folders-to-a-ZIP-archive)
*   [Create a password-protected ZIP archive using ZipCrypto](#Create-a-Password-Protected-ZIP-Archive-using-ZipCrypto-in-CSharp)
*   [Encrypt ZIP archives with AES encryption](#Create-AES-Encrypted-ZIP-Archives-in-CSharp)
*   [Set parallel compression mode](#Set-parallel-compression-mode)

## C# ZIP Library

The **[Aspose.ZIP for .NET](https://products.aspose.net/zip/)** library is a powerful tool for handling ZIP file operations within .NET applications, making it easier to zip or unzip files and folders. This library is particularly effective for **handling large files in C# .NET ZIP archives** and supports AES encryption for enhanced security. You can easily install this library from **[NuGet](https://www.nuget.org/packages/Aspose.ZIP)** or download the binaries from the **[Downloads](https://downloads.aspose.com/zip/net)** section.

## Create a ZIP Archive in C# {#Create-a-ZIP-archive-using-CSharp}

To **programmatically create a ZIP file in C#**, follow these steps:

1. Create a [FileStream](https://docs.microsoft.com/en-us/dotnet/api/system.io.filestream?view=netframework-4.8) object for the output ZIP archive.
2. Open the source file as a _FileStream_ object.
3. Instantiate the [Archive](https://reference.aspose.com/zip/net/aspose.zip/archive) class.
4. Add the file to the archive using the [Archive.CreateEntry(string, FileStream)](https://reference.aspose.com/zip/net/aspose.zip.archive/createentry/methods/1) method.
5. Save the ZIP archive with the [Archive.Save(FileStream)](https://reference.aspose.com/zip/net/aspose.zip/archive/methods/save) method.

Here’s a code sample demonstrating how to add a file to a ZIP archive in C#:

{{< gist aspose-com-gists dea0000f742629e43ecc24f5a19ab2ac "create-zip-archive-in-csharp.cs" >}}

## Add Multiple Files to a ZIP Archive in C# {#Add-multiple-files-to-a-ZIP-archive}

When you need to **add multiple files to a ZIP archive**, several approaches can be taken. Here are the methods you can use with **C# to zip multiple files**:

### Using FileStream to Add Multiple Files

This method employs the _FileStream_ class to add files to the ZIP archive via the [Archive.CreateEntry(String, FileStream)](https://reference.aspose.com/zip/net/aspose.zip.archive/createentry/methods/1) method. Here’s how you can do it:

{{< gist aspose-com-gists dea0000f742629e43ecc24f5a19ab2ac "add-mulitple-files-to-zip.cs" >}}

### Using FileInfo for Multiple Files

Alternatively, you can utilize the [FileInfo](https://docs.microsoft.com/en-us/dotnet/api/system.io.fileinfo?view=netframework-4.8) class to load files and add them to the ZIP archive with the [Archive.CreateEntry(String, FileInfo)](https://reference.aspose.com/zip/net/aspose.zip/archive/methods/createentry) method. Below is a code sample:

{{< gist aspose-com-gists dea0000f742629e43ecc24f5a19ab2ac "add-mulitple-files-to-zip-fileinfo.cs" >}}

### Using File Paths

You can also directly provide the file paths to the [Archive.CreateEntry(String name, String path, Boolean openImmediately, ArchiveEntrySettings newEntrySettings)](https://reference.aspose.com/zip/net/aspose.zip.archive/createentry/methods/3) method. Here’s an example:

{{< gist aspose-com-gists dea0000f742629e43ecc24f5a19ab2ac "add-files-to-zip-filepath.cs" >}}

## Add Folders to a ZIP Archive in C# {#Add-folders-to-a-ZIP-archive}

To **add a folder to a ZIP archive in C#**, follow these steps:

1. Create a [FileStream](https://docs.microsoft.com/en-us/dotnet/api/system.io.filestream?view=netframework-4.8) object for the output ZIP archive.
2. Instantiate the [Archive](https://reference.aspose.com/zip/net/aspose.zip/archive) class.
3. Use the [DirectoryInfo](https://docs.microsoft.com/en-us/dotnet/api/system.io.directoryinfo?view=netframework-4.8) class to specify the folder you want to zip.
4. Add the folder to the ZIP using the [Archive.CreateEntries(DirectoryInfo)](https://reference.aspose.com/zip/net/aspose.zip/archive/methods/createentries) method.
5. Save the ZIP archive with the [Archive.Save(FileStream)](https://reference.aspose.com/zip/net/aspose.zip/archive/methods/save) method.

Here’s a code sample that illustrates how to add a folder to a ZIP file:

{{< gist aspose-com-gists dea0000f742629e43ecc24f5a19ab2ac "compress-folder-into-zip.cs" >}}

## Create a Password Protected ZIP using ZipCrypto in C# {#Create-a-Password-Protected-ZIP-Archive-using-ZipCrypto-in-CSharp}

To secure your ZIP archives, you can apply password protection using ZipCrypto encryption. This is accomplished by utilizing the [ArchiveEntrySettings](https://reference.aspose.com/net/zip/aspose.zip.saving/archiveentrysettings) class in the constructor of the [Archive](https://reference.aspose.com/zip/net/aspose.zip/archive), which accepts the encryption type as a parameter. You can use the **C# Zip Archive Password** method to easily implement this.

Here’s how to create a password-protected ZIP archive using ZipCrypto in C#:

{{< gist aspose-com-gists dea0000f742629e43ecc24f5a19ab2ac "create-password-protected-zip.cs" >}}

## Create Password Protected ZIP with AES Encryption {#Create-AES-Encrypted-ZIP-Archives-in-CSharp}

The **Aspose.ZIP for .NET** library also supports AES encryption for protecting ZIP archives. You can choose from the following AES encryption methods:

*   **AES128**
*   **AES192**
*   **AES256**

To apply AES encryption, use the [AesEcryptionSettings](https://reference.aspose.com/zip/net/aspose.zip.saving/aesecryptionsettings) class. Below is a code sample demonstrating how to create a password-protected ZIP with AES encryption in C#, including support for the **C# Zip File Password** feature:

{{< gist aspose-com-gists dea0000f742629e43ecc24f5a19ab2ac "encrypt-zip-with-aes-encryption.cs" >}}

## Set Parallel Compression Mode {#Set-parallel-compression-mode}

For efficient handling of multiple entries, you can configure the API for parallel compression using the [ParallelOptions](https://reference.aspose.com/zip/net/aspose.zip.saving/paralleloptions) class. The available parallel compression modes are:

*   **Never** - Do not compress in parallel.
*   **Always** - Compress in parallel (beware of potential memory issues).
*   **Auto** - Automatically decide whether to use parallel compression based on the entries.

Here’s how to set parallel compression mode while zipping multiple files with the Aspose C# ZIP library:

{{< gist aspose-com-gists 42ee14864d84aeae8619284450c3d628 "Examples-CSharp-CompressingAndDecompressingFiles-UsingParallelismToCompressFiles-UsingParallelismToCompressFiles.cs" >}}

## Learn More About C# .NET ZIP Library 

To deepen your understanding of the **C# .NET ZIP library**, explore the following resources:

*   [Documentation](https://docs.aspose.net/display/zipnet/Getting+Started)
*   [Source code examples](https://github.com/aspose-zip/Aspose.ZIP-for-.NET)

## Try Our Online ZIP Compression Tool

You can also experiment with our **[free online application](https://products.aspose.app/zip/compression/zip)** based on the Aspose.ZIP for .NET to compress files into ZIP archives effortlessly.

## Conclusion

In this article, you have learned how to **create ZIP archives programmatically in C#**. The provided code samples demonstrate how to add files and folders to ZIP archives, create password-protected ZIP files using ZipCrypto and AES encryption methods, and configure parallel compression. Additionally, you now understand how to **create ZIP files in C#**, including how to **zip a file**, **create a ZIP file in C#**, and **add files to ZIP** archives. If you have any questions or need further assistance, feel free to reach out via our **[forum](https://forum.aspose.net/)**.

## See Also

|  |  |  |
|----------|----------|----------|
| [Unrar or Extract Files using C#](https://blog.aspose.com/zip/unrar-extract-rar-extractor-opener-in-csharp-asp.net/) | [Unzip Files in ZIP Archives using C#](https://blog.aspose.com/zip/unzip-files-in-password-protected-zip-archives-in-csharp-asp.net/) | [Create 7z (7-Zip) Archives in C# .NET](https://blog.aspose.com/zip/create-7zip-archives-programmatically-using-csharp-asp.net/) | 
| [Open or Extract 7z (7zip) File in C# .NET](https://blog.aspose.com/zip/open-extract-7zip-7z-file-unzip-in-csharp-asp-net/) | [Create and Extract GZip Archives using C#](https://blog.aspose.com/zip/create-and-extract-gzip-archives-using-csharp/) | [Convert RAR Files to ZIP Archive in C#](https://blog.aspose.com/zip/convert-rar-files-to-zip-in-csharp/) |
| [Convert ZIP Archives to TAR in C#](https://blog.aspose.com/zip/convert-zip-to-tar-in-csharp.net/) | [Create a Flat ZIP Archive in C#](https://blog.aspose.com/zip/create-a-flat-zip-archive-in-csharp/) | [Create Executable Self-extracting Archive in C#](https://blog.aspose.com/zip/create-self-extracting-archive-in-csharp/) |
| [Create TAR.GZ and TAR.XZ Files in C#](https://blog.aspose.com/zip/create-tar-gz-xz-files-in-csharp/) | [Delete Files in a ZIP Archive in C#](https://blog.aspose.com/zip/delete-files-in-zip-archive-csharp-net/) | [Extract Nested ZIP Archives in C#](https://blog.aspose.com/zip/extract-nested-zip-archives-in-csharp-net/) |
| [Merge Multiple ZIP or TAR Archives in C#](https://blog.aspose.com/zip/merge-zip-and-tar-files-in-csharp/) | [How to Create ZIP Files](https://blog.aspose.com/zip/how-to-create-zip-files/) | [Extract 7z Online](https://blog.aspose.com/zip/extract-7z-online/) |  

## Additional Resources

If you're looking for more information on how to **create ZIP files in C#**, consider checking out:

* [How to Zip Files in .NET with C#](https://blog.aspose.com/zip/how-to-zip-files-in-dotnet-using-csharp/)
* [C# Zip File with Password](https://blog.aspose.com/zip/csharp-zip-file-with-password/)
* [C# Create Zip File from Multiple Files](https://blog.aspose.com/zip/csharp-create-zip-file-from-multiple-files/)
* [C# Zip Folder](https://blog.aspose.com/zip/csharp-zip-folder/)
* [C# Add Files to Zip](https://blog.aspose.com/zip/csharp-add-files-to-zip/)  

Incorporating various methods to **create ZIP files in C#**, such as **.NET Core Create ZIP File**, **C# Create ZIP File Programmatically**, and **C# Add Files to ZIP**, can significantly enhance your development efficiency and data handling capabilities. 

You can also explore the **C# Zip File Example** to see a practical implementation of these methods, which will further enhance your understanding of how to **zip files in .NET with C#**.