# test-examples/ - .NET Compilation Project

This is a .NET 8.0 console project used to compile and run C# code examples.

## How It Works

The pipeline writes extracted C# code to `Program.cs`, then runs `dotnet build` and `dotnet run` against this project. The `.csproj` file includes NuGet package references for the target Aspose family.

## Key Files

- `AsposeZipValidator.csproj` - Project file with NuGet package references
- `Program.cs` - Overwritten per-example during pipeline execution (gitignored)
- `CatalogTypes.cs` - Assembly reflection tool for generating API catalogs

## Usage

This directory is managed automatically by the pipeline. Do not edit `Program.cs` manually.

```bash
# The pipeline does this internally:
dotnet build test-examples/AsposeZipValidator.csproj
dotnet run --project test-examples/AsposeZipValidator.csproj
```
