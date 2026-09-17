from pathlib import Path
import copy, json, unittest
from jsonschema import Draft202012Validator, FormatChecker
P=Path(__file__).resolve().parents[1]

def read(path): return json.loads((P/path).read_text(encoding='utf-8'))
def validator(name):
    return Draft202012Validator(read(f'contracts/{name}.schema.json'),format_checker=FormatChecker())

class ContractTests(unittest.TestCase):
    def test_schemas_well_formed(self):
        for p in (P/'contracts').glob('*.schema.json'):
            Draft202012Validator.check_schema(json.loads(p.read_text(encoding='utf-8')))
    def test_all_examples(self):
        for name in ('exam-spec','candidate','public-question','blind-input','validation-record'):
            validator(name).validate(read(f'examples/{name}.json'))
    def test_blind_input_rejects_private_answer(self):
        x=read('examples/blind-input.json'); x['private']={'answer':'B'}
        self.assertTrue(list(validator('blind-input').iter_errors(x)))
    def test_student_question_rejects_private_answer(self):
        x=read('examples/public-question.json'); x['answer']='B'
        self.assertTrue(list(validator('public-question').iter_errors(x)))
    def test_nested_question_rejects_private(self):
        x=read('examples/blind-input.json'); x['public_question']['private']={'answer':'B'}
        self.assertTrue(list(validator('blind-input').iter_errors(x)))
    def test_material_group_requires_children_and_zero_parent_score(self):
        x=read('examples/public-question.json'); x['kind']='material_group'
        self.assertTrue(list(validator('public-question').iter_errors(x)))
    def test_example_scores_and_answer_refs_semantically_consistent(self):
        x=read('examples/exam-spec.json')
        self.assertEqual(x['total_score_x100'],sum(s['count']*s['score_each_x100'] for s in x['sections']))
        self.assertEqual(100,sum(x['difficulty_distribution'].values()))
        c=read('examples/candidate.json'); q=c['public']; a=c['private']['answers'][0]
        self.assertEqual(a['local_question_id'],q['local_id'])
        self.assertEqual(sum(r['score_x100'] for r in a['rubric']),q['score_x100'])
        self.assertEqual(len(a['correct_option_ids']),1)
        self.assertTrue(set(a['correct_option_ids']) <= {o['id'] for o in q['options']})
    def test_all_stage_spec_examples(self):
        for stage in ("primary","senior"):
            validator("exam-spec").validate(read(f"examples/exam-spec-{stage}.json"))
    def test_unknown_grade_stage_rejected(self):
        x=read('examples/exam-spec.json'); x['stage']='university'
        self.assertTrue(list(validator('exam-spec').iter_errors(x)))

if __name__ == '__main__': unittest.main()
