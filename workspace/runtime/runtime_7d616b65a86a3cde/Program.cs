// File: Program.cs
using System;
using System.IO;
using System.Text;
using Aspose.Zip.SevenZip;

class Program
{
    static void Main()
    {
        var outputPath = "example.7z";

        using (var archive = new SevenZipArchive())
        {
            // Add a text file from memory
            using (var ms = new MemoryStream(Encoding.UTF8.GetBytes("Hello 7z from Aspose.ZIP")))
            {
                archive.CreateEntry("docs/readme.txt", ms);
            }

            // Add a file from disk
            var sourceFile = "alice29.txt"; // ensure this file exists
            if (File.Exists(sourceFile))
            {
                using var fs = File.OpenRead(sourceFile);
                archive.CreateEntry("reports/2025/alice29.txt", fs);
            }

            // Save the 7z archive
            using var outStream = new FileStream(outputPath, FileMode.Create);
            archive.Save(outStream);
        }

        Console.WriteLine("Saved 7z: " + Path.GetFullPath(outputPath));
    }
}