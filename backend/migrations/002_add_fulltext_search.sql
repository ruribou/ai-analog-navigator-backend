-- Migration: 002_add_fulltext_search.sql
-- Description: Add full-text search support (tsvector) for Hybrid search strategy
-- Created: 2025-11-20

-- ============================================================================
-- Add tsvector column for BM25-style full-text search
-- ============================================================================

-- Add text_tsv column (generated from text column)
-- Note: Using 'simple' config as 'japanese' is not available in standard PostgreSQL
-- 'simple' splits on whitespace and punctuation but doesn't stem or remove stop words
ALTER TABLE chunks
ADD COLUMN IF NOT EXISTS text_tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', coalesce(text, ''))) STORED;

-- Create GIN index for full-text search
CREATE INDEX IF NOT EXISTS chunks_text_tsv_gin
  ON chunks USING gin(text_tsv);

-- ============================================================================
-- Verification query (optional - for testing)
-- ============================================================================
-- Example query to test full-text search:
-- SELECT chunk_id, text, 
--        ts_rank_cd(text_tsv, plainto_tsquery('simple', 'IoT')) AS rank
-- FROM chunks
-- WHERE text_tsv @@ plainto_tsquery('simple', 'IoT')
-- ORDER BY rank DESC
-- LIMIT 5;

