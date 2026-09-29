"""No-network reproductions for the final generation trust boundaries."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from reference_code.adapter_contract import RunResult
from services.api.main import app
from services.exam.question_service import QuestionService, GenerationFailure
from services.validators import validate_candidate
ROOT = Path(__file__).resolve().parents[1]

class CloseoutTests(unittest.TestCase):
    def fixture(self):
        candidate=json.loads((ROOT/'examples/candidate.json').read_text())
        spec=json.loads((ROOT/'examples/exam-spec.json').read_text())
        slot={'slot_id':'s1','kind':candidate['public']['kind'],'score_x100':candidate['public']['score_x100'],'spec_revision':1,'plan_revision':1,'question_revision_id':'qrev-1'}
        return candidate,spec,slot

    def test_blind_evidence_changes_evidence_hash_not_question_content(self):
        c,s,slot=self.fixture()
        one=validate_candidate(c,slot,s,{'match_reference':True,'is_same_model':True,'model_id':'test'})
        two=validate_candidate(c,slot,s,{'match_reference':False,'is_same_model':True,'model_id':'test'})
        self.assertEqual(one['content_hash'],two['content_hash'])
        self.assertIn('evidence_hash',one)
        self.assertNotEqual(one['evidence_hash'],two['evidence_hash'])

    def test_bad_author_slot_does_not_charge_solver(self):
        c,s,slot=self.fixture();slot['score_x100']+=100
        adapter=Mock()
        adapter.run_stage.side_effect=lambda req,*args: RunResult('SUCCEEDED',c if req.role=='author' else {
            'question_revision_id':req.input_payload['question_revision_id'],'action':'repair',
            'issues':['分值不符'],'summary':'修订分值'},(),{},None)
        with patch.object(QuestionService,'get_adapter',return_value=adapter):
            result=QuestionService.generate_slot_result(c['public']['local_id'],spec=s,slot=slot)
        self.assertEqual(result['validation']['overall_status'],'FAIL')
        self.assertEqual(adapter.run_stage.call_count,6)
        self.assertNotIn('solver',[call.args[0].role for call in adapter.run_stage.call_args_list])

    def test_cancel_before_start_never_constructs_runtime(self):
        c,s,slot=self.fixture()
        with patch.object(QuestionService,'get_adapter') as adapter:
            with self.assertRaises(GenerationFailure):
                QuestionService.generate_slot_result(c['public']['local_id'],spec=s,slot=slot,cancellation_requested=lambda:True)
            adapter.assert_not_called()

    def test_unsupported_publication_cannot_publish_old_store_candidates(self):
        with patch('services.api.routes.exams.store.publish_exam') as publish:
            response=TestClient(app).post('/v1/exams/current/publish',json={})
        self.assertEqual(response.status_code,501)
        publish.assert_not_called()

    def test_old_job_and_candidates_do_not_become_current_after_spec_change(self):
        from services.exam.job_service import GenerationJobService
        from services.api.store import ExamStore
        with patch.dict('os.environ',{'DATABASE_URL':''}):
            local=ExamStore()
            local.candidates=[{'public':{'local_id':'old'}}]
            previous=copy.deepcopy(local.candidates)
            local.update_spec(self.fixture()[1])
            self.assertEqual(local.get_candidates(),[])
            self.assertEqual(local.candidates,previous)  # Stale data is retained, not destroyed.
        repo=Mock();repo.get.return_value={'spec_revision':1,'job_id':'old','status':'COMPLETED'}
        with patch.object(GenerationJobService,'repository',return_value=repo),patch('services.exam.job_service.store.get_spec_revision',return_value=2):
            self.assertIsNone(GenerationJobService.get_current_job())

    def test_old_plan_job_and_results_are_not_current_with_same_spec(self):
        from services.exam.job_service import GenerationJobService
        repo=Mock()
        repo.get.return_value={'spec_revision':7,'revision':2,'job_id':'old-plan','status':'COMPLETED'}
        repo.results.return_value=[{'candidate':{'public':{'local_id':'q01'}},'validation':{'overall_status':'REVIEW'}}]
        current_plan={'revision':3,'spec_revision':7}
        with patch.dict('os.environ',{'DATABASE_URL':'mock-only'}), \
             patch.object(GenerationJobService,'repository',return_value=repo), \
             patch('services.exam.question_service.store.get_spec_revision',return_value=7), \
             patch('services.exam.question_service.store.get_blueprint',return_value=current_plan), \
             patch('services.exam.job_service.store.get_spec_revision',return_value=7), \
             patch('services.exam.job_service.store.get_blueprint',return_value=current_plan):
            self.assertEqual(QuestionService.list_candidates(),[])
            self.assertEqual(QuestionService.get_validation(),{})
            self.assertIsNone(GenerationJobService.get_current_job())

    def test_replanned_draft_hides_old_candidates_and_checks(self):
        from services.api.store import ExamStore
        with patch.dict('os.environ',{'DATABASE_URL':''}):
            local=ExamStore()
            local.candidates=[{'public':{'local_id':'old'}}]
            local.validation={'old':{'overall_status':'REVIEW'}}
            local.adjudications={'old':{'status':'approved'}}
            plan={'spec_revision':local.spec_revision,'canonical_spec':copy.deepcopy(local.spec),
                  'plan_hash':'fixture','revision':local.blueprint.get('revision',1)+1,'slots':[]}
            with patch.object(local,'_plan_hash',return_value='fixture'):
                local.save_blueprint(plan)
            self.assertEqual(local.get_candidates(),[])
            self.assertEqual(local.get_validation(),{})
            self.assertEqual(local.get_adjudications(),{})
