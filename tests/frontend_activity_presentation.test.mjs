import test from 'node:test';
import assert from 'node:assert/strict';
import { readableOutput, timelineLogs, activityText } from '../apps/web/src/pages/job-progress/activityPresentation.ts';

test('incomplete JSON streams readable text with escaped quotes and linebreaks', () => {
  assert.equal(readableOutput('{"public":{"prompt":[{"text":"已知 x\\n求解'), '已知 x\n求解');
  assert.equal(readableOutput('{"summary":"核对\\"A\\"选项'), '核对"A"选项');
  assert.equal(readableOutput('{"private":'), '');
});
test('final author output exposes body and answers without altering actual text', () => {
  const raw = JSON.stringify({public:{prompt:[{text:'<script>不是HTML</script>'}],options:[{id:'x',content:[{text:'甲'}]},{id:'y',content:[{text:'乙'}]}]},private:{answers:[{correct_option_ids:['y'],solution:[{text:'因为乙成立'}]}]}});
  assert.equal(readableOutput(raw), '<script>不是HTML</script>\n\nA. 甲\n\nB. 乙\n\n参考答案：B\n\n因为乙成立');
});
test('replace duplicate final text while preserving role, attempts and raw payload', () => {
  const base={role:'author',slot_id:'slot_001',attempt:0,timestamp:'2026-09-25T00:00:00Z'};
  const final={...base,kind:'run.result',message:'{"summary":"审核意见"}',data:{output:'{"summary":"审核意见"}'}};
  const stream=[{...base,kind:'phase_started'}, {...base,kind:'message.delta',message:'{"summary":"'},final,{...base,attempt:1,kind:'message.delta',message:'new'}];
  const rows=timelineLogs(stream);
  assert.equal(rows.length,3);
  assert.equal(rows[1],final);
  assert.equal(activityText(final),'审核意见');
  assert.equal(rows[2].message,'new');
});
