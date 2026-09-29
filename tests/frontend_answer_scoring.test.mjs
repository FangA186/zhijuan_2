import test from 'node:test';
import assert from 'node:assert/strict';
import { answerScoring } from '../apps/web/src/lib/answerScoring.ts';

test('exclusive tiers preserve 4/2/0 and derive labels from only the structured answer', () => {
  const q={kind:'multiple_choice',score_x100:400,options:[{id:'a'},{id:'b'},{id:'c'}]};
  const a={scoring_mode:'exclusive',partial_score_x100:200,correct_option_ids:['a','c'],rubric:[]};
  let view=answerScoring(q,a);
  assert.equal(view.exclusive,true);
  assert.deepEqual(view.rows.map(r=>r.score_x100),[400,200,0]);
  assert.match(view.rows[0].description,/A、C/);
  a.correct_option_ids=['a','b'];
  assert.match(answerScoring(q,a).rows[0].description,/A、B/);
  a.partial_score_x100=400;
  assert.match(answerScoring(q,a).warning,/越界/);
  assert.equal(answerScoring(q,{rubric:[{description:'步骤',score_x100:400}]}).exclusive,false);
});

import { sectionIssues } from '../apps/web/src/lib/sectionScope.ts';
test('partial credit cannot reach full score before plan submission', () => {
  const sections=[{id:'m',question_type:'multiple_choice',count:1,score_each_x100:400}];
  assert.deepEqual(sectionIssues(sections,400,200),[]);
  assert.match(sectionIssues(sections,400,400).join(''),/少选得分必须小于/);
});
