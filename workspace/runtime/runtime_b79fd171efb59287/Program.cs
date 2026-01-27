using System;
using System.IO;
using System.Text;
using Aspose.Zip;
using Aspose.Zip.Saving;

class Program
{
    static void Main()
    {
        // Prepare output buffer
        using var zipBuffer = new MemoryStream();

        // Choose compression (Deflate is the standard ZIP method)
        var deflate = new DeflateCompressionSettings();
        var entrySettings = new ArchiveEntrySettings(deflate);

        using (var archive = new Archive())
        {
            // 1) Add a text file from memory
            using (var ms = new MemoryStream(Encoding.UTF8.GetBytes("Hello from Aspose.ZIP in memory.")))
            {
                archive.CreateEntry("docs/readme.txt", ms, entrySettings);
            }

            // 2) Add a file from disk (streamed; not fully loaded in RAM)
            var sourcePath = "archive.zip"; // ensure it exists
            if (File.Exists(sourcePath))
            {
                using var fs = File.OpenRead(sourcePath);
                archive.CreateEntry("reports/2025/report.pdf", fs, entrySettings);
            }

            // 3) Save the ZIP to our in-memory buffer
            zipBuffer.Position = 0; // Reset position before saving
            archive.Save(zipBuffer, new ArchiveSaveOptions { CompressionSettings = deflate });
        }

        // Use the ZIP bytes as needed (send over network, write to DB, etc.)
        byte[] zipBytes = zipBuffer.ToArray();
        Console.WriteLine($"ZIP size: {zipBytes.Length} bytes");
    }
}