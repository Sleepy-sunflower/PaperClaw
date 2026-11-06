CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE papers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users (id),
    filename text NOT NULL,
    content_sha256 text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, content_sha256)
);

CREATE TABLE chunks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id uuid NOT NULL REFERENCES papers (id),
    user_id uuid NOT NULL REFERENCES users (id),
    page integer NOT NULL,
    content text NOT NULL,
    embedding vector(2048) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ingest_tasks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users (id),
    filename text NOT NULL,
    content_sha256 text NOT NULL,
    pdf bytea NOT NULL,
    status text NOT NULL,
    log text[] NOT NULL DEFAULT '{}',
    paper_id uuid REFERENCES papers (id),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, content_sha256)
);
