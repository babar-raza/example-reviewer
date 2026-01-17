using Aspose.Zip;

public class Program
{
    public static void Main(string[] args)
    {
        using (var archiveFile = new Archive())
        {
            archiveFile.CreateEntry("AnimationImages");
        }
    }
}