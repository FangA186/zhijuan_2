import copy
import json
import unittest
from pathlib import Path
from services.validators import validate_candidate
from services.hermes_adapter.schema_validator import validate_candidate as validate_shape, SchemaValidationError
from services.exam.spec_validation import validate_spec
from tests import test_validators as fixture
from services.hermes_adapter.blind_runtime import BlindSolverRuntime, SecurityIsolationError


class ScoringModesTests(unittest.TestCase):
    def candidate(self):
        c = fixture.ValidatorTests().candidate()
        c['public'].update(kind='multiple_choice', score_x100=400)
        c['public']['options'].append({'id':'C','content':[{'type':'text','text':'C'}]})
        a = c['private']['answers'][0]
        a.update(correct_option_ids=['A','B','C'], scoring_mode='exclusive', partial_score_x100=200, rubric=[])
        return c

    def check(self, c, partial=200):
        return validate_candidate(c, {'kind':c['public']['kind'],'score_x100':c['public']['score_x100']},
                                  {'multiple_choice_partial_score_x100':partial})

    def test_four_two_zero_tiers_are_not_summed_and_input_is_not_changed(self):
        c = self.candidate(); before = copy.deepcopy(c)
        validate_shape(c)
        result = self.check(c)
        self.assertEqual(result['overall_status'],'REVIEW')
        self.assertEqual(c,before)
        self.assertEqual(next(x['status'] for x in result['rule_checks'] if x['rule_id']=='ANSWER_AND_RUBRIC'),'PASS')
        self.assertNotEqual(result['content_hash'],self.check(c,0)['content_hash'])

    def test_teacher_policy_and_kind_cannot_be_overridden(self):
        self.assertEqual(self.check(self.candidate(),0)['overall_status'],'FAIL')
        c=self.candidate();c['private']['answers'][0].update(scoring_mode='additive',partial_score_x100=0,rubric=[{'id':'r','description':'score','score_x100':400,'acceptable_variants':[]}])
        self.assertEqual(self.check(c)['overall_status'],'FAIL')
        for partial in [-1,400,500,True,2.5]:
            c=self.candidate();c['private']['answers'][0]['partial_score_x100']=partial
            self.assertEqual(self.check(c)['overall_status'],'FAIL')
        c=self.candidate();c['public']['kind']='solution';c['private']['answers'][0].update(correct_option_ids=[],answer_kind='free_text')
        self.assertEqual(self.check(c)['overall_status'],'FAIL')

    def test_legacy_additive_stays_valid_and_zero_rubric_is_not_relaxed(self):
        c=fixture.ValidatorTests().candidate();validate_shape(c)
        c['private']['answers'][0]['rubric'][0]['score_x100']=0
        with self.assertRaises(SchemaValidationError):validate_shape(c)
        c=self.candidate();c['private']['answers'][0]['rubric']=[{'id':'r','description':'extra','score_x100':400,'acceptable_variants':[]}]
        with self.assertRaises(SchemaValidationError):validate_shape(c)

    def test_explicit_answer_conflict_is_reported_without_guessing_correct_answer(self):
        c=self.candidate();a=c['private']['answers'][0]
        a['correct_option_ids']=['C'];a['solution']=[{'type':'text','text':'全部选对（A、C）得满分。'}]
        result=self.check(c)
        self.assertEqual(next(x['status'] for x in result['rule_checks'] if x['rule_id']=='ANSWER_TEXT_CONSISTENCY'),'FAIL')
        self.assertEqual(a['correct_option_ids'],['C'])
        a['correct_option_ids']=['A','C'];self.assertEqual(self.check(c)['overall_status'],'REVIEW')
        for text in ['若只选A，不是全对。','正确答案为 A=[1,2]，此处A为集合。','正确选项为 A 和选项 C。']:
            a['solution']=[{'type':'text','text':text}]
            self.assertEqual(self.check(c)['overall_status'],'REVIEW')

    def test_new_private_scoring_fields_cannot_enter_blind_input(self):
        for key, value in [('scoring_mode','exclusive'),('partial_score_x100',200)]:
            q=copy.deepcopy(self.candidate()['public']);q[key]=value
            with self.assertRaises(SecurityIsolationError):BlindSolverRuntime(None).prepare_blind_input(q)

    def test_partial_credit_rejected_before_model_work_when_not_below_full_score(self):
        spec=json.loads(Path('acceptance/fixtures/minimum-senior.json').read_text())
        spec['sections'][0]['question_type']='multiple_choice'
        spec['multiple_choice_partial_score_x100']=spec['sections'][0]['score_each_x100']
        with self.assertRaisesRegex(ValueError,'少选得分'):validate_spec(spec)
        spec['multiple_choice_partial_score_x100']=0
        validate_spec(spec)
