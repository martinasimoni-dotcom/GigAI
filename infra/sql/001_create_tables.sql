-- 001_create_tables.sql
-- GigAI core schema
-- Run: psql $DATABASE_URL -f infra/sql/001_create_tables.sql

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS events (
    event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type      TEXT NOT NULL,
    source          TEXT NOT NULL CHECK (source IN ('fireflies', 'acc', 'gmail', 'calendar')),
    raw_data        JSONB,
    normalized_data JSONB,
    enriched_data   JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at    TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS proposals (
    proposal_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id         UUID REFERENCES events(event_id) ON DELETE CASCADE,
    alert            JSONB NOT NULL,
    actions          JSONB NOT NULL DEFAULT '[]',
    confidence_score FLOAT NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    recommendation   TEXT NOT NULL CHECK (recommendation IN ('accept', 'review', 'reject')),
    status           TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS actions (
    action_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID REFERENCES proposals(proposal_id) ON DELETE CASCADE,
    action_type TEXT NOT NULL CHECK (action_type IN ('email', 'task', 'calendar', 'drawing')),
    action_data JSONB NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'executed', 'failed')),
    executed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id             UUID REFERENCES proposals(proposal_id) ON DELETE CASCADE,
    decision                TEXT NOT NULL CHECK (decision IN ('accepted', 'rejected')),
    rejection_reason        TEXT,
    confidence_at_decision  FLOAT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS past_changes (
    change_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    change_type     TEXT NOT NULL,
    material_from   TEXT,
    material_to     TEXT,
    location        TEXT,
    cost            FLOAT,
    outcome         TEXT,
    success_rate    FLOAT,
    embedding       vector(1024),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content     TEXT NOT NULL,
    embedding   vector(1024) NOT NULL,
    source      TEXT NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}'
);
