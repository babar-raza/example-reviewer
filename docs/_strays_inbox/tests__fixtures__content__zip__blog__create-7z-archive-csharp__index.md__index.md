---
author: Usman Aziz
categories:
- Aspose.ZIP Plugin Family
date: 2024-05-10
description: Learn how to create 7zip (.7z) archives programmatically using C#. Apply AES encryption to secure your archives and set passwords for files with ease. Unlock advanced features for just $99 with the Aspose Plugin.
draft: false
lastmod: '2025-04-08'
seoTitle: Create 7zip Archive using C# .NET | Create AES Encrypted 7z Files in C#
summary: Discover how to programmatically create 7z archives in C# using the .NET 7-Zip library. Explore AES encryption and password protection features with the Aspose Plugin for just $99.
tags:
- C# .NET 7-Zip programmatic archive creation
- .NET 7z archive creation with password protection
- .NET Core 7z archive creation example
- .NET Framework 7z archive creation
title: Create 7z (7-Zip) Archives Programmatically using C# .NET
enhanced: true
---
{{< figure align=center src="images/Create-7Zip-Archive-in-C.jpg" alt="Create 7Zip Archive in C#">}}

In a [previous post](https://blog.aspose.com/zip/create-zip-archives-add-files-or-folders-to-zip-in-csharp-asp.net/), we explored how to create [ZIP](https://docs.fileformat.com/compression/zip/) archives using [C#](https://docs.fileformat.com/programming/cs/). Now, we’ll shift our focus to the **7z format**, which is renowned for its high compression ratio and robust **256-bit AES encryption** capabilities. This makes the .NET 7z library an ideal choice for handling archives securely and efficiently.

## What You Will Learn

In this tutorial, you'll learn how to **create 7z (7-Zip) archives programmatically using C#**. We will cover the following topics:

- [Creating a 7z Archive with a Single Entry](#Create-a-7z-7Zip-Archive-using-Csharp)
- [Creating an AES Encrypted 7z Archive](#Create-an-AES-Encrypted-7z-Archive-using-Csharp)
- [Setting Different Passwords for 7z Entries](#Set-Different-Password-for-7z-Entries-using-Csharp)

We'll be using the [Aspose.ZIP for .NET](https://products.aspose.com/zip/net) API. You can install this library via:

- [NuGet Package Manager](http://nuget.org/packages/Aspose.zip)
- [Download the DLL](https://downloads.aspose.com/zip/net) and include it in your project

## Create 7z (7-Zip) Archive using C# {#Create-a-7z-7Zip-Archive-using-Csharp}

You can compress files into a 7z archive, suitable for both **single file** and **multiple files** scenarios. This functionality provides a cost-effective solution for developers looking for a .NET RAR extraction tool.

### Create 7z Archive with a Single Entry

To create a 7z archive with a single file, follow these steps:

1. Open a new [FileStream](https://docs.microsoft.com/en-us/dotnet/api/system.io.filestream) to create the 7z file.
2. Instantiate the [SevenZipArchive](https://reference.aspose.com/zip/net/aspose.zip.sevenzip/sevenziparchive) class.
3. Add the file using [SevenZipArchive.CreateEntry](https://reference.aspose.com/zip/net/aspose.zip.sevenzip.sevenziparchive/createentry/methods/3).
4. Save the archive with [SevenZipArchive.Save](https://reference.aspose.com/zip/net/aspose.zip.sevenzip/sevenziparchive/methods/save).

Here’s a **C# example** to illustrate:

{{< gist aspose-com-gists 42ee14864d84aeae8619284450c3d628 "Examples-CSharp-WorkingWithSevenZip-CreateSevenZipEntry-CreateSevenZipEntry.cs" >}}

### Create 7z Archive with Multiple Entries

To compress multiple files into a single 7z archive:

1. Create an instance of the [SevenZipArchive](https://reference.aspose.com/zip/net/aspose.zip.sevenzip/sevenziparchive) class.
2. Use [SevenZipArchive.CreateEntries](https://reference.aspose.com/zip/net/aspose.zip.sevenzip.sevenziparchive/createentries/methods/1) and pass the folder path.
3. Save the archive with [SevenZipArchive.Save](https://reference.aspose.com/zip/net/aspose.zip.sevenzip/sevenziparchive/save/methods/1).

Example:

{{< gist aspose-com-gists 42ee14864d84aeae8619284450c3d628 "Examples-CSharp-WorkingWithSevenZip-CreateSevenZipEntries-CreateSevenZipEntries.cs" >}}

## Create an AES Encrypted 7z Archive using C# {#Create-an-AES-Encrypted-7z-Archive-using-Csharp}

To secure your archives, you can utilize **AES encryption**, a feature of the .NET 7z library that enhances archive security:

1. Create an instance of [SevenZipAESEncryptionSettings](https://reference.aspose.com/zip/net/aspose.zip.saving/sevenzipaesencryptionsettings).
2. Configure the necessary encryption parameters.
3. Add entries to the archive and save it.

Example:

{{< gist aspose-com-gists 42ee14864d84aeae8619284450c3d628 "Examples-CSharp-WorkingWithSevenZip-AESEncryptionSettings-AESEncryptionSettings.cs" >}}

## Set Different Passwords for 7z Entries using C# {#Set-Different-Password-for-7z-Entries-using-Csharp}

To assign unique passwords to different entries within your archive:

1. Open a [FileStream](https://docs.microsoft.com/en-us/dotnet/api/system.io.filestream) for the 7z archive.
2. Use [SevenZipArchive.CreateEntry](https://reference.aspose.com/zip/net/aspose.zip.sevenzip/sevenziparchive/methods/createentry) to add entries while specifying individual passwords.
3. Save the archive.

Example:

{{< gist aspose-com-gists 42ee14864d84aeae8619284450c3d628 "Examples-CSharp-WorkingWithSevenZip-EntriesWithDifferentPasswords-EntriesWithDifferentPasswords.cs" >}}

## Conclusion

In this article, we have explored how to **create 7z archives programmatically in C#**, secure them with **AES encryption**, and assign unique passwords to entries. For more advanced features and best practices, check out the [Aspose.ZIP documentation](https://docs.aspose.net/display/zipnet/Product+Overview).

By utilizing the **Aspose Plugin** for .NET, you can efficiently manage archives, apply encryption, and streamline your workflows—all for just **$99**. Unlock advanced features today with this reliable .NET archive extraction plugin, supporting all major formats!