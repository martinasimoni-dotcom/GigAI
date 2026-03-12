-- 002_create_indexes.sql
-- GigAI HNSW vector indexes + B-tree supporting indexes
-- Run AFTER 001_create_tables.sql
-- Requires: PostgreSQL 15+, pgvector extension >= 0.5.0

-- HNSW index on knowledge_chunks.embedding (primary vector search target)
-- m=16 (default, good balance of build time vs query speed)
-- ef_construction=64 (default, good recall at reasonable build cost)
CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_hnsw_idx
    ON knowledge_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- HNSW index on past_changes.embedding (historical similarity search)
CREATE INDEX IF NOT EXISTS past_changes_embedding_hnsw_idx
    ON past_changes
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- B-tree supporting indexes for FK lookups and status filtering
CREATE INDEX IF NOT EXISTS proposals_event_id_idx ON proposals (event_id);
CREATE INDEX IF NOT EXISTS proposals_status_idx ON proposals (status);
CREATE INDEX IF NOT EXISTS actions_proposal_id_idx ON actions (proposal_id);
CREATE INDEX IF NOT EXISTS actions_status_idx ON actions (status);
CREATE INDEX IF NOT EXISTS feedback_proposal_id_idx ON feedback (proposal_id);
CREATE INDEX IF NOT EXISTS events_source_idx ON events (source);
CREATE INDEX IF NOT EXISTS events_event_type_idx ON events (event_type);
CREATE INDEX IF NOT EXISTS events_created_at_idx ON events (created_at DESC);
