-- Migration: 001_init_vector_db.sql
-- Description: Initialize pgvector extension and create documents/chunks tables for RAG
-- Created: 2025-11-20

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- documents table: Manage source document metadata
-- ============================================================================
CREATE TABLE IF NOT EXISTS documents (
  doc_id          UUID PRIMARY KEY,
  source_url      TEXT NOT NULL,
  source_type     TEXT NOT NULL,  -- school_hp / lab_hp / pdf / news
  title           TEXT,
  lang            TEXT DEFAULT 'ja',
  fetched_at      TIMESTAMPTZ NOT NULL,
  updated_at      TIMESTAMPTZ,
  content_hash    TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'active', -- active / superseded / error
  meta            JSONB DEFAULT '{}'::jsonb
);

-- Indexes for documents
CREATE UNIQUE INDEX IF NOT EXISTS documents_source_url_uq ON documents(source_url);
CREATE INDEX IF NOT EXISTS documents_status_idx ON documents(status);

-- ============================================================================
-- chunks table: Store text chunks with embeddings
-- ============================================================================
CREATE TABLE IF NOT EXISTS chunks (
  chunk_id        UUID PRIMARY KEY,
  doc_id          UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
  chunk_index     INT NOT NULL,
  text            TEXT NOT NULL,
  token_count     INT,
  heading_path    TEXT[],
  tags            TEXT[],

  -- Prefilter columns for structured search
  campus          TEXT,
  building        TEXT,
  department      TEXT,
  lab             TEXT,
  professor       TEXT[],

  validity_start  DATE,
  validity_end    DATE,

  source_url      TEXT NOT NULL,

  -- Embedding fields
  embedding       VECTOR(768) NOT NULL, -- text-embedding-nomic-embed-text-v1.5
  embedding_model TEXT NOT NULL,
  embedding_dim   INT NOT NULL,
  version         INT NOT NULL DEFAULT 1,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for chunks
CREATE UNIQUE INDEX IF NOT EXISTS chunks_doc_order_uq ON chunks(doc_id, chunk_index);

-- BTree indexes for prefilter columns
CREATE INDEX IF NOT EXISTS chunks_campus_idx ON chunks(campus);
CREATE INDEX IF NOT EXISTS chunks_building_idx ON chunks(building);
CREATE INDEX IF NOT EXISTS chunks_department_idx ON chunks(department);
CREATE INDEX IF NOT EXISTS chunks_lab_idx ON chunks(lab);

-- GIN indexes for array columns
CREATE INDEX IF NOT EXISTS chunks_professor_gin ON chunks USING gin(professor);
CREATE INDEX IF NOT EXISTS chunks_tags_gin ON chunks USING gin(tags);

-- Index for validity date range
CREATE INDEX IF NOT EXISTS chunks_validity_idx ON chunks(validity_start, validity_end);

-- ============================================================================
-- HNSW index for vector similarity search
-- ============================================================================
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
  ON chunks USING hnsw (embedding vector_cosine_ops)
  WITH (m=16, ef_construction=128);

