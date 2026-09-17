-- PostgreSQL 18 domain schema DRAFT; not a production-ready migration.
-- Use Alembic after review and real PostgreSQL tests. No production login grants,
-- OIDC callbacks, partitioning, retention jobs or complete migration history here.
-- Runtime role MUST NOT own these tables or have superuser/BYPASSRLS.
BEGIN;
CREATE SCHEMA IF NOT EXISTS zhijuan;
SET search_path TO zhijuan, public;

CREATE TABLE tenants (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE users (
  id uuid PRIMARY KEY,
  oidc_subject text UNIQUE NOT NULL,
  display_name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE memberships (
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  user_id uuid NOT NULL REFERENCES users(id),
  role text NOT NULL CHECK (role IN ('author','reviewer','admin','operator')),
  PRIMARY KEY (tenant_id,user_id,role)
);
CREATE TABLE exams (
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  id uuid NOT NULL,
  revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
  state text NOT NULL CHECK (state IN ('DRAFT','PLANNING','PLAN_READY','GENERATING','REVIEW_READY','APPROVED','PUBLISHED','ARCHIVED')),
  title text NOT NULL,
  spec_json jsonb NOT NULL CHECK (jsonb_typeof(spec_json)='object'),
  current_plan_id uuid,
  created_by uuid NOT NULL REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id,id)
);
CREATE TABLE exam_plans (
  tenant_id uuid NOT NULL,
  id uuid NOT NULL,
  exam_id uuid NOT NULL,
  spec_revision integer NOT NULL CHECK (spec_revision > 0),
  revision integer NOT NULL CHECK (revision > 0),
  plan_hash char(64) NOT NULL CHECK (plan_hash ~ '^[0-9a-f]{64}$'),
  slots_json jsonb NOT NULL CHECK (jsonb_typeof(slots_json)='array'),
  confirmed_by uuid REFERENCES users(id),
  confirmed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id,id),
  UNIQUE (tenant_id,exam_id,id),
  UNIQUE (tenant_id,exam_id,revision),
  FOREIGN KEY (tenant_id,exam_id) REFERENCES exams(tenant_id,id),
  CHECK ((confirmed_by IS NULL) = (confirmed_at IS NULL))
);
ALTER TABLE exams ADD CONSTRAINT current_plan_same_exam_fk
  FOREIGN KEY (tenant_id,id,current_plan_id) REFERENCES exam_plans(tenant_id,exam_id,id)
  DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE question_revisions (
  tenant_id uuid NOT NULL,
  id uuid NOT NULL,
  exam_id uuid NOT NULL,
  slot_id text NOT NULL,
  revision integer NOT NULL CHECK (revision > 0),
  public_json jsonb NOT NULL CHECK (jsonb_typeof(public_json)='object'),
  content_hash char(64) NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  blind_input_hash char(64) NOT NULL CHECK (blind_input_hash ~ '^[0-9a-f]{64}$'),
  origin text NOT NULL CHECK (origin IN ('ai_generated','human_edited')),
  provenance_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by uuid REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id,id),
  UNIQUE (tenant_id,exam_id,slot_id,revision),
  UNIQUE (tenant_id,exam_id,slot_id,id),
  FOREIGN KEY (tenant_id,exam_id) REFERENCES exams(tenant_id,id)
);
CREATE TABLE current_questions (
  tenant_id uuid NOT NULL,
  exam_id uuid NOT NULL,
  slot_id text NOT NULL,
  question_revision_id uuid NOT NULL,
  PRIMARY KEY (tenant_id,exam_id,slot_id),
  FOREIGN KEY (tenant_id,exam_id) REFERENCES exams(tenant_id,id),
  FOREIGN KEY (tenant_id,exam_id,slot_id,question_revision_id) REFERENCES question_revisions(tenant_id,exam_id,slot_id,id)
);
CREATE TABLE answer_revisions (
  tenant_id uuid NOT NULL,
  question_revision_id uuid NOT NULL,
  private_json jsonb NOT NULL CHECK (jsonb_typeof(private_json)='object'),
  PRIMARY KEY (tenant_id,question_revision_id),
  FOREIGN KEY (tenant_id,question_revision_id) REFERENCES question_revisions(tenant_id,id)
);
CREATE TABLE assets (
  tenant_id uuid NOT NULL,
  id uuid NOT NULL,
  exam_id uuid NOT NULL,
  kind text NOT NULL,
  media_type text NOT NULL,
  sha256 char(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  storage_key text NOT NULL,
  byte_size bigint NOT NULL CHECK (byte_size >= 0),
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id,id),
  FOREIGN KEY (tenant_id,exam_id) REFERENCES exams(tenant_id,id)
);
CREATE TABLE jobs (
  tenant_id uuid NOT NULL,
  id uuid NOT NULL,
  exam_id uuid NOT NULL,
  parent_job_id uuid,
  kind text NOT NULL CHECK (kind IN ('plan','generate','regenerate','validate','export')),
  status text NOT NULL CHECK (status IN ('QUEUED','RUNNING','RECONCILING','CANCEL_REQUESTED','CANCELLED','SUCCEEDED','PARTIAL_FAILED','FAILED','TIMED_OUT','BUDGET_EXCEEDED')),
  input_revision integer NOT NULL CHECK (input_revision > 0),
  input_hash char(64) NOT NULL CHECK (input_hash ~ '^[0-9a-f]{64}$'),
  policy_snapshot jsonb NOT NULL,
  skill_bundle_hash char(64) NOT NULL,
  budget_microunits bigint NOT NULL CHECK (budget_microunits > 0),
  reserved_microunits bigint NOT NULL DEFAULT 0 CHECK (reserved_microunits >= 0),
  settled_microunits bigint NOT NULL DEFAULT 0 CHECK (settled_microunits >= 0),
  currency text NOT NULL,
  cancel_requested_at timestamptz,
  deadline_at timestamptz NOT NULL,
  last_event_sequence bigint NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id,id),
  FOREIGN KEY (tenant_id,exam_id) REFERENCES exams(tenant_id,id),
  FOREIGN KEY (tenant_id,parent_job_id) REFERENCES jobs(tenant_id,id),
  UNIQUE (tenant_id,exam_id,id)
);
CREATE TABLE job_steps (
  tenant_id uuid NOT NULL,
  id uuid NOT NULL,
  job_id uuid NOT NULL,
  stage text NOT NULL,
  slot_id text NOT NULL DEFAULT '',
  attempt integer NOT NULL CHECK (attempt >= 1),
  input_hash char(64) NOT NULL,
  status text NOT NULL,
  lease_token bigint NOT NULL DEFAULT 0,
  lease_expires_at timestamptz,
  output_reference jsonb,
  error_code text,
  PRIMARY KEY (tenant_id,id),
  UNIQUE (tenant_id,job_id,stage,slot_id,attempt),
  UNIQUE (tenant_id,job_id,id),
  FOREIGN KEY (tenant_id,job_id) REFERENCES jobs(tenant_id,id)
);
CREATE TABLE job_events (
  tenant_id uuid NOT NULL,
  job_id uuid NOT NULL,
  sequence bigint NOT NULL CHECK (sequence > 0),
  event_type text NOT NULL,
  exam_revision integer NOT NULL,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id,job_id,sequence),
  FOREIGN KEY (tenant_id,job_id) REFERENCES jobs(tenant_id,id)
);
CREATE TABLE outbox (
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  id uuid NOT NULL,
  topic text NOT NULL,
  payload jsonb NOT NULL,
  published_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id,id)
);
CREATE TABLE idempotency_records (
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  actor_id uuid NOT NULL REFERENCES users(id),
  route text NOT NULL,
  idempotency_key text NOT NULL,
  request_hash char(64) NOT NULL,
  response_status integer,
  response_body jsonb,
  expires_at timestamptz NOT NULL,
  PRIMARY KEY (tenant_id,actor_id,route,idempotency_key)
);
CREATE TABLE validation_reports (
  tenant_id uuid NOT NULL,
  id uuid NOT NULL,
  exam_id uuid NOT NULL,
  target_type text NOT NULL CHECK (target_type IN ('question','exam','render')),
  target_id text NOT NULL,
  content_hash char(64) NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  check_code text NOT NULL,
  checker_id text NOT NULL,
  checker_version text NOT NULL,
  evidence_type text NOT NULL CHECK (evidence_type IN ('deterministic','model','human')),
  status text NOT NULL CHECK (status IN ('PASS','FAIL','REVIEW')),
  manual_allowed boolean NOT NULL DEFAULT false,
  evidence_json jsonb NOT NULL,
  signed_envelope_ref text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id,id),
  FOREIGN KEY (tenant_id,exam_id) REFERENCES exams(tenant_id,id)
);
CREATE TABLE review_decisions (
  tenant_id uuid NOT NULL,
  id uuid NOT NULL,
  exam_id uuid NOT NULL,
  actor_id uuid NOT NULL REFERENCES users(id),
  action text NOT NULL CHECK (action IN ('resolve_review','approve_content','approve_render','reject','revoke_decision')),
  target_hash char(64) NOT NULL,
  rationale text NOT NULL,
  linked_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id,id),
  FOREIGN KEY (tenant_id,exam_id) REFERENCES exams(tenant_id,id)
);
CREATE TABLE exports (
  tenant_id uuid NOT NULL,
  id uuid NOT NULL,
  exam_id uuid NOT NULL,
  job_id uuid NOT NULL,
  source_hash char(64) NOT NULL,
  render_hash char(64),
  format text NOT NULL CHECK (format IN ('pdf','docx','html','json')),
  view_kind text NOT NULL CHECK (view_kind IN ('student','teacher')),
  status text NOT NULL CHECK (status IN ('QUEUED','RENDERING','PREFLIGHT_FAILED','REVIEW_READY','PUBLISHED','FAILED')),
  storage_key text,
  renderer_version text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id,id),
  FOREIGN KEY (tenant_id,exam_id) REFERENCES exams(tenant_id,id),
  FOREIGN KEY (tenant_id,exam_id,job_id) REFERENCES jobs(tenant_id,exam_id,id)
);
CREATE TABLE exam_snapshots (
  tenant_id uuid NOT NULL,
  id uuid NOT NULL,
  exam_id uuid NOT NULL,
  revision integer NOT NULL,
  content_hash char(64) NOT NULL,
  public_snapshot jsonb NOT NULL,
  private_snapshot_storage_key text NOT NULL,
  manifest_json jsonb NOT NULL,
  published_by uuid NOT NULL REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id,id),
  UNIQUE (tenant_id,exam_id,revision),
  FOREIGN KEY (tenant_id,exam_id) REFERENCES exams(tenant_id,id)
);
CREATE TABLE usage_ledger (
  tenant_id uuid NOT NULL,
  id uuid NOT NULL,
  job_id uuid NOT NULL,
  step_id uuid,
  provider text NOT NULL,
  model_id text NOT NULL,
  provider_request_id text,
  input_tokens bigint CHECK (input_tokens >= 0),
  output_tokens bigint CHECK (output_tokens >= 0),
  cost_microunits bigint CHECK (cost_microunits >= 0),
  currency text NOT NULL,
  usage_unknown boolean NOT NULL DEFAULT false,
  pricing_version text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id,id),
  FOREIGN KEY (tenant_id,job_id) REFERENCES jobs(tenant_id,id),
  FOREIGN KEY (tenant_id,job_id,step_id) REFERENCES job_steps(tenant_id,job_id,id)
);
CREATE TABLE audit_logs (
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  id uuid NOT NULL,
  actor_ref text NOT NULL,
  action text NOT NULL,
  object_ref text NOT NULL,
  metadata_json jsonb NOT NULL,
  trace_id text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id,id)
);
CREATE INDEX jobs_status_created_idx ON jobs(tenant_id,status,created_at);
CREATE INDEX outbox_pending_idx ON outbox(created_at) WHERE published_at IS NULL;
CREATE INDEX reports_target_idx ON validation_reports(tenant_id,exam_id,target_id,content_hash,check_code);
CREATE INDEX exams_owner_idx ON exams(tenant_id,created_by,updated_at DESC);
CREATE INDEX usage_job_idx ON usage_ledger(tenant_id,job_id);

-- Fail closed if tenant context is unset. Set context only from authenticated
-- server-side identity, per transaction, and never from a model/browser tenant_id.
CREATE FUNCTION active_tenant() RETURNS uuid LANGUAGE sql STABLE AS $$
  SELECT NULLIF(current_setting('app.tenant_id',true),'')::uuid
$$;
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['memberships','exams','exam_plans','question_revisions',
    'current_questions','answer_revisions','assets','jobs','job_steps','job_events',
    'outbox','idempotency_records','validation_reports','review_decisions','exports',
    'exam_snapshots','usage_ledger','audit_logs']
  LOOP
    EXECUTE format('ALTER TABLE zhijuan.%I ENABLE ROW LEVEL SECURITY',t);
    EXECUTE format('ALTER TABLE zhijuan.%I FORCE ROW LEVEL SECURITY',t);
    EXECUTE format('CREATE POLICY tenant_scope ON zhijuan.%I USING (tenant_id = zhijuan.active_tenant()) WITH CHECK (tenant_id = zhijuan.active_tenant())',t);
  END LOOP;
END $$;
CREATE FUNCTION reject_record_update() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'immutable record: create a new revision or append a revocation event';
END $$;
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['question_revisions','answer_revisions','validation_reports',
    'review_decisions','exam_snapshots','job_events','audit_logs']
  LOOP
    EXECUTE format('CREATE TRIGGER immutable_update BEFORE UPDATE ON zhijuan.%I FOR EACH ROW EXECUTE FUNCTION zhijuan.reject_record_update()',t);
  END LOOP;
END $$;
-- Next migration must create runtime roles and explicit least-privilege GRANTs.
-- Agent/solver identities must have NO SQL access. RLS alone is not answer RBAC.
COMMIT;
