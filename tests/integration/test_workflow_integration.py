"""Independent Astra checks: temporary/dedicated PG only; no model calls."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from services.api.main import app
from services.api.store import store, ExamStore
from services.exam.question_service import QuestionService, GenerationFailure
from services.worker.jobs import run_job

ROOT=Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.getenv('ZHIJUAN_TEST_DATABASE_URL'), 'Dedicated integration database required')
class WorkflowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get('DATABASE_URL') != os.environ['ZHIJUAN_TEST_DATABASE_URL']:
            raise RuntimeError('Tests must use the dedicated database')
        cls.client=TestClient(app)
        cls.job_ids=[]
        # These API/database tests substitute worker/model configuration; no model runs.
        configured = patch('services.api.routes.exams.generation_configuration', return_value={'configured': True})
        configured.start()
        cls.addClassCleanup(configured.stop)
        # This suite checks job lifecycle semantics; real dependency readiness
        # has its own suites and is stubbed green here.
        ready = patch('services.api.health.runtime_readiness', return_value={
            'configured': True, 'ready': True, 'runtime_verified': True,
            'checked_at': '1970-01-01T00:00:00+00:00', 'reason_codes': [],
            'components': {name: {'ok': True} for name in (
                'database', 'broker', 'worker', 'dispatcher', 'author', 'solver', 'budget')},
        })
        ready.start()
        cls.addClassCleanup(ready.stop)

    def spec(self,stage='primary',year=4):
        spec=json.loads((ROOT/'examples/exam-spec-primary.json').read_text())
        spec.update(title='Workflow acceptance temporary draft',stage=stage,stage_year=year)
        spec['sections']=[dict(spec['sections'][0],count=1,score_each_x100=100)]
        spec['total_score_x100']=100
        spec['difficulty_distribution']={'basic':100,'medium':0,'advanced':0}
        return spec

    def get_tag(self):return self.client.get('/v1/exams/current/spec').headers['etag']

    def save(self,spec):
        response=self.client.put('/v1/exams/current/spec',json=spec,headers={'If-Match':self.get_tag()})
        self.assertEqual(response.status_code,200,response.text)
        return response.headers['etag']

    def test_invalid_input_etag_and_cross_exam_boundaries(self):
        payload=self.spec()
        self.assertEqual(self.client.put('/v1/exams/current/spec',json=payload).status_code,428)
        self.assertEqual(self.client.put('/v1/exams/current/spec',json=payload,headers={'If-Match':'"-1"'}).status_code,412)
        payload['total_score_x100']=101
        with patch.object(QuestionService,'get_adapter') as adapter:
            response=self.client.put('/v1/exams/current/spec',json=payload,headers={'If-Match':self.get_tag()})
            self.assertEqual(response.status_code,422)
            adapter.assert_not_called()
        self.assertEqual(self.client.get('/v1/exams/someone-else/spec').status_code,404)

    def test_three_stages_exact_blueprint_confirmation_and_restart(self):
        for stage,year in [('primary',4),('junior',2),('senior',2)]:
            with self.subTest(stage=stage):
                spec=self.spec(stage,year);tag=self.save(spec)
                response=self.client.post('/v1/exams/current/plans/generate',json=spec,headers={'If-Match':tag})
                self.assertEqual(response.status_code,200,response.text)
                plan=response.json()
                self.assertFalse(plan['confirmed']);self.assertEqual(sum(s['score_x100'] for s in plan['slots']),100)
                self.assertNotEqual(self.client.post('/v1/exams/current/generation-jobs',headers={'If-Match':tag}).status_code,202)
                self.assertEqual(self.client.post('/v1/exams/current/plans/wrong/confirm',headers={'If-Match':tag}).status_code,409)
                response=self.client.post(f"/v1/exams/current/plans/{plan['plan_id']}/confirm",headers={'If-Match':tag})
                self.assertEqual(response.status_code,200,response.text)
                restored=ExamStore()
                self.assertEqual(restored.get_spec()['stage'],stage)
                self.assertTrue(restored.get_blueprint()['confirmed'])
        old_plan=store.get_blueprint()['plan_id']
        changed=self.spec('senior',2);changed['title']+=' revised'
        new_tag=self.save(changed)
        self.assertFalse(store.get_blueprint()['confirmed'])
        self.assertEqual(self.client.post(f'/v1/exams/current/plans/{old_plan}/confirm',headers={'If-Match':new_tag}).status_code,409)

    def test_job_is_explicit_idempotent_and_cancelled_before_worker(self):
        spec=self.spec();tag=self.save(spec)
        plan=self.client.post('/v1/exams/current/plans/generate',json=spec,headers={'If-Match':tag}).json()
        self.client.post(f"/v1/exams/current/plans/{plan['plan_id']}/confirm",headers={'If-Match':tag})
        with patch.object(QuestionService,'get_adapter') as adapter:
            response=self.client.post('/v1/exams/current/generation-jobs',headers={'If-Match':tag})
            self.assertEqual(response.status_code,202,response.text)
            job=response.json();self.job_ids.append(job['job_id'])
            self.assertEqual(job['status'],'QUEUED');self.assertIsNone(job['tokens_used'])
            again=self.client.post('/v1/exams/current/generation-jobs',headers={'If-Match':tag})
            self.assertEqual(again.json()['job_id'],job['job_id'])
            for _ in range(2):
                current=self.client.get('/v1/exams/current/generation-jobs/current').json()
                self.assertEqual(current['job_id'],job['job_id'])
                self.assertNotIn('spec_snapshot',current)
            cancelled=self.client.post('/v1/exams/current/generation-jobs/current/cancel')
            self.assertEqual(cancelled.status_code,200)
            generate=__import__('unittest.mock',fromlist=['Mock']).Mock()
            run_job(job['job_id'],generate=generate)
            generate.assert_not_called();adapter.assert_not_called()

    def test_active_job_blocks_same_spec_replan_and_old_plan_cannot_start(self):
        from services.api.repositories import PostgresJobRepository
        from services.exam.job_service import GenerationJobService
        from services.exam.blueprint_service import BlueprintService
        spec=self.spec();spec['title']='Plan fence dedicated database check'
        tag=self.save(spec)
        response=self.client.post('/v1/exams/current/plans/generate',json=spec,headers={'If-Match':tag})
        self.assertEqual(response.status_code,200,response.text)
        old_plan=response.json()
        response=self.client.post(f"/v1/exams/current/plans/{old_plan['plan_id']}/confirm",headers={'If-Match':tag})
        self.assertEqual(response.status_code,200,response.text)
        old_plan=response.json()
        response=self.client.post('/v1/exams/current/generation-jobs',headers={'If-Match':tag})
        self.assertEqual(response.status_code,202,response.text)
        job=response.json();self.job_ids.append(job['job_id'])
        repo=PostgresJobRepository()
        current=repo.get('current');current['status']='RUNNING'
        repo.replace(current,current['version'])
        try:
            response=self.client.post('/v1/exams/current/plans/generate',json=spec,headers={'If-Match':tag})
            self.assertEqual(response.status_code,422,response.text)
            self.assertEqual(store.get_blueprint()['plan_hash'],old_plan['plan_hash'])
            self.assertEqual(repo.get('current')['status'],'RUNNING')
        finally:
            self.client.post('/v1/exams/current/generation-jobs/current/cancel')
        response=self.client.post('/v1/exams/current/plans/generate',json=spec,headers={'If-Match':tag})
        self.assertEqual(response.status_code,200,response.text)
        new_plan=response.json()
        self.assertNotEqual(new_plan['plan_hash'],old_plan['plan_hash'])
        response=self.client.post(f"/v1/exams/current/plans/{new_plan['plan_id']}/confirm",headers={'If-Match':tag})
        self.assertEqual(response.status_code,200,response.text)
        with patch.object(BlueprintService,'get_blueprint',return_value=old_plan):
            with self.assertRaises(RuntimeError):
                GenerationJobService.start_job()

    @classmethod
    def tearDownClass(cls):
        import psycopg
        with psycopg.connect(os.environ['ZHIJUAN_TEST_DATABASE_URL']) as conn:
            for job_id in cls.job_ids:
                conn.execute('DELETE FROM generation_job_outbox WHERE job_id=%s',(job_id,))
                conn.execute('DELETE FROM generation_job_results WHERE job_id=%s',(job_id,))
                conn.execute("DELETE FROM generation_jobs WHERE snapshot->>'job_id'=%s",(job_id,))
