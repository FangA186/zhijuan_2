import test from 'node:test';
import assert from 'node:assert/strict';
import { slotReasons } from '../apps/web/src/pages/exam-paper/slotDiagnostics.ts';

test('diagnostics bind to this job and distinguish exact failures, review and missing evidence', () => {
  const slot = {slot_id:'slot_011', status:'FAIL'};
  const record = {revision:{question_revision_id:'current:slot_011'},rule_checks:[
    {rule_id:'ANSWER_AND_RUBRIC',status:'FAIL'},
    {rule_id:'BLIND_COMPARISON',status:'REVIEW'},
  ]};
  const candidates = [{public:{local_id:'q11',kind:'multiple_choice'},private:{answers:[
    {local_question_id:'q11',correct_option_ids:['a']},
  ]}}];
  const reasons = slotReasons(slot,'current',{q11:record},candidates);
  assert.match(reasons[0], /1 个正确选项.*至少 2/);
  assert.match(reasons[1], /未获得盲解/);
  assert.match(slotReasons(slot,'new-job',{q11:record},candidates)[0], /未找到绑定本题/);
  record.blind_evidence = {match_reference:false,is_same_model:true};
  assert.match(slotReasons(slot,'current',{q11:record},candidates)[1], /不一致.*同一模型/);
  assert.deepEqual(slotReasons({...slot,status:'PENDING'},'current',{},[]), []);
});

import { snapshotSummary } from '../apps/web/src/pages/exam-paper/jobSnapshotSummary.ts';
test('terminal summary shows failed and review counts without stale active question', () => {
  const summary = snapshotSummary({completed_slots:3,total_slots:3,slots:[
    {status:'FAIL'}, {status:'REVIEW_REQUIRED'}, {status:'REVIEW_REQUIRED'},
  ]});
  assert.equal(summary.activeSlotId, null);
  assert.match(summary.note, /1 题失败，2 题待教师复核/);
  assert.equal(summary.progress.completed, 3);
});
