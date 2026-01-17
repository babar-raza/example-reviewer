// File: Program.cs
using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
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

        // Keep streams alive until after Save()
        var streams = new List<Stream>();

        using (var archive = new Archive())
        {
            // 1) Add a text file from memory
            var ms = new MemoryStream(Encoding.UTF8.GetBytes("Hello from Aspose.ZIP in memory."));
            streams.Add(ms);
            archive.CreateEntry("docs/readme.txt", ms, entrySettings);

            // 2) Add a file from disk (streamed; not fully loaded in RAM)
            var sourcePath = "report.pdf"; // ensure it exists
            if (File.Exists(sourcePath))
            {
                var fs = File.OpenRead(sourcePath);
                streams.Add(fs);
                archive.CreateEntry("reports/2025/report.pdf", fs, entrySettings);
            }

            // 3) Save the ZIP to our in-memory buffer
            archive.Save(zipBuffer);
        }

        // Now dispose the streams
        foreach (var stream in streams)
        {
            stream.Dispose();
        }

        // Use the ZIP bytes as needed (send over network, write to DB, etc.)
        byte[] zipBytes = zipBuffer.ToArray();
        Console.WriteLine($"ZIP size: {zipBytes.Length} bytes");
    }
}
