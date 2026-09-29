-- Local runtime heartbeat table for component liveness tracking.
-- This is runtime metadata, NOT a tenant data migration.
-- Rollback: stop new code accessing this table; keep the table and its data.
--           Do NOT drop any generation results or tenant data on rollback.
-- Deployment: test in a dedicated schema before applying to the daily database.
BEGIN;

CREATE TABLE IF NOT EXISTS runtime_heartbeats (
    runtime_id   text NOT NULL,
    component    text NOT NULL,
    instance_id  text NOT NULL,
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    metadata     jsonb NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (runtime_id, component, instance_id)
);

COMMENT ON TABLE runtime_heartbeats IS
    'Local runtime heartbeat for component liveness tracking (readiness probes). '
    'This is runtime metadata, not a tenant data migration. '
    'Rollback: retain table; do not DROP.';

COMMENT ON COLUMN runtime_heartbeats.runtime_id IS
    'Deployment identity (e.g. zhijuan-local). Cross-runtime heartbeats are rejected by the application.';
COMMENT ON COLUMN runtime_heartbeats.component IS
    'Component name: worker, dispatcher, api, author, solver.';
COMMENT ON COLUMN runtime_heartbeats.instance_id IS
    'Process-unique instance identifier (uuid4.hex), regenerated on each start.';
COMMENT ON COLUMN runtime_heartbeats.last_seen_at IS
    'Server-side timestamp of the last heartbeat, always set by DB now().';
COMMENT ON COLUMN runtime_heartbeats.metadata IS
    'Non-secret metadata: model_id, gateway endpoint host:port, config version.';

CREATE INDEX IF NOT EXISTS idx_runtime_heartbeats_last_seen
    ON runtime_heartbeats (last_seen_at);
