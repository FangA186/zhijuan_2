"""Only run against the disposable planner_test database; never the local draft DB."""
import copy
import json
import os
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, Mock

from services.api.planning_repository import PlanningRepository
from services.api.store import store
from services.blueprint.planner import bind_design
from services.worker.planning import run_planning
from reference_code.adapter_contract import RunResult
from tests.test_planner_agent import fixture


@unittest.skipUnless(os.getenv('ZHIJUAN_PLANNER_TEST_DSN'), 'disposable PostgreSQL required')
class PlannerPostgresTests(unittest.TestCase):
    def setUp(self):
        self.repo=PlanningRepository(os.environ['ZHIJUAN_PLANNER_TEST_DSN'])
        self.spec,self.skeleton,self.design=fixture()
        with self.repo.psycopg.connect(self.repo.dsn) as conn:
            self.assertEqual(conn.execute('SELECT current_database()').fetchone()[0],'planner_test')
            for p in ['database/003_generation_jobs.sql','database/004_generation_exam_state.sql']:conn.execute(Path(p).read_text())
            for table in ['generation_job_outbox','generation_jobs','generation_exam_state','generation_exam_revisions','generation_job_history']:conn.execute(f'DELETE FROM {table}')
            state={'spec':self.spec,'spec_revision':2,'blueprint':{'plan_hash':'old'},'slots':[],'validation':{},'adjudications':{}}
            conn.execute("INSERT INTO generation_exam_state VALUES ('current',1,%s::jsonb)",(json.dumps(state),))
            conn.execute("INSERT INTO generation_jobs VALUES ('current',%s::jsonb)",(json.dumps({'status':'COMPLETED','job_id':'old-paper','version':1}),))
        self.job={'job_id':'planner1','exam_id':'planning:current','job_kind':'planning','status':'QUEUED',
                  'version':1,'spec_revision':2,'spec_snapshot':self.spec,'skeleton':self.skeleton,
                  'base_plan_hash':'old','request_key':'request1','updated_at':'2026-09-28T00:00:00+00:00','activity':[]}

    def test_atomic_admission_outbox_replay_and_real_worker_commit(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            results=list(executor.map(lambda _: self.repo.admit(copy.deepcopy(self.job)),range(2)))
        self.assertEqual(results[0]['job_id'],results[1]['job_id'])
        self.assertEqual(len(self.repo.pending_dispatches()),1)
        adapter=Mock()
        def call(req,emit,cancelled):
            emit({'event':'hermes_run_admitted','run_id':'run_fixture'})
            return RunResult('SUCCEEDED',self.design,(),{'total_tokens':80},None)
        adapter.run_stage.side_effect=call
        with patch.dict(os.environ,{'DATABASE_URL':self.repo.dsn}):
            run_planning('planner1',self.repo,adapter)
            run_planning('planner1',self.repo,adapter)
            plan=store.get_blueprint()
        self.assertEqual(plan['planning_source'],'hermes_planner');self.assertFalse(plan['confirmed'])
        self.assertEqual(self.repo.get('current')['job_id'],'old-paper')
        self.assertEqual(self.repo.get('planning:current')['status'],'COMPLETED')
        self.assertEqual(adapter.run_stage.call_count,1)
        with self.assertRaisesRegex(ValueError,'蓝图已变化'):self.repo.admit({**self.job,'request_key':'request2'})

    def test_late_result_is_fenced_by_revision_or_active_author_job(self):
        self.repo.admit(self.job)
        running=self.repo.replace({**self.job,'status':'RUNNING'},1)
        plan=bind_design(self.skeleton,self.design,{})
        with self.repo.psycopg.connect(self.repo.dsn) as conn:
            conn.execute("UPDATE generation_exam_state SET state=jsonb_set(state,'{spec_revision}','3'::jsonb) WHERE exam_id='current'")
        with self.assertRaisesRegex(ValueError,'配置或蓝图'):self.repo.commit_plan(running,plan)
        with self.repo.psycopg.connect(self.repo.dsn) as conn:
            conn.execute("UPDATE generation_exam_state SET state=jsonb_set(state,'{spec_revision}','2'::jsonb) WHERE exam_id='current'")
            conn.execute("UPDATE generation_jobs SET snapshot=jsonb_set(snapshot,'{status}','\"RUNNING\"'::jsonb) WHERE exam_id='current'")
        with self.assertRaisesRegex(ValueError,'命题任务'):self.repo.commit_plan(running,plan)
        self.assertEqual(self.repo.get('planning:current')['status'],'RUNNING')

    def test_stale_unknown_job_is_quarantined_without_new_dispatch(self):
        self.repo.admit(self.job)
        self.repo.replace({**self.job,'status':'RUNNING'},1)
        with self.repo.psycopg.connect(self.repo.dsn) as conn:
            conn.execute("UPDATE generation_jobs SET snapshot=jsonb_set(snapshot,'{updated_at}','\"2020-01-01T00:00:00+00:00\"'::jsonb) WHERE exam_id='planning:current'")
        self.assertEqual(self.repo.reconcile_stale(),1)
        same=self.repo.admit({**self.job,'request_key':'new-request'})
        self.assertEqual(same['status'],'RECONCILING')
        self.assertEqual(len(self.repo.pending_dispatches()),1)
