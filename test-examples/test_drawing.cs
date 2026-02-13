using System;
using System.Drawing;
using System.Drawing.Imaging;

class Test {
    static void Main() {
        var img = new Bitmap(100, 100);
        img.Save("test.png", ImageFormat.Png);
        Console.WriteLine("System.Drawing works!");
    }
}
