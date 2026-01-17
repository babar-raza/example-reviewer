using Aspose.Zip;
using Aspose.Zip.Saving;

public class Program
{
    public static void Main(string[] args)
    {
        using (SevenZipArchive archive = new SevenZipArchive())
        {
            var entrySettings = new ArchiveEntrySettings(new FolderOptions("folder"));
            archive.CreateEntries(entrySettings);

            archive.Save("folder.7z");
        }
    }
}