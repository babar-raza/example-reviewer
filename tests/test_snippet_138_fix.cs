using System;
using System.IO;
using Aspose.Zip;
using Aspose.Zip.Saving;

static class InMemoryZipper
{
    // CORRECT FIX 1: Remove default parameter entirely
    public static byte[] ZipFolderToBytes(string sourceFolder)
    {
        if (!Directory.Exists(sourceFolder))
            throw new DirectoryNotFoundException(sourceFolder);

        var deflate = new DeflateCompressionSettings();
        var entrySettings = new ArchiveEntrySettings(deflate);

        using var buffer = new MemoryStream();
        using (var archive = new Archive())
        {
            var root = Path.GetFullPath(sourceFolder);
            foreach (var filePath in Directory.GetFiles(root, "*", SearchOption.AllDirectories))
            {
                var rel = Path.GetRelativePath(root, filePath).Replace(Path.DirectorySeparatorChar, '/');
                using var fs = File.OpenRead(filePath);
                archive.CreateEntry(rel, fs, entrySettings);
            }

            archive.Save(buffer);
        }
        return buffer.ToArray();
    }

    // CORRECT FIX 2: Use null default and apply inside
    public static byte[] ZipFolderToBytesWithSettings(string sourceFolder, CompressionSettings settings = null)
    {
        if (!Directory.Exists(sourceFolder))
            throw new DirectoryNotFoundException(sourceFolder);

        settings = settings ?? CompressionSettings.Deflate;
        var entrySettings = new ArchiveEntrySettings(settings);

        using var buffer = new MemoryStream();
        using (var archive = new Archive())
        {
            var root = Path.GetFullPath(sourceFolder);
            foreach (var filePath in Directory.GetFiles(root, "*", SearchOption.AllDirectories))
            {
                var rel = Path.GetRelativePath(root, filePath).Replace(Path.DirectorySeparatorChar, '/');
                using var fs = File.OpenRead(filePath);
                archive.CreateEntry(rel, fs, entrySettings);
            }

            archive.Save(buffer);
        }
        return buffer.ToArray();
    }
}
