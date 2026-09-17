"""Offline plan/contract tests. These do NOT implement or run the MVP."""
from copy import deepcopy
from jsonschema import Draft202012Validator, ValidationError
import unittest
from tools.verify_execution_plan import ROOT, read_yaml, validate_execution, validate_task_graph, validate_case

class ExecutionPlanTests(unittest.TestCase):
    def setUp(self):
        self.tasks=read_yaml(ROOT/'execution/task-index.yaml')['tasks']
        self.ids={t['id'] for t in self.tasks}
        self.case=read_yaml(ROOT/'acceptance/minimum-cases.yaml')['cases'][0]
    def test_complete_plan_consistency(self):
        self.assertEqual(validate_execution()['task_cards'],32)
    def test_duplicate_task_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):validate_task_graph(self.tasks+[deepcopy(self.tasks[0])])
    def test_missing_dependency_rejected(self):
        self.tasks[1]['depends_on']=['M0-99']
        with self.assertRaisesRegex(ValueError,'Unknown dependency'):validate_task_graph(self.tasks)
    def test_dependency_cycle_rejected(self):
        self.tasks[0]['depends_on']=['M0-02']
        with self.assertRaisesRegex(ValueError,'Cycle'):validate_task_graph(self.tasks)
    def test_dependency_on_later_phase_rejected(self):
        self.tasks[0]['depends_on']=['M3-08']
        with self.assertRaisesRegex(ValueError,'later phase'):validate_task_graph(self.tasks)
    def test_case_single_summary_rejected(self):
        self.case['steps']=['一个概括性的步骤并不能替代执行手册']
        with self.assertRaisesRegex(ValueError,'Insufficient'):validate_case(self.case,self.ids)
    def test_case_without_cleanup_rejected(self):
        self.case['cleanup']=[]
        with self.assertRaisesRegex(ValueError,'cleanup'):validate_case(self.case,self.ids)
    def test_fake_runtime_pass_rejected(self):
        self.case['status']='PASS'
        with self.assertRaisesRegex(ValueError,'claims implementation'):validate_case(self.case,self.ids)
    def test_fake_runtime_evidence_rejected(self):
        self.case['evidence_refs']=['invented-run.json']
        with self.assertRaisesRegex(ValueError,'Invented runtime'):validate_case(self.case,self.ids)
    def test_unknown_task_mapping_rejected(self):
        self.case['implementation_tasks']=['M8-99']
        with self.assertRaisesRegex(ValueError,'mapping'):validate_case(self.case,self.ids)
    def test_added_read_operations_and_revoke_exist(self):
        api=read_yaml(ROOT/'contracts/openapi.yaml')
        for path,method in [('/v1/session','get'),('/v1/exams','get'),('/v1/exams/{exam_id}/spec','get'),('/v1/exams/{exam_id}/plans/current','get'),('/v1/exams/{exam_id}/publications/{snapshot_id}/revoke','post')]:
            self.assertIn(method,api['paths'][path])
        self.assertIn('ETag',api['paths']['/v1/exams/{exam_id}/plans/current']['get']['responses']['200']['headers'])
        slot={'slot_id':'group-a','kind':'material_group','parent_slot_id':None,'score_x100':0,'knowledge_ids':['k1'],'objective':'材料共享','constraints':[],'material_group_id':'mat-1'}
        validator=Draft202012Validator(api['components']['schemas']['PlanSlot'])
        validator.validate(slot)
        slot['score_x100']=100
        with self.assertRaises(ValidationError):validator.validate(slot)
    def test_unexecuted_materials_leave_all_gates_unclaimed(self):
        r=validate_execution()
        for key in ('application_executed','hermes_installed','live_model_called'):self.assertFalse(r[key])

if __name__=='__main__':unittest.main()
