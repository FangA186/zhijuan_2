"""Offline planner binding and queue lifecycle; no external model calls."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from reference_code.adapter_contract import RunResult
from services.blueprint.generator import BlueprintGenerator
from services.blueprint.planner import bind_design, planning_input
from services.exam.planning_service import PlanningService
from services.worker.planning import run_planning
from tools.deepseek_json_contract import prepare_strict_request


def fixture():
    spec = json.loads(Path('acceptance/fixtures/minimum-primary.json').read_text())
    spec['taught_scope']['scope_confirmed'] = True
    skeleton = BlueprintGenerator.generate(spec, spec_revision=2, revision=3)
    design = {'summary': '离线合成规划，用于验证结构与流程，不代表真实模型输出。', 'conflicts': [], 'slots': []}
    for slot in skeleton['slots']:
        design['slots'].append({'slot_id': slot['slot_id'], 'knowledge_ids': slot['knowledge_ids'],
            'cognitive_target': '运算与解释', 'difficulty': slot['estimated_difficulty'],
            'design_brief': f"第{slot['order']}题使用不同给定条件，解释计算与概念之间的关系。", 'rationale': '匹配本题题型与分值要求'})
    return spec, skeleton, design


class MemoryRepo:
    def __init__(self, job): self.job, self.commits = copy.deepcopy(job), 0
    def get_by_job_id(self, id): return self.get('planning:current') if id == self.job['job_id'] else None
    def get(self, key): return copy.deepcopy(self.job)
    def replace(self, job, expected):
        if self.job['version'] != expected: raise RuntimeError('stale')
        self.job = copy.deepcopy({**job, 'version': expected + 1})
        return self.get('planning:current')
    def commit_plan(self, job, plan):
        self.commits += 1
        return self.replace({**job, 'status': 'COMPLETED', 'result': plan}, job['version'])


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.spec, self.skeleton, self.design = fixture()

    def test_planner_owns_semantics_program_owns_structure_and_hash(self):
        self.design['slots'][0]['design_brief'] = '先理解给定图表中的关系，再解释一次运算的依据。'
        plan = bind_design(self.skeleton, self.design, {'run_id': 'run_test'})
        self.assertFalse(plan['confirmed'])
        self.assertEqual(plan['planning_source'], 'hermes_planner')
        self.assertNotEqual(plan['plan_hash'], self.skeleton['plan_hash'])
        self.assertEqual([(s['kind'],s['score_x100']) for s in plan['slots']], [(s['kind'],s['score_x100']) for s in self.skeleton['slots']])
        self.assertEqual(plan['slots'][0]['design_brief'], self.design['slots'][0]['design_brief'])
        self.assertNotIn('target_topic', planning_input(self.spec,self.skeleton)['slots'][0])
        from services.exam.generation_context import author_input
        payload = author_input(self.spec, plan['slots'][0], 'q01')
        self.assertEqual(payload['slot']['design_brief'], self.design['slots'][0]['design_brief'])

    def test_invalid_or_conflicting_design_never_falls_back(self):
        for mutate in [lambda d:d['slots'].pop(), lambda d:d['slots'].append(d['slots'][0]),
                       lambda d:d['slots'][0].update(knowledge_ids=['越界考点']),
                       lambda d:d['slots'][0].update(score_x100=1),
                       lambda d:d['slots'][0].update(difficulty='unknown'),
                       lambda d:d.update(conflicts=['配置无法满足']),
                       lambda d:d['slots'][1].update(design_brief=d['slots'][0]['design_brief'])]:
            design=copy.deepcopy(self.design);mutate(design)
            with self.assertRaises(ValueError): bind_design(self.skeleton,design,{})
        design=copy.deepcopy(self.design)
        design['slots'][0]['difficulty']='advanced' if design['slots'][0]['difficulty']=='basic' else 'basic'
        with self.assertRaisesRegex(ValueError,'难度'):bind_design(self.skeleton,design,{})

    def test_strict_proxy_routes_planner_to_planner_schema(self):
        body=prepare_strict_request({'messages':[{'role':'user','content':'Role: planner. Return blueprint-design.'}]})
        props=body['tools'][0]['function']['parameters']['properties']
        self.assertEqual(set(props), {'summary','conflicts','slots'})
        self.assertIn('design_brief',props['slots']['items']['properties'])

    def job(self):
        return {'job_id':'j1','exam_id':'planning:current','status':'QUEUED','version':1,
                'spec_revision':2,'spec_snapshot':self.spec,'skeleton':self.skeleton,'base_plan_hash':'old',
                'request_key':'request1','activity':[]}

    def test_worker_calls_real_adapter_contract_once_and_redelivery_does_not_call(self):
        repo=MemoryRepo(self.job());adapter=Mock()
        def run(req,emit,cancelled):
            self.assertEqual(req.role,'planner');self.assertEqual(req.max_iterations,1)
            self.assertFalse(cancelled());emit({'event':'hermes_run_admitted','run_id':'run_plan'})
            emit({'event':'activity','data':{'event':'message.delta','delta':'真实来源字段的离线合成片段'}})
            return RunResult('SUCCEEDED',self.design,(),{'total_tokens':30},None)
        adapter.run_stage.side_effect=run
        with patch('services.worker.planning.store.get_spec_revision',return_value=2):
            run_planning('j1',repo,adapter);run_planning('j1',repo,adapter)
        self.assertEqual(adapter.run_stage.call_count,1)
        self.assertEqual(repo.job['status'],'COMPLETED');self.assertEqual(repo.commits,1)
        self.assertEqual(repo.job['run_id'],'run_plan');self.assertEqual(repo.job['usage']['total_tokens'],30)
        self.assertTrue(any('合成片段' in a['message'] for a in repo.job['activity']))

    def test_unknown_and_invalid_outputs_never_commit_or_retry(self):
        for result,status in [(RunResult('UNKNOWN',None,(),{},'HERMES_ADMISSION_UNKNOWN'),'RECONCILING'),
                              (RunResult('SUCCEEDED',{},(),{},None),'FAILED')]:
            repo=MemoryRepo(self.job());adapter=Mock();adapter.run_stage.return_value=result
            with patch('services.worker.planning.store.get_spec_revision',return_value=2):
                run_planning('j1',repo,adapter);run_planning('j1',repo,adapter)
            self.assertEqual(repo.commits,0);self.assertEqual(repo.job['status'],status)
            self.assertEqual(adapter.run_stage.call_count,1)

    def test_revision_change_before_call_stops_without_billing(self):
        repo=MemoryRepo(self.job());adapter=Mock()
        with patch('services.worker.planning.store.get_spec_revision',return_value=3):run_planning('j1',repo,adapter)
        adapter.run_stage.assert_not_called();self.assertEqual(repo.commits,0)

    def test_admission_idempotence_and_public_projection(self):
        old={**self.job(),'status':'RECONCILING'};repo=Mock();repo.get.return_value=old
        with patch('services.exam.planning_service.GenerationJobService.runtime_readiness') as ready:
            self.assertEqual(PlanningService.start('another-key',2,repo),old)
            ready.assert_not_called();repo.admit.assert_not_called()
        visible=PlanningService.public(old)
        self.assertNotIn('spec_snapshot',visible);self.assertNotIn('skeleton',visible)

class PlannerRoutesTests(unittest.TestCase):
    def test_local_only_and_admission_has_no_model_work(self):
        from fastapi.testclient import TestClient
        from services.api.main import app
        with patch('services.api.routes.planning_routes.require_revision',return_value=2), \
             patch.object(PlanningService,'start',return_value={'job_id':'j','status':'QUEUED','version':1}) as start, \
             patch('services.exam.question_service.QuestionService.get_adapter') as adapter:
            client=TestClient(app)
            self.assertEqual(client.post('/v1/exams/current/planning-jobs').status_code,422)
            response=client.post('/v1/exams/current/planning-jobs',headers={'Idempotency-Key':'request1'})
            self.assertEqual(response.status_code,202);start.assert_called_once();adapter.assert_not_called()
            remote=TestClient(app,client=('203.0.113.1',50000))
            self.assertEqual(remote.get('/v1/exams/current/planning-jobs/current').status_code,403)

    def test_stale_read_retains_diagnostic_without_reusable_plan(self):
        from services.api.routes.planning_routes import current_planning
        with patch.object(PlanningService,'current',return_value={'job_id':'j','spec_revision':2,'status':'RECONCILING','result':{'slots':[]}}), \
             patch('services.api.routes.planning_routes.store.get_spec_revision',return_value=3):
            result=current_planning()
        self.assertTrue(result['stale']);self.assertNotIn('result',result)
        self.assertEqual(result['status'],'RECONCILING')

    def test_dispatch_routes_planning_and_not_authoring(self):
        from services.worker.jobs import run_job
        repo=Mock();repo.get_by_job_id.return_value={'job_id':'j','status':'QUEUED','job_kind':'planning'}
        generate=Mock()
        with patch('services.worker.planning.run_planning') as planner:
            run_job('j',repository=repo,generate=generate)
        planner.assert_called_once_with('j');generate.assert_not_called()

    def test_confirmed_external_cancellation_finishes_stop_request(self):
        spec,skeleton,_=fixture()
        repo=MemoryRepo({'job_id':'j','exam_id':'planning:current','status':'QUEUED','version':1,
                         'spec_revision':2,'spec_snapshot':spec,'skeleton':skeleton,'activity':[]})
        adapter=Mock()
        def stop(req,emit,cancelled):
            current=repo.get('planning:current');current.update(status='RECONCILING',stop_requested=True)
            repo.replace(current,current['version'])
            return RunResult('CANCELLED',None,(),{},None)
        adapter.run_stage.side_effect=stop
        with patch('services.worker.planning.store.get_spec_revision',return_value=2):run_planning('j',repo,adapter)
        self.assertEqual(repo.job['status'],'CANCELLED');self.assertEqual(repo.commits,0)
