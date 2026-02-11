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
        // Only show header for non-catalog commands (catalog outputs JSON)
        bool isCatalogCommand = args.Length > 0 && args[0] == "catalog-types";

        if (!isCatalogCommand)
        {
            Console.WriteLine("Aspose Package Validator");
            Console.WriteLine("========================");
            Console.WriteLine($"Using Aspose.ZIP version: {typeof(Aspose.Zip.Archive).Assembly.GetName().Version}");
            Console.WriteLine();
        }

        if (args.Length == 0)
        {
            Console.WriteLine("Usage:");
            Console.WriteLine("  dotnet run -- validate <code-snippet>");
            Console.WriteLine("  dotnet run -- validate-file <path-to-file>");
            Console.WriteLine("  dotnet run -- check-api <method-name>");
            Console.WriteLine("  dotnet run -- catalog-types --package <name> --version <ver> --namespace-prefix <prefix> [--include-enums] [--include-constructors] [--include-methods] [--include-properties] [--full]");
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
            case "catalog-types":
                var packageName = GetArg(args, "--package");
                var version = GetArg(args, "--version");
                var nsPrefix = GetArg(args, "--namespace-prefix");
                bool includeFull = HasFlag(args, "--full");
                bool includeEnums = HasFlag(args, "--include-enums") || includeFull;
                bool includeConstructors = HasFlag(args, "--include-constructors") || includeFull;
                bool includeMethods = HasFlag(args, "--include-methods") || includeFull;
                bool includeProperties = HasFlag(args, "--include-properties") || includeFull;
                CatalogTypes(packageName, version, nsPrefix, includeEnums, includeConstructors, includeMethods, includeProperties);
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

    static string GetArg(string[] args, string argName)
    {
        for (int i = 0; i < args.Length - 1; i++)
        {
            if (args[i].Equals(argName, StringComparison.OrdinalIgnoreCase))
            {
                return args[i + 1];
            }
        }
        return string.Empty;
    }

    static bool HasFlag(string[] args, string flagName)
    {
        return args.Any(a => a.Equals(flagName, StringComparison.OrdinalIgnoreCase));
    }

    static string LocateNuGetPackage(string packageName, string version)
    {
        // Try to locate NuGet package in standard locations
        var userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        var nugetRoot = Path.Combine(userProfile, ".nuget", "packages", packageName.ToLower());

        if (!Directory.Exists(nugetRoot))
        {
            throw new DirectoryNotFoundException($"NuGet package '{packageName}' not found at: {nugetRoot}");
        }

        // If version is not specified or is "*", find the latest version
        string packageDir;
        if (string.IsNullOrEmpty(version) || version == "*")
        {
            var versions = Directory.GetDirectories(nugetRoot)
                .Select(Path.GetFileName)
                .OrderByDescending(v => v)
                .ToList();

            if (!versions.Any())
            {
                throw new DirectoryNotFoundException($"No versions found for package '{packageName}'");
            }

            version = versions.First()!;
            packageDir = Path.Combine(nugetRoot, version);
        }
        else
        {
            packageDir = Path.Combine(nugetRoot, version);
            if (!Directory.Exists(packageDir))
            {
                throw new DirectoryNotFoundException($"Version '{version}' not found for package '{packageName}'");
            }
        }

        return packageDir;
    }

    static void CatalogTypes(string packageName, string version, string namespacePrefix,
        bool includeEnums = false, bool includeConstructors = false, bool includeMethods = false,
        bool includeProperties = false)
    {
        try
        {
            if (string.IsNullOrEmpty(packageName) || string.IsNullOrEmpty(namespacePrefix))
            {
                Console.Error.WriteLine("Error: --package and --namespace-prefix are required");
                Environment.Exit(1);
                return;
            }

            // Try to load assembly dynamically
            Assembly assembly;

            // Special case: if package is already loaded (like Aspose.Zip)
            if (packageName.Equals("Aspose.Zip", StringComparison.OrdinalIgnoreCase))
            {
                assembly = typeof(Aspose.Zip.Archive).Assembly;
            }
            else
            {
                // Locate NuGet package and load DLL
                var packageDir = LocateNuGetPackage(packageName, version);
                var dllPath = Path.Combine(packageDir, "lib", "net8.0", $"{packageName}.dll");

                // Try alternative paths if net8.0 not found
                if (!File.Exists(dllPath))
                {
                    var libDir = Path.Combine(packageDir, "lib");
                    var tfmDirs = Directory.GetDirectories(libDir)
                        .Select(Path.GetFileName)
                        .OrderByDescending(d => d)
                        .ToList();

                    foreach (var tfm in tfmDirs)
                    {
                        dllPath = Path.Combine(libDir, tfm!, $"{packageName}.dll");
                        if (File.Exists(dllPath))
                        {
                            break;
                        }
                    }
                }

                if (!File.Exists(dllPath))
                {
                    Console.Error.WriteLine($"Error: DLL not found for package '{packageName}' at: {dllPath}");
                    Environment.Exit(1);
                    return;
                }

                assembly = Assembly.LoadFrom(dllPath);
            }

            // Extract all public types in the namespace
            var exportedTypes = assembly.GetExportedTypes()
                .Where(t => t.IsPublic && !string.IsNullOrEmpty(t.Namespace) && t.Namespace!.StartsWith(namespacePrefix))
                .OrderBy(t => t.Namespace)
                .ThenBy(t => t.Name)
                .ToList();

            var typeInfos = exportedTypes
                .Select(t => new
                {
                    Name = t.Name,
                    Namespace = t.Namespace,
                    FullName = t.FullName,
                    Category = t.IsEnum ? "enum" : t.IsInterface ? "interface" : t.IsClass ? "class" : "other"
                })
                .ToList();

            // Build result structure
            var namespaces = typeInfos.Select(t => t.Namespace).Distinct().OrderBy(n => n).ToList();

            // Group types by name to detect ambiguous types (same name in different namespaces)
            var typesByName = typeInfos.GroupBy(t => t.Name).ToList();
            var ambiguousTypes = typesByName
                .Where(g => g.Count() > 1)
                .ToDictionary(g => g.Key, g => g.Select(t => t.Namespace).ToList());

            // For non-ambiguous types, create simple name->namespace map
            // For ambiguous types, use first namespace (Python validator will cross-reference)
            var simpleTypeMap = typesByName.ToDictionary(g => g.Key, g => g.First().Namespace);

            // Create full map using FullName as key to avoid conflicts
            var fullTypeMap = typeInfos.ToDictionary(t => t.FullName!, t => new { t.Name, t.Namespace, t.Category });

            // --- Optional enrichment sections ---

            // Enums: extract member names and values for each enum type
            Dictionary<string, List<string>>? enumsDict = null;
            if (includeEnums)
            {
                enumsDict = new Dictionary<string, List<string>>();
                foreach (var enumType in exportedTypes.Where(t => t.IsEnum))
                {
                    var members = enumType.GetFields(BindingFlags.Public | BindingFlags.Static)
                        .Select(f => f.Name)
                        .ToList();
                    enumsDict[enumType.Name] = members;
                }
            }

            // Constructors: extract public constructor signatures for each type
            Dictionary<string, List<Dictionary<string, string>>>? constructorsDict = null;
            if (includeConstructors)
            {
                constructorsDict = new Dictionary<string, List<Dictionary<string, string>>>();
                foreach (var type in exportedTypes.Where(t => !t.IsEnum && !t.IsInterface))
                {
                    var ctors = type.GetConstructors(BindingFlags.Public | BindingFlags.Instance);
                    if (ctors.Length > 0)
                    {
                        var ctorList = new List<Dictionary<string, string>>();
                        foreach (var ctor in ctors)
                        {
                            var parameters = ctor.GetParameters();
                            var paramStr = string.Join(", ", parameters.Select(p => FormatParameterType(p) + " " + p.Name));
                            ctorList.Add(new Dictionary<string, string> { { "params", paramStr } });
                        }
                        constructorsDict[type.Name] = ctorList;
                    }
                }
            }

            // Key methods: extract signatures for commonly-used methods
            Dictionary<string, List<Dictionary<string, string>>>? methodsDict = null;
            if (includeMethods)
            {
                var keyMethodNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
                {
                    "Save", "Load", "Extract", "Open", "Create", "Add", "Remove",
                    "SaveSplit", "CreateEntry", "CreateEntries", "DeleteEntry",
                    "ExtractToDirectory"
                };

                methodsDict = new Dictionary<string, List<Dictionary<string, string>>>();
                foreach (var type in exportedTypes.Where(t => !t.IsEnum))
                {
                    var methods = type.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static)
                        .Where(m => !m.IsSpecialName && keyMethodNames.Any(k => m.Name.Contains(k, StringComparison.OrdinalIgnoreCase)))
                        .ToList();

                    if (methods.Count > 0)
                    {
                        var methodList = new List<Dictionary<string, string>>();
                        foreach (var method in methods)
                        {
                            var parameters = method.GetParameters();
                            var paramStr = string.Join(", ", parameters.Select(p => FormatParameterType(p) + " " + p.Name));
                            var returnType = FormatTypeName(method.ReturnType);
                            methodList.Add(new Dictionary<string, string>
                            {
                                { "name", method.Name },
                                { "params", paramStr },
                                { "returns", returnType },
                                { "static", method.IsStatic ? "true" : "false" }
                            });
                        }
                        methodsDict[type.Name] = methodList;
                    }
                }
            }

            // Properties: extract all public property names for each type (for CS1061 member-not-found fixes)
            Dictionary<string, List<string>>? propertiesDict = null;
            if (includeProperties)
            {
                propertiesDict = new Dictionary<string, List<string>>();
                foreach (var type in exportedTypes.Where(t => !t.IsEnum))
                {
                    var props = type.GetProperties(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static)
                        .Select(p => p.Name)
                        .Distinct()
                        .OrderBy(n => n)
                        .ToList();
                    if (props.Count > 0)
                    {
                        propertiesDict[type.Name] = props;
                    }
                }
            }

            // Build result object — conditionally include enrichment sections
            var resultDict = new Dictionary<string, object?>
            {
                ["Namespaces"] = namespaces,
                ["Types"] = simpleTypeMap,
                ["TypesFullMap"] = fullTypeMap,
                ["AmbiguousTypes"] = ambiguousTypes,
                ["AssemblyVersion"] = assembly.GetName().Version?.ToString(),
                ["AssemblyFullName"] = assembly.FullName,
                ["TotalTypes"] = typeInfos.Count,
                ["TotalNamespaces"] = namespaces.Count
            };

            if (enumsDict != null)
                resultDict["Enums"] = enumsDict;
            if (constructorsDict != null)
                resultDict["Constructors"] = constructorsDict;
            if (methodsDict != null)
                resultDict["KeyMethods"] = methodsDict;
            if (propertiesDict != null)
                resultDict["Properties"] = propertiesDict;

            // Output JSON to stdout
            var json = JsonConvert.SerializeObject(resultDict, Formatting.Indented);
            Console.WriteLine(json);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Error during catalog generation: {ex.Message}");
            Console.Error.WriteLine(ex.StackTrace);
            Environment.Exit(1);
        }
    }

    /// <summary>
    /// Format a parameter's type name for display, handling nullable and generic types.
    /// </summary>
    static string FormatParameterType(ParameterInfo param)
    {
        var typeName = FormatTypeName(param.ParameterType);
        // Append ? for nullable reference type parameters (optional params in C#)
        if (param.HasDefaultValue && !param.ParameterType.IsValueType)
        {
            if (!typeName.EndsWith("?"))
                typeName += "?";
        }
        return typeName;
    }

    /// <summary>
    /// Format a Type to a clean, readable name (e.g. Nullable types, generics).
    /// </summary>
    static string FormatTypeName(Type type)
    {
        // Handle nullable value types (e.g. int?, bool?)
        if (type.IsGenericType && type.GetGenericTypeDefinition() == typeof(Nullable<>))
        {
            return FormatTypeName(type.GetGenericArguments()[0]) + "?";
        }

        // Handle common built-in type aliases
        if (type == typeof(void)) return "void";
        if (type == typeof(string)) return "string";
        if (type == typeof(int)) return "int";
        if (type == typeof(long)) return "long";
        if (type == typeof(bool)) return "bool";
        if (type == typeof(float)) return "float";
        if (type == typeof(double)) return "double";
        if (type == typeof(byte)) return "byte";
        if (type == typeof(char)) return "char";
        if (type == typeof(object)) return "object";

        // Handle generic types (e.g. List<T>, Dictionary<K,V>)
        if (type.IsGenericType)
        {
            var baseName = type.Name.Split('`')[0];
            var args = type.GetGenericArguments().Select(FormatTypeName);
            return $"{baseName}<{string.Join(", ", args)}>";
        }

        // Handle arrays
        if (type.IsArray)
        {
            return FormatTypeName(type.GetElementType()!) + "[]";
        }

        // Use simple name (strip namespace) for readability
        return type.Name;
    }
}
