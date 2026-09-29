"""Offline curriculum allocation and same-paper duplicate boundaries."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from services.blueprint.generator import BlueprintGenerator
from services.blueprint.topic_scope import choose_topic, topic_pool
from services.validators.diversity import same_paper_check, public_summaries
from services.validators import validate_candidate
from services.exam.question_service import QuestionService, GenerationFailure
from tests.test_validators import ValidatorTests


class TopicDiversityTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads(Path('acceptance/fixtures/minimum-primary.json').read_text())
        self.spec['taught_scope']['scope_confirmed'] = True

    def test_template_labels_are_rejected_before_planning_or_paid_author(self):
        self.spec['taught_scope']['topics'].append('基础概念辨析')
        self.spec['sections'][0]['topics']=['基础概念辨析']
        with self.assertRaisesRegex(ValueError, '通用标签'):
            BlueprintGenerator.generate(self.spec)
        with patch.object(QuestionService, 'get_adapter') as adapter:
            with self.assertRaisesRegex(GenerationFailure,'PLAN_TOPIC_UNRESOLVED'):
                QuestionService.generate_slot_result('q1',spec=self.spec,slot={'target_topic':'基础概念辨析','kind':'single_choice'})
            adapter.assert_not_called()

    def test_chapters_and_unused_leaf_targets_span_section_boundaries(self):
        topics=['第六章 向量','6.1 运算','6.1.1 加法','6.1.2 数乘','7.1 复数','7.1.1 复数概念',
                '7.1.2 共轭复数','8.1 立体几何','9.1 随机抽样','10.1 概率']
        self.spec['taught_scope']['topics']=topics
        for section in self.spec['sections']:section['topics']=topics
        plan=BlueprintGenerator.generate(self.spec)
        chosen=[s['target_topic'] for s in plan['slots']]
        self.assertEqual(chosen,['6.1.1 加法','7.1.1 复数概念','8.1 立体几何','9.1 随机抽样','10.1 概率'])
        self.assertEqual(sum(s['score_x100'] for s in plan['slots']),2000)
        self.assertEqual(plan['canonical_spec'],self.spec)
        self.assertFalse(plan['confirmed'])
        counts,chapters={},{}
        chosen=[choose_topic(topic_pool(topics),counts,chapters) for _ in range(7)]
        self.assertEqual(len(set(chosen)),7)

    def test_duplicate_failure_and_similar_review_do_not_conflate_math_symbols(self):
        def q(id,text):return {'local_id':id,'prompt':[{'type':'text','text':text}]}
        original=q('q1','已知复数 z 满足 (1+i)z=2i，求 z 的模。')
        duplicate=q('q2','（原创题）已知复数 z 满足 (1+i)z=2i，求 z 的模。')
        self.assertEqual(same_paper_check(duplicate,[original])[0],'FAIL')
        variant=q('q2','已知复数 z 满足 (1+i)z=2i，求 z 的共轭。')
        self.assertEqual(same_paper_check(variant,[original])[0],'REVIEW')
        variant['local_id']='q0'
        self.assertEqual(same_paper_check(duplicate,[variant,original])[0],'FAIL')
        self.assertNotEqual(same_paper_check(q('q2','求 x²'),[q('q1','求 x₂')])[0],'FAIL')
        self.assertNotEqual(same_paper_check(q('q2','求 z∈[0,1]'),[q('q1','求 z∈(0,1)')])[0],'FAIL')
        self.assertNotEqual(same_paper_check(q('q2',r'求 \overline{z}'),[q('q1','求 z')])[0],'FAIL')

    def test_duplicate_check_and_evidence_bind_to_peer_public_text(self):
        c=ValidatorTests().candidate();other=copy.deepcopy(c['public']);other['local_id']='q0'
        slot={'kind':'single_choice','score_x100':200}
        base=validate_candidate(c,slot,{})
        checked=validate_candidate(c,slot,{},previous_questions=[other])
        self.assertEqual(checked['overall_status'],'FAIL')
        self.assertNotEqual(base['content_hash'],checked['content_hash'])
        self.assertEqual(next(r['status'] for r in checked['rule_checks'] if r['rule_id']=='IN_PAPER_DIVERSITY'),'FAIL')
        other['private']={'answers':['never-copy']}
        self.assertNotIn('never-copy',json.dumps(public_summaries([other])))

    def test_current_peers_go_to_author_and_reviewer_but_not_solver(self):
        from reference_code.adapter_contract import RunResult
        candidate=json.loads(Path('examples/candidate.json').read_text())
        peer={'local_id':'previous','kind':'single_choice','prompt':[{'type':'text','text':'同卷公开题干'}]}
        spec=json.loads(Path('examples/exam-spec.json').read_text())
        calls=[]
        def run(request,*args):
            calls.append(request)
            if request.role=='author':data=candidate
            elif request.role=='solver':data={'derived_answer':'x=4','selected_option_ids':[],'steps':[]}
            else:data={'question_revision_id':'rev','action':'no_change','issues':[],'summary':'待人工复核'}
            return RunResult('SUCCEEDED',data,(),{},None)
        adapter=Mock();adapter.run_stage.side_effect=run
        slot={'kind':candidate['public']['kind'],'score_x100':candidate['public']['score_x100'],'question_revision_id':'rev'}
        with patch.object(QuestionService,'get_adapter',return_value=adapter):
            result=QuestionService.generate_slot_result(candidate['public']['local_id'],spec=spec,slot=slot,previous_questions=[peer])
        self.assertEqual(calls[0].input_payload['same_paper_questions'][0]['stem'],'同卷公开题干')
        self.assertEqual(set(calls[1].input_payload),{'public_question'})
        self.assertIn('same_paper_questions',calls[2].input_payload)
        self.assertEqual(result['validation']['overall_status'],'REVIEW')

    def test_structure_import_does_not_invent_curriculum_topics(self):
        from services.exam.template_parser import RuleTemplateParser
        parsed=RuleTemplateParser.parse(['合成测试卷','一、单项选择题（本大题共2小题，每小题4分，共8分）','1. 测试一','2. 测试二'])
        self.assertTrue(parsed['sections'])
        self.assertTrue(all(not s['topics'] for s in parsed['sections']))
