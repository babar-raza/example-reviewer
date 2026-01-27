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
            var sourceFile = "report.pdf"; // ensure this file exists
            if (File.Exists(sourceFile))
            {
                using var fs = File.OpenRead(sourceFile);
                archive.CreateEntry("reports/2025/report.pdf", fs);
            }

            // Save the 7z archive
            using var outStream = File.Create(outputPath);
            archive.Save(outStream, null); // Add null for save options if not needed
        }

        Console.WriteLine("Saved 7z: " + Path.GetFullPath(outputPath));
    }
}