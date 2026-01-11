using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Emit;
using System.Reflection;
using System.Text;
using Newtonsoft.Json;

namespace AsposeZipValidator;

class Program
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("Aspose.ZIP Example Validator");
        Console.WriteLine("============================");
        Console.WriteLine($"Using Aspose.ZIP version: {typeof(Aspose.Zip.Archive).Assembly.GetName().Version}");
        Console.WriteLine();

        if (args.Length == 0)
        {
            Console.WriteLine("Usage:");
            Console.WriteLine("  dotnet run -- validate <code-snippet>");
            Console.WriteLine("  dotnet run -- validate-file <path-to-file>");
            Console.WriteLine("  dotnet run -- check-api <method-name>");
            return;
        }

        var command = args[0];

        switch (command)
        {
            case "check-api":
                CheckApiAvailability(args[1]);
                break;
            case "validate":
                var code = args.Length > 1 ? args[1] : "";
                await ValidateCodeSnippet(code);
                break;
            case "validate-file":
                var filePath = args.Length > 1 ? args[1] : "";
                if (File.Exists(filePath))
                {
                    var fileCode = await File.ReadAllTextAsync(filePath);
                    await ValidateCodeSnippet(fileCode);
                }
                else
                {
                    Console.WriteLine($"File not found: {filePath}");
                }
                break;
            default:
                Console.WriteLine($"Unknown command: {command}");
                break;
        }
    }

    static void CheckApiAvailability(string methodName)
    {
        Console.WriteLine($"Checking API availability for: {methodName}");
        Console.WriteLine();

        // Check Archive class
        var archiveType = typeof(Aspose.Zip.Archive);
        var methods = archiveType.GetMethods(BindingFlags.Public | BindingFlags.Instance);

        var found = methods.Where(m => m.Name.Contains(methodName, StringComparison.OrdinalIgnoreCase));

        if (found.Any())
        {
            Console.WriteLine($"Found {found.Count()} method(s):");
            foreach (var method in found)
            {
                var parameters = method.GetParameters();
                var paramStr = string.Join(", ", parameters.Select(p => $"{p.ParameterType.Name} {p.Name}"));
                Console.WriteLine($"  - {method.ReturnType.Name} {method.Name}({paramStr})");
            }
        }
        else
        {
            Console.WriteLine($"Method '{methodName}' NOT FOUND in Archive class");
        }

        // Check DeflateCompressionSettings constructors
        if (methodName.Contains("Deflate", StringComparison.OrdinalIgnoreCase))
        {
            Console.WriteLine();
            Console.WriteLine("DeflateCompressionSettings constructors:");
            var deflateType = typeof(Aspose.Zip.Saving.DeflateCompressionSettings);
            var constructors = deflateType.GetConstructors(BindingFlags.Public | BindingFlags.Instance);

            foreach (var ctor in constructors)
            {
                var parameters = ctor.GetParameters();
                var paramStr = string.Join(", ", parameters.Select(p => $"{p.ParameterType.Name} {p.Name}"));
                Console.WriteLine($"  - new DeflateCompressionSettings({paramStr})");
            }
        }
    }

    static async Task<bool> ValidateCodeSnippet(string code)
    {
        Console.WriteLine("Validating code snippet...");
        Console.WriteLine();

        // Wrap code if it's not a complete program
        string fullCode = code;
        if (!code.Contains("class ") && !code.Contains("namespace "))
        {
            fullCode = $@"
using System;
using System.IO;
using System.Text;
using Aspose.Zip;
using Aspose.Zip.Saving;

namespace TestValidation
{{
    class Program
    {{
        static void Main(string[] args)
        {{
{code}
        }}
    }}
}}";
        }

        // Parse and compile
        var syntaxTree = CSharpSyntaxTree.ParseText(fullCode);

        // Get references
        var references = new List<MetadataReference>();

        // Core references
        var systemRuntime = Assembly.Load("System.Runtime");
        references.Add(MetadataReference.CreateFromFile(systemRuntime.Location));
        references.Add(MetadataReference.CreateFromFile(typeof(object).Assembly.Location));
        references.Add(MetadataReference.CreateFromFile(typeof(Console).Assembly.Location));
        references.Add(MetadataReference.CreateFromFile(typeof(File).Assembly.Location));
        references.Add(MetadataReference.CreateFromFile(typeof(System.Text.Encoding).Assembly.Location));

        // Aspose.Zip reference
        references.Add(MetadataReference.CreateFromFile(typeof(Aspose.Zip.Archive).Assembly.Location));

        // Additional system references
        try
        {
            references.Add(MetadataReference.CreateFromFile(Assembly.Load("System.Collections").Location));
            references.Add(MetadataReference.CreateFromFile(Assembly.Load("System.Linq").Location));
            references.Add(MetadataReference.CreateFromFile(Assembly.Load("System.IO.FileSystem").Location));
            references.Add(MetadataReference.CreateFromFile(Assembly.Load("System.Threading").Location));
            references.Add(MetadataReference.CreateFromFile(Assembly.Load("System.Threading.Tasks").Location));
            references.Add(MetadataReference.CreateFromFile(Assembly.Load("netstandard").Location));
        }
        catch { /* Some references might not be available */ }

        // Add ASP.NET Core references if code uses them
        if (code.Contains("WebApplication") || code.Contains("HttpContext"))
        {
            try
            {
                references.Add(MetadataReference.CreateFromFile(Assembly.Load("Microsoft.AspNetCore.Http.Abstractions").Location));
                references.Add(MetadataReference.CreateFromFile(Assembly.Load("Microsoft.AspNetCore.Http").Location));
            }
            catch { }
        }

        var compilation = CSharpCompilation.Create(
            "ValidationAssembly",
            syntaxTrees: new[] { syntaxTree },
            references: references,
            options: new CSharpCompilationOptions(OutputKind.ConsoleApplication));

        using var ms = new MemoryStream();
        EmitResult result = compilation.Emit(ms);

        if (!result.Success)
        {
            Console.WriteLine("COMPILATION FAILED");
            Console.WriteLine("==================");

            var failures = result.Diagnostics.Where(diagnostic =>
                diagnostic.IsWarningAsError ||
                diagnostic.Severity == DiagnosticSeverity.Error);

            foreach (var diagnostic in failures)
            {
                Console.WriteLine($"  {diagnostic.Id}: {diagnostic.GetMessage()}");
                var lineSpan = diagnostic.Location.GetLineSpan();
                Console.WriteLine($"    at line {lineSpan.StartLinePosition.Line + 1}");
            }

            return false;
        }
        else
        {
            Console.WriteLine("COMPILATION SUCCESSFUL");
            Console.WriteLine("======================");
            Console.WriteLine("The code compiles correctly against Aspose.ZIP");
            return true;
        }
    }
}
