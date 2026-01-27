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
        string[] files = Directory.GetFiles(@"C:\path\to\test\data\", "*.zip");
        foreach (string file in files)
        {
            using (Archive archive = new Archive(file))
            {
                archive.ExtractToDirectory(@"C:\output_folder");
            }
        }
    }
}