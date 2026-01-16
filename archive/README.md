# Archive Directory

This directory contains archived files from repository cleanup operations.

## Purpose

As the project evolves, temporary analysis scripts and old documentation accumulate in the root directory. This archive preserves these files while keeping the root directory clean and navigable.

## Contents

### analysis-scripts/
Temporary analysis, validation, and debugging scripts created during development and troubleshooting. These scripts were useful for specific investigations but are not part of the core codebase.

### old-summaries/
Historical summary documents and reports that have been superseded by newer documentation or are no longer actively referenced.

## Recovery

All files here were moved using `git mv` to preserve git history. To view a file's history:

```bash
git log --follow archive/analysis-scripts/<filename>
```

## Cleanup History

- 2026-01-16: Initial cleanup (Task IH-04) - Moved 21 analysis scripts and 2 old summary files
