-- Migration 011: Add code block location metadata for safe md_update targeting
-- Purpose: Enable deterministic block replacement in markdown files with multiple code blocks
-- Context: Fix md_update multi-block targeting (root-cause, safe, backward compatible)
--
-- This migration adds code_block_signature to track the original content hash,
-- enabling verification before replacement in md_update.

-- Add code_block_signature to example_records (canonical record)
-- This stores sha256 hash of the normalized original code content
ALTER TABLE example_records ADD COLUMN code_block_signature TEXT DEFAULT NULL;

-- Add code_block_signature index for efficient lookup
CREATE INDEX IF NOT EXISTS idx_example_records_signature ON example_records(code_block_signature);

-- Add extraction_warning to flag ambiguous extraction cases
-- If extractor cannot determine block index deterministically, this will be set
ALTER TABLE example_records ADD COLUMN extraction_warning TEXT DEFAULT NULL;

-- NOTE: Migration recording is handled automatically by the migration engine
-- DO NOT manually INSERT into schema_migrations here
