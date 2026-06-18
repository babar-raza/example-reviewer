---
title: "How to Extract Zip File in C#"
productname: "Aspose.ZIP"
productkey: "zip"
platformkey: "net"
productplatform: ".NET"
description: "This tutorial provides step-by-step instructions on how to extract zip files in C# using Aspose.ZIP, including runnable code examples."
date: 2025-01-17
lastmod: 2022-06-01
weight: 8
draft: false
type: "topic"
keywords: [
    "extract zip file C#",
    "Aspose.ZIP",
    "unzip archive C#",
    "C# archive extraction",
    "extract files from ZIP"
]
step1: "Install Aspose.ZIP for .NET package from NuGet.org."
step2: "Include the Aspose.ZIP namespace in your code."
step3: "Use SetLicense method to set up the license for Aspose.ZIP API."
step4: "Load the input zip file into a FileStream object."
step5: "Create a new Archive object from the FileStream."
step6: "Get the count of files in the archive and loop through the archive entries."
step7: "Extract each archive entry and save the file to disk."
step8: ""
step9: ""
step10: ""
---

In this tutorial, you'll learn how to extract zip files using C# code. With the Aspose.ZIP library, you can easily unzip archives of various formats such as ZIP, GZip, RAR, TAR, and 7Zip directly in your applications.

### Benefits of Extracting ZIP Files
1. **File Management**:
   - Simplifies handling and organizing large sets of files.
2. **Compatibility**:
   - Easily integrates with different file formats supported by Aspose.ZIP.
3. **Automated Processes**:
   - Ideal for applications requiring automated file extractions.

---

## Prerequisites: Preparing the Environment
1. Set up Visual Studio or any compatible .NET IDE.
2. Install Aspose.ZIP from NuGet Package Manager.

---

## Step-by-Step Guide to Extract Zip File in C#

{{% steps %}}

### Step 1: Install Aspose.ZIP
Begin by adding the Aspose.ZIP library to your project.


```shell
Install-Package Aspose.ZIP
```

---

### Step 2: Include the Namespace
Add a reference to the `Aspose.Zip` namespace in your code.


```cs
using Aspose.Zip;
```

---

### Step 3: Load the ZIP File
Open the [ZIP](https://docs.aspose.net/file-formats/zip/) file using a `FileStream` object.


```cs
FileStream zipFileToBeExtracted = File.Open("ZipFileToBeExtracted.zip", FileMode.Open);
```

---

### Step 4: Create an Archive Object
Load the `FileStream` into an Archive object.


```cs
Archive zipArchiveToExtract = new Archive("archive.zip");
```

---

### Step 5: Count the Files in the Archive
Retrieve the number of files contained in the ZIP archive.


```cs
using Aspose.Zip;

public class Program
{
    public static void Main(string[] args)
    {
        using (var zipArchiveToExtract = new Archive("example.zip"))
        {
            int numberOfFilesInArchive = zipArchiveToExtract.Entries.Count;
        }
    }
}
```

---

### Step 6: Extract Each Entry
Loop through each entry in the archive and extract the files.


```cs
for (int fileCounter = 0; fileCounter < numberOfFilesInArchive; fileCounter++)
{
    ArchiveEntry archiveFileEntry = zipArchiveToExtract.Entries[fileCounter];
    string nameOfFileInZipEntry = archiveFileEntry.Name;
    archiveFileEntry.Extract(nameOfFileInZipEntry);
}
```

{{% /steps %}}

## Complete Code Example to Extract a ZIP File
Below is the full example of extracting a ZIP file using C#:


```cs
// Open file from disk using a file stream
FileStream zipFileToBeExtracted = File.Open("archive.zip", FileMode.Open);

// Load the Zip file stream into an Archive object
Archive zipArchiveToExtract = new Archive(zipFileToBeExtracted);

// Get the number of files in the archive
int numberOfFilesInArchive = zipArchiveToExtract.Entries.Count;

// Loop through the archive for each file
for (int fileCounter = 0; fileCounter < numberOfFilesInArchive; fileCounter++)
{
    // Get each zip archive entry and extract the file
    ArchiveEntry archiveFileEntry = zipArchiveToExtract.Entries[fileCounter];
    string nameOfFileInZipEntry = archiveFileEntry.Name;
    
    // Ensure the directory exists before extracting
    string directoryName = Path.GetDirectoryName(nameOfFileInZipEntry);
    if (!string.IsNullOrEmpty(directoryName))
    {
        Directory.CreateDirectory(directoryName);
    }
    
    archiveFileEntry.Extract(nameOfFileInZipEntry);
}
```

## Additional Information
- This functionality supports not just ZIP files, but also other formats like GZip, RAR, and TAR.
- You can also extract files directly in memory if needed for further processing.

## Conclusion
This tutorial has demonstrated how to extract zip files in C# using Aspose.ZIP. By following the steps and using the provided code example, you can easily integrate zip file extraction into your applications. For more advanced functionalities, consider exploring other tutorials related to file compression and extraction.