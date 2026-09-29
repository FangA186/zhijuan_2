import test from 'node:test';
import assert from 'node:assert/strict';
import {repairTemplateTopicScope,alignConcreteSections,topicLabel} from '../apps/web/src/lib/topicPlanning.ts';
import {canonicalSections} from '../apps/web/src/lib/scoring.ts';

test('template placeholder removal preserves approved scope and requires fresh confirmation',()=>{
  const s={taught_scope:{topics:['6.1 向量','7.1 复数','基础概念辨析'],scope_confirmed:true},sections:[{id:'s',topics:['基础概念辨析'],count:2,score_each_x100:400}]};
  const fixed=repairTemplateTopicScope(s);
  assert.deepEqual(fixed.taught_scope.topics,['6.1 向量','7.1 复数']);
  assert.deepEqual(fixed.sections[0].topics,['6.1 向量','7.1 复数']);
  assert.equal(fixed.taught_scope.scope_confirmed,false);assert.equal(s.taught_scope.scope_confirmed,true);
  assert.equal(repairTemplateTopicScope(fixed),null);
  assert.match(topicLabel('基础概念辨析'),/未绑定具体考点/);
  assert.equal(topicLabel('7.1 复数'),'7.1 复数');
});
test('existing 12/14-point canonical parts can adopt whole scope without losing scores',()=>{
  const topics=Array.from({length:83},(_,i)=>`考点${i}`);
  const sections=[{id:'s_part_1',title:'解答题',question_type:'solution',topics:['解答证明题'],count:1,score_each_x100:1200},
    {id:'s_part_2',title:'解答题',question_type:'solution',topics:['解答证明题'],count:5,score_each_x100:1400}];
  const fixed=repairTemplateTopicScope({taught_scope:{topics:[...topics,'解答证明题'],scope_confirmed:true},sections});
  const saved=canonicalSections(fixed.sections);
  assert.deepEqual(saved.flatMap(s=>Array(s.count).fill(s.score_each_x100)),[1200,1400,1400,1400,1400,1400]);
  assert.equal(new Set(saved.flatMap(s=>s.topics)).size,83);
  assert.ok(saved.every(s=>s.topics.length<=30));
});
test('explicit narrower targets survive and absent curriculum stays empty',()=>{
  const section={topics:['7.1 复数']};
  assert.deepEqual(alignConcreteSections([section],['6.1 向量','7.1 复数'])[0].topics,['7.1 复数']);
  assert.deepEqual(alignConcreteSections([{topics:['关键公式代入']}],[])[0].topics,[]);
});
