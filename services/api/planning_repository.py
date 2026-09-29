"""Planning jobs share the durable outbox, under a separate draft namespace."""
import copy
import json
from .repositories import PostgresJobRepository
from .store_state import ExamStoreState

ACTIVE = {'QUEUED', 'RUNNING', 'PAUSED', 'RECONCILING'}


class PlanningRepository(PostgresJobRepository):
    def admit(self, job):
        with self.psycopg.connect(self.dsn) as conn, conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('current', 0))")
            draft = conn.execute("SELECT state FROM generation_exam_state WHERE exam_id='current' FOR UPDATE").fetchone()
            if not draft or draft[0]['spec_revision'] != job['spec_revision'] or draft[0]['spec'] != job['spec_snapshot']:
                raise ValueError('配置已变化，请重新加载')
            current = draft[0].get('blueprint', {})
            if current.get('plan_hash') != job['base_plan_hash']:
                raise ValueError('蓝图已变化，请重新加载')
            active = conn.execute("SELECT 1 FROM generation_jobs WHERE exam_id='current' AND snapshot->>'status' = ANY(%s)", (list(ACTIVE),)).fetchone()
            if active:
                raise ValueError('命题任务尚未结束，不能重新规划')
            row = conn.execute('SELECT snapshot FROM generation_jobs WHERE exam_id=%s FOR UPDATE', (job['exam_id'],)).fetchone()
            if row:
                previous = row[0]
                if previous['status'] in ACTIVE or previous.get('request_key') == job['request_key']:
                    return copy.deepcopy(previous)
                conn.execute('INSERT INTO generation_job_history(job_id,exam_id,snapshot) VALUES (%s,%s,%s::jsonb) ON CONFLICT DO NOTHING',
                             (previous['job_id'], job['exam_id'], json.dumps(previous)))
            conn.execute('INSERT INTO generation_jobs(exam_id,snapshot) VALUES (%s,%s::jsonb) ON CONFLICT(exam_id) DO UPDATE SET snapshot=EXCLUDED.snapshot',
                         (job['exam_id'], json.dumps(job)))
            conn.execute('INSERT INTO generation_job_outbox(job_id,event_type) VALUES (%s,%s) ON CONFLICT DO NOTHING', (job['job_id'], 'dispatch:1'))
            return copy.deepcopy(job)

    def commit_plan(self, job, plan):
        with self.psycopg.connect(self.dsn) as conn, conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('current', 0))")
            row = conn.execute("SELECT version,state FROM generation_exam_state WHERE exam_id='current' FOR UPDATE").fetchone()
            live = conn.execute('SELECT snapshot FROM generation_jobs WHERE exam_id=%s FOR UPDATE', (job['exam_id'],)).fetchone()
            if not row or not live or live[0]['job_id'] != job['job_id'] or live[0]['version'] != job['version'] or live[0]['status'] != 'RUNNING':
                raise ValueError('规划任务已变化，结果未应用')
            state = row[1]
            if state['spec_revision'] != job['spec_revision'] or state['spec'] != job['spec_snapshot'] or state.get('blueprint', {}).get('plan_hash') != job['base_plan_hash']:
                raise ValueError('规划期间配置或蓝图已变化，结果未应用')
            active = conn.execute("SELECT 1 FROM generation_jobs WHERE exam_id='current' AND snapshot->>'status'=ANY(%s)", (list(ACTIVE),)).fetchone()
            if active:
                raise ValueError('已有命题任务，规划结果未应用')
            if plan['plan_hash'] != ExamStoreState._plan_hash(plan):
                raise ValueError('规划结果哈希不一致')
            state.update(blueprint=plan, slots=plan['slots'], validation={}, adjudications={})
            conn.execute("UPDATE generation_exam_state SET version=version+1,state=%s::jsonb WHERE exam_id='current'", (json.dumps(state),))
            job = {**job, 'status': 'COMPLETED', 'version': job['version'] + 1, 'result': plan}
            conn.execute('UPDATE generation_jobs SET snapshot=%s::jsonb WHERE exam_id=%s', (json.dumps(job), job['exam_id']))
            return job
