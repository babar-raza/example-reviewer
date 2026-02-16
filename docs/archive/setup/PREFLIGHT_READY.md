# Families Ready for Preflight Testing

**Date:** 2026-02-16

## Ready to Run

The following families are fully configured and ready for preflight discovery testing:

### Newly Configured (2 families)

1. **IMAGING** (9,233 files - 2nd largest family!)
   - Config: ✅ Complete
   - Catalog: ✅ Generated (671 KB, 1,231 types, 119 namespaces)
   - Test Data: ✅ Directory created
   - Repo: ✅ https://github.com/aspose-imaging/Aspose.Imaging-for-.NET

2. **EMAIL** (621 files)
   - Config: ✅ Complete
   - Catalog: ✅ Generated (1.1 MB - includes enums, constructors, methods, properties)
   - Test Data: ✅ Directory created
   - Repo: ✅ https://github.com/aspose-email/Aspose.Email-for-.NET

## Run Preflight Commands

```bash
# Run discovery tests for both families
c:/Users/prora/.venv/Scripts/python.exe -m src.cli.main verify --family imaging --max-examples 10
c:/Users/prora/.venv/Scripts/python.exe -m src.cli.main verify --family email --max-examples 10

# Or run full pipeline (limited to 20 examples each)
c:/Users/prora/.venv/Scripts/python.exe -m src.cli.main verify --family imaging --max-examples 20
c:/Users/prora/.venv/Scripts/python.exe -m src.cli.main verify --family email --max-examples 20
```

## Expected Outcomes

### Imaging Family
- High content volume (9,233 files)
- Rich API catalog (1,231 types)
- Should discover 50-200 examples
- Target: 70%+ verification rate

### Email Family
- Lower content volume (621 files)
- Very rich API catalog (1.1 MB)
- Should discover 20-50 examples
- Target: 60%+ verification rate

## Next Steps After Preflight

1. **If preflight successful (>50% verified):**
   - Run full pipeline without max-examples limit
   - Monitor for patterns that need deterministic fixes
   - Add to learned_patterns database

2. **If preflight needs improvement (<50%):**
   - Analyze common failure patterns
   - Add deterministic fixes to semantic_microfixes.py
   - Update fixture_resolver for missing test files

3. **Complete remaining families:**
   - Install missing NuGet packages (slides, tex, cad, html, page, tasks)
   - Generate remaining catalogs
   - Run preflights for all families
