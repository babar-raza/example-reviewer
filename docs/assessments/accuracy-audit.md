# Family Accuracy Audit

> Last updated: 2026-04-20
> Source data: [evals/family_accuracy_report.json](../../evals/family_accuracy_report.json)
> Methodology: [evals/methodology.md](../../evals/methodology.md)

## Summary

This document provides the human-readable accuracy audit trail for all
production families in Example Reviewer. It explains what the accuracy figures
in [README.md Section 9](../../README.md#9-supported-families) mean, where they
come from, and why the unverified fraction exists.

## Methodology (Short Form)

An example is **verified** when it:
1. Compiles successfully with `dotnet build` (after deterministic or LLM-assisted fix)
2. Runs to completion without exception
3. Passes the LLM final review gate (semantic fidelity confirmed)

All three must pass. See [evals/methodology.md](../../evals/methodology.md) for full definitions.

## Current Accuracy Table

| Family | Discovered | Verified | Rate | Status | Baseline |
|--------|-----------|---------|------|--------|---------|
| ZIP | 66 | 61 | 92.4% | Production | [zip_baseline.json](../../.benchmarks/baselines/zip_baseline.json) |
| PSD | 391 | 347 | 88.7% | Production | pending config |
| HTML | 16 | 14 | 87.5% | Production | [html_baseline.json](../../.benchmarks/baselines/html_baseline.json) |
| Email | 20 | 17 | 85.0% | Production | [email_baseline.json](../../.benchmarks/baselines/email_baseline.json) |
| Words | 147 | 123 | 83.7% | Production | [words_baseline.json](../../.benchmarks/baselines/words_baseline.json) |
| PDF | 825 | 684 | 82.9% | Production | [pdf_baseline.json](../../.benchmarks/baselines/pdf_baseline.json) |
| TeX | 45 | 37 | 82.2% | Production | [tex_baseline.json](../../.benchmarks/baselines/tex_baseline.json) |
| Barcode | 201 | 161 | 80.1% | Production | pending config |
| CAD | 10 | 8 | 80.0% | Production | [cad_baseline.json](../../.benchmarks/baselines/cad_baseline.json) |
| Imaging | 217 | 138 | 63.6% | Production | [imaging_baseline.json](../../.benchmarks/baselines/imaging_baseline.json) |
| Cells | 196 | 121 | 61.7% | Production | [cells_baseline.json](../../.benchmarks/baselines/cells_baseline.json) |
| Slides | 551 | 223 | 40.5% | Production | [slides_baseline.json](../../.benchmarks/baselines/slides_baseline.json) |
| OCR | 115 | 41 | 35.7% | Production | pending config |
| Medical | 88 | 6 | 6.8% | Early | [medical_baseline.json](../../.benchmarks/baselines/medical_baseline.json) |
| Page | 8 | 0 | 0% | Early | [page_baseline.json](../../.benchmarks/baselines/page_baseline.json) |
| Tasks | 6 | 0 | 0% | Early | [tasks_baseline.json](../../.benchmarks/baselines/tasks_baseline.json) |

## Unverified Fraction Analysis

### ZIP (7.6% unverified — 5 examples)

The 5 unverified ZIP examples fall into two categories:

**2 compile-failed (COMPILE_FAILED)**
API members removed in Aspose.ZIP 25.x. The examples call methods that no
longer exist (CS1061 "does not contain a definition for X"). The LLM cannot
reconstruct the correct replacement without knowing the new API, and the API
change log is not in the KB hints. These examples require manual KB hint
additions to fix.

**3 runtime-failed (RUNTIME_FAILED)**
Examples require encrypted archive fixtures (e.g. `encrypted_password.zip`).
The 5-tier fixture resolver does not have these files in any tier. The fix
path is either adding fixture files or adding generation code.

### Words (16.3% unverified — 24 examples)

**~8 compile-failed**
Aspose.Words API evolved significantly between 24.x and 25.x. Method
signatures changed on `DocumentBuilder`, `Shape`, and mail-merge classes.
KB hints cover the most common patterns (9 hints in `words_review_hints.json`)
but uncommon API surface is not yet covered.

**~16 runtime-failed**
Examples requiring `.docx` templates or mail-merge data sources that are not
in the fixture tree. Fixture resolver tier 3 (family-specific directory) would
handle these if the fixture files were added.

### PDF (17.1% unverified — 141 examples)

PDF has the highest absolute unverified count (141 of 825) because it has the
largest discovered set. The proportional rate (82.9%) is close to the
Words/TeX range.

**~80 compile-failed**
Aspose.PDF API surface is large and changes frequently. Missing namespace
imports, renamed classes (`Document` → `PdfDocument` in some contexts), and
removed convenience overloads are the most common patterns. No KB hints
exist yet for PDF — adding even 3–5 review hints for the most common
CS0246/CS1061 patterns would have a measurable impact.

**~61 runtime-failed**
PDF runtime failures are primarily missing source files (PDFs, images) that
fixture resolver tier 2 (runtime-testdata directory) does not yet have.

### Imaging (36.4% unverified — 79 examples)

Imaging has a lower verification rate because:
1. The API changed substantially between Aspose.Imaging 22.x and 25.x
2. Many examples depend on image fixtures not in the fixture tree
3. No KB hints exist yet

### Cells, Slides (low rates)

Both families have rates below 65%. Primary cause: large API surface with
many changed overloads + high fixture dependency (spreadsheets, presentations
referenced in examples). These are known hard families. Work is ongoing.

### Early Families (Medical, Page, Tasks)

These families are in initial onboarding. Low rates reflect:
- Medical: namespace and terminology changes between library versions
- Page: very small family (8 examples); all currently fail with import errors
- Tasks: very small family (6 examples); fixture dependencies not yet set up

## Claim History

| Date | Change | Notes |
|------|--------|-------|
| 2026-04-20 | Initial baseline commit | All figures from production run data as documented in README Section 9. Baselines in `.benchmarks/baselines/`. |

## Updating This Audit

After refreshing baselines with `generate_baseline.py`, update:
1. The accuracy table above
2. The unverified fraction analysis for families with meaningful changes
3. The claim history table with a new row
4. `evals/family_accuracy_report.json` → `report_date` field
