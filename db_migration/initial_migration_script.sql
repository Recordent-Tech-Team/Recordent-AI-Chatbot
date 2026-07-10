-- Recordent AI Chatbot initial database schema
-- Run this manually against the target PostgreSQL database.

BEGIN;

CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS "dev_ai_chatbot";
SET search_path TO "dev_ai_chatbot", public;

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'session_status'
          AND n.nspname = 'dev_ai_chatbot'
    ) THEN
        CREATE TYPE "dev_ai_chatbot".session_status AS ENUM ('active', 'closed');
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'evaluation_run_status'
          AND n.nspname = 'dev_ai_chatbot'
    ) THEN
        CREATE TYPE "dev_ai_chatbot".evaluation_run_status AS ENUM ('queued', 'running', 'completed', 'failed');
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'document_version_status'
          AND n.nspname = 'dev_ai_chatbot'
    ) THEN
        CREATE TYPE "dev_ai_chatbot".document_version_status AS ENUM ('active', 'archived', 'pending');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS "dev_ai_chatbot".chat_sessions (
    id SERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    status "dev_ai_chatbot".session_status NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL,
    closed_at TIMESTAMPTZ NULL
);

CREATE TABLE IF NOT EXISTS "dev_ai_chatbot".document_versions (
    id SERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    version INTEGER NOT NULL,
    status "dev_ai_chatbot".document_version_status NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE TABLE IF NOT EXISTS "dev_ai_chatbot".audit_logs (
    id SERIAL PRIMARY KEY,
    action VARCHAR(128) NOT NULL,
    metadata JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE TABLE IF NOT EXISTS "dev_ai_chatbot".chat_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES "dev_ai_chatbot".chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    response TEXT NULL,
    response_time_ms INTEGER NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id
ON "dev_ai_chatbot".chat_messages (session_id);

CREATE TABLE IF NOT EXISTS "dev_ai_chatbot".documents (
    id SERIAL PRIMARY KEY,
    document_version_id INTEGER NOT NULL REFERENCES "dev_ai_chatbot".document_versions(id) ON DELETE CASCADE,
    file_name VARCHAR(512) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    s3_path VARCHAR(1024) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_documents_document_version_id
ON "dev_ai_chatbot".documents (document_version_id);

CREATE TABLE IF NOT EXISTS "dev_ai_chatbot".embeddings (
    id SERIAL PRIMARY KEY,
    document_version_id INTEGER NOT NULL REFERENCES "dev_ai_chatbot".document_versions(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    embedding public.vector(1024) NOT NULL,
    chunk_index INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_embeddings_document_version_id
ON "dev_ai_chatbot".embeddings (document_version_id);

CREATE INDEX IF NOT EXISTS ix_embeddings_vector
ON "dev_ai_chatbot".embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE TABLE IF NOT EXISTS "dev_ai_chatbot".embedding_archives (
    id SERIAL PRIMARY KEY,
    document_version_id INTEGER NOT NULL REFERENCES "dev_ai_chatbot".document_versions(id) ON DELETE CASCADE,
    archived_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_embedding_archives_document_version_id
ON "dev_ai_chatbot".embedding_archives (document_version_id);

CREATE TABLE IF NOT EXISTS "dev_ai_chatbot".evaluation_logs (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NULL REFERENCES "dev_ai_chatbot".chat_sessions(id) ON DELETE SET NULL,
    question TEXT NOT NULL,
    retrieved_chunks JSONB NULL,
    answer TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    token_usage JSONB NULL,
    retrieval_score DOUBLE PRECISION NULL,
    grounding_score DOUBLE PRECISION NULL,
    quality_score DOUBLE PRECISION NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_evaluation_logs_session_id
ON "dev_ai_chatbot".evaluation_logs (session_id);

CREATE TABLE IF NOT EXISTS "dev_ai_chatbot".golden_datasets (
    id SERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE TABLE IF NOT EXISTS "dev_ai_chatbot".golden_dataset_cases (
    id SERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    dataset_id INTEGER NOT NULL REFERENCES "dev_ai_chatbot".golden_datasets(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    expected_answer TEXT NOT NULL,
    expected_sources JSONB NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_golden_dataset_cases_dataset_id
ON "dev_ai_chatbot".golden_dataset_cases (dataset_id);

CREATE TABLE IF NOT EXISTS "dev_ai_chatbot".evaluation_runs (
    id SERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    dataset_id INTEGER NULL REFERENCES "dev_ai_chatbot".golden_datasets(id) ON DELETE SET NULL,
    status "dev_ai_chatbot".evaluation_run_status NOT NULL DEFAULT 'queued',
    total_cases INTEGER NOT NULL DEFAULT 0,
    completed_cases INTEGER NOT NULL DEFAULT 0,
    failed_cases INTEGER NOT NULL DEFAULT 0,
    error_message TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_evaluation_runs_dataset_id
ON "dev_ai_chatbot".evaluation_runs (dataset_id);

CREATE TABLE IF NOT EXISTS "dev_ai_chatbot".evaluation_results (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NULL REFERENCES "dev_ai_chatbot".evaluation_runs(id) ON DELETE SET NULL,
    dataset_case_id INTEGER NULL REFERENCES "dev_ai_chatbot".golden_dataset_cases(id) ON DELETE SET NULL,
    question TEXT NOT NULL,
    expected_answer TEXT NOT NULL,
    generated_answer TEXT NOT NULL,
    retrieved_context JSONB NULL,
    recall_score DOUBLE PRECISION NULL,
    precision_score DOUBLE PRECISION NULL,
    correctness_score DOUBLE PRECISION NULL,
    relevancy_score DOUBLE PRECISION NULL,
    completeness_score DOUBLE PRECISION NULL,
    faithfulness_score DOUBLE PRECISION NULL,
    hallucination_score DOUBLE PRECISION NULL,
    citation_supported BOOLEAN NULL,
    overall_score DOUBLE PRECISION NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_evaluation_results_run_id
ON "dev_ai_chatbot".evaluation_results (run_id);

CREATE INDEX IF NOT EXISTS ix_evaluation_results_dataset_case_id
ON "dev_ai_chatbot".evaluation_results (dataset_case_id);

CREATE INDEX IF NOT EXISTS ix_evaluation_results_created_at
ON "dev_ai_chatbot".evaluation_results (created_at);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_chat_sessions_updated_at ON "dev_ai_chatbot".chat_sessions;
CREATE TRIGGER trg_chat_sessions_updated_at
BEFORE UPDATE ON "dev_ai_chatbot".chat_sessions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_document_versions_updated_at ON "dev_ai_chatbot".document_versions;
CREATE TRIGGER trg_document_versions_updated_at
BEFORE UPDATE ON "dev_ai_chatbot".document_versions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_audit_logs_updated_at ON "dev_ai_chatbot".audit_logs;
CREATE TRIGGER trg_audit_logs_updated_at
BEFORE UPDATE ON "dev_ai_chatbot".audit_logs
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_chat_messages_updated_at ON "dev_ai_chatbot".chat_messages;
CREATE TRIGGER trg_chat_messages_updated_at
BEFORE UPDATE ON "dev_ai_chatbot".chat_messages
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_documents_updated_at ON "dev_ai_chatbot".documents;
CREATE TRIGGER trg_documents_updated_at
BEFORE UPDATE ON "dev_ai_chatbot".documents
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_embeddings_updated_at ON "dev_ai_chatbot".embeddings;
CREATE TRIGGER trg_embeddings_updated_at
BEFORE UPDATE ON "dev_ai_chatbot".embeddings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_embedding_archives_updated_at ON "dev_ai_chatbot".embedding_archives;
CREATE TRIGGER trg_embedding_archives_updated_at
BEFORE UPDATE ON "dev_ai_chatbot".embedding_archives
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_evaluation_logs_updated_at ON "dev_ai_chatbot".evaluation_logs;
CREATE TRIGGER trg_evaluation_logs_updated_at
BEFORE UPDATE ON "dev_ai_chatbot".evaluation_logs
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_golden_datasets_updated_at ON "dev_ai_chatbot".golden_datasets;
CREATE TRIGGER trg_golden_datasets_updated_at
BEFORE UPDATE ON "dev_ai_chatbot".golden_datasets
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_golden_dataset_cases_updated_at ON "dev_ai_chatbot".golden_dataset_cases;
CREATE TRIGGER trg_golden_dataset_cases_updated_at
BEFORE UPDATE ON "dev_ai_chatbot".golden_dataset_cases
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_evaluation_runs_updated_at ON "dev_ai_chatbot".evaluation_runs;
CREATE TRIGGER trg_evaluation_runs_updated_at
BEFORE UPDATE ON "dev_ai_chatbot".evaluation_runs
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_evaluation_results_updated_at ON "dev_ai_chatbot".evaluation_results;
CREATE TRIGGER trg_evaluation_results_updated_at
BEFORE UPDATE ON "dev_ai_chatbot".evaluation_results
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

COMMIT;
