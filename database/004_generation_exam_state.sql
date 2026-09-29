-- Local single-exam integration storage; does not implement tenant/role migrations from M1-02.
CREATE TABLE IF NOT EXISTS generation_exam_state (
    exam_id text PRIMARY KEY,
    version integer NOT NULL,
    state jsonb NOT NULL
);
