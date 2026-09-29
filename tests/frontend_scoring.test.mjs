import test from 'node:test';
import assert from 'node:assert/strict';
import { canonicalSections, sectionItemScores, validateScoreBalance } from '../apps/web/src/lib/scoring.ts';

const section = (id, kind, scores, topics=['考点']) => ({ id, title:id, question_type:kind,
  count:scores.length, score_each_x100:scores[0], item_scores_x100:scores,
  total_score_x100:scores.reduce((a,b)=>a+b,0), topics });
const paper = (topics) => [section('single','single_choice',Array(10).fill(400),topics),
  section('multi','multiple_choice',Array(3).fill(400),topics),
  section('fill','fill_blank',Array(4).fill(400),topics),
  section('solution','solution',[1200,1400,1400,1400,1400,1400],topics)];

test('imported 23-question 150-point paper preserves unequal solution scores on save', () => {
  const original=paper(), before=JSON.stringify(original);
  assert.equal(original.reduce((s,x)=>s+x.count*x.score_each_x100,0),14000); // Old failure.
  assert.equal(validateScoreBalance(original,15000).isBalanced,true);
  const saved=canonicalSections(original);
  assert.equal(saved.length,5);
  assert.equal(saved.reduce((s,x)=>s+x.count,0),23);
  assert.equal(saved.reduce((s,x)=>s+x.count*x.score_each_x100,0),15000);
  assert.deepEqual(saved.filter(x=>x.question_type==='solution').flatMap(x=>Array(x.count).fill(x.score_each_x100)),[1200,1400,1400,1400,1400,1400]);
  assert.ok(saved.every(s=>!('item_scores_x100' in s) && !('total_score_x100' in s)));
  assert.equal(JSON.stringify(original),before);
  assert.deepEqual(canonicalSections(saved),saved);
});

test('full textbook scope keeps all selected topics within the existing 30-topic section limit', () => {
  const topics=Array.from({length:89},(_,i)=>`考点${i}`), original=paper(topics), saved=canonicalSections(original);
  assert.ok(saved.length<=30);
  assert.ok(saved.every(s=>s.topics.length<=30));
  for(const kind of original.map(s=>s.question_type)) {
    assert.deepEqual([...new Set(saved.filter(s=>s.question_type===kind).flatMap(s=>s.topics))],topics);
  }
  assert.deepEqual(saved.flatMap(s=>Array(s.count).fill(s.score_each_x100)),original.flatMap(s=>s.item_scores_x100));
});

test('contradictory or invalid item scores cannot bypass exact score validation', () => {
  const s=section('solution','solution',[1200,1400]);
  assert.throws(()=>sectionItemScores({...s,count:3}),/数量/);
  assert.throws(()=>sectionItemScores({...s,total_score_x100:3000}),/不一致/);
  assert.throws(()=>sectionItemScores({...s,item_scores_x100:[1200,-1]}),/正整数/);
  assert.equal(validateScoreBalance([s],2601).isBalanced,false);
  assert.equal(validateScoreBalance([{...s,count:3}],2600).isBalanced,false);
  assert.deepEqual(sectionItemScores({id:'s',title:'s',question_type:'solution',topics:['a'],count:3,score_each_x100:33,total_score_x100:100}),[33,33,34]);
});
