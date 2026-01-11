using Aspose.Zip;
var archive = new Archive();
archive.CreateEntry("file.txt", "test_data.txt");
archive.Save("output.zip");
