// Create FileStream for output ZIP archive
using (FileStream zipFile = File.Open("compressed_file.zip", FileMode.Create))
{
	// File to be added to archive
	using (FileStream source1 = File.Open("alice29.txt", FileMode.Open, FileAccess.Read))
	{
		using (var archive = new Archive(new ArchiveEntrySettings()))
		{
			// Add file to the archive
			archive.CreateEntry("alice29.txt", source1);
			// ZIP file
			archive.Save(zipFile);
		}
	}
}
