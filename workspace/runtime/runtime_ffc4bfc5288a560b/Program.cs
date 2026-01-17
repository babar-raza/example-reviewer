using Aspose.Zip;
using System.IO;

public class Program
{
    public static void Main(string[] args)
    {
        // Create a file stream object for the output zip file
        using (FileStream zippedFolder = new FileStream("AnimationImages.zip", FileMode.Create))
        {
            // Create a Zip archive file class object
            using (Archive archiveFile = new Archive())
            {
                // Add all the files and folders recursively
                archiveFile.CreateEntriesFromDirectory("AnimationImages");

                // Save the output ZIP file
                archiveFile.Save(zippedFolder);
            }
        }
    }
}