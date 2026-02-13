using System;
using System.IO;
using Aspose.BarCode.Generation;

class BarcodeFixtureGenerator
{
    static void Main(string[] args)
    {
        string outputDir = args.Length > 0 ? args[0] : "barcode-fixtures";
        Directory.CreateDirectory(outputDir);

        Console.WriteLine($"Generating barcode fixtures to: {outputDir}");

        // Sample.png (Code128)
        using (var gen = new BarcodeGenerator(EncodeTypes.Code128, "SAMPLE123"))
        {
            gen.Parameters.Barcode.XDimension.Millimeters = 1f;
            gen.Save(Path.Combine(outputDir, "sample.png"), BarCodeImageFormat.Png);
        }

        // Barcode.png (QR Code)
        using (var gen = new BarcodeGenerator(EncodeTypes.QR, "https://aspose.com"))
        {
            gen.Parameters.Barcode.XDimension.Millimeters = 2f;
            gen.Save(Path.Combine(outputDir, "barcode.png"), BarCodeImageFormat.Png);
        }

        // Test.png (DataMatrix)
        using (var gen = new BarcodeGenerator(EncodeTypes.DataMatrix, "TEST-DATA"))
        {
            gen.Parameters.Barcode.XDimension.Millimeters = 1.5f;
            gen.Save(Path.Combine(outputDir, "test.png"), BarCodeImageFormat.Png);
        }

        Console.WriteLine("Generated 3 barcode fixture files");
    }
}
