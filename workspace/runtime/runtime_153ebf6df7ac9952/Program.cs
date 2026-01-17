using Aspose.Zip;
using Aspose.Zip.Security;

public class Program
{
    public static void Main(string[] args)
    {
        using (Aspose.Zip.Archive archive = new Aspose.Zip.Archive("your_password"))
        {
            archive.Open("path_to_your_archive.zip");
            archive.ExtractToDirectory("ExtractedFiles");
        }
    }
}