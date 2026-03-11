-- Migration 012: Add article_intent for semantic intent validation
-- Purpose: Store compact article intent (title + description + steps) from YAML frontmatter
-- Context: Phase E (final review) uses this to check code aligns with what the article claims

-- Add article_intent to example_records (canonical record)
-- This stores the frontmatter-derived intent string (capped at 800 chars)
ALTER TABLE example_records ADD COLUMN article_intent TEXT DEFAULT NULL;

-- NOTE: Migration recording is handled automatically by the migration engine
-- DO NOT manually INSERT into schema_migrations here
