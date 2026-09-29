-- Apply only after the PostgreSQL deployment is configured; no migration runs on import.
CREATE TABLE IF NOT EXISTS generation_jobs (
    exam_id text PRIMARY KEY,
    snapshot jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS generation_exam_revisions (
    exam_id text PRIMARY KEY,
    spec_revision integer NOT NULL
);
CREATE TABLE IF NOT EXISTS generation_job_outbox (
    id bigserial PRIMARY KEY,
    job_id text NOT NULL,
    event_type text NOT NULL,
    dispatched_at timestamptz,
    UNIQUE (job_id, event_type)
);
CREATE TABLE IF NOT EXISTS generation_job_results (
    job_id text NOT NULL,
    slot_id text NOT NULL,
    candidate jsonb NOT NULL,
    validation jsonb NOT NULL,
    PRIMARY KEY (job_id, slot_id)
);

CREATE TABLE IF NOT EXISTS generation_job_history (
    job_id text PRIMARY KEY,
    exam_id text NOT NULL,
    snapshot jsonb NOT NULL
);
