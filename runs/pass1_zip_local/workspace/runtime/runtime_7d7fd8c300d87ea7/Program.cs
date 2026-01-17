using Aspose.Zip;
using Aspose.Zip.Rar;
using Aspose.Zip.Saving;
using Aspose.Zip.SevenZip;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

public class Program
{
    public static void Main(string[] args)
    {
        string zipFilePath = "archive.zip";
        string password = "your_password";
        
        using (Aspose.Zip.Archive archive = new Aspose.Zip.Archive(zipFilePath, password))
        {
            archive.ExtractToDirectory("ExtractedFiles");
        }
    }
}