import test from 'node:test';
import assert from 'node:assert/strict';
import {freshRequest,applyRecord} from '../apps/web/public/raw-api-core.js';
test('preserves raw SSE and independently collects reasoning, content and tool argument chunks',()=>{
  const r=freshRequest({request_id:'one'});
  const chunks=[{choices:[{delta:{reasoning_content:'sample reasoning'}}]},
    {choices:[{delta:{content:'answer',tool_calls:[{index:0,id:'call1',function:{name:'f',arguments:'{"x":'}}]}}]},
    {choices:[{delta:{tool_calls:[{index:0,function:{arguments:'1}'}}]},finish_reason:'tool_calls'}],usage:{total_tokens:10}}];
  const wire=chunks.map(c=>`data: ${JSON.stringify(c)}\r\n\r\n`);
  for(const raw of wire)applyRecord(r,{kind:'sse',raw});
  applyRecord(r,{kind:'sse',raw:'data: [DONE]\n\n'});
  assert.equal(r.raw,wire.join('')+'data: [DONE]\n\n');
  assert.equal(r.reasoning,'sample reasoning');assert.equal(r.content,'answer');
  assert.equal(r.tools.get('0:0').arguments,'{"x":1}');assert.equal(r.usage.total_tokens,10);assert.equal(r.done,true);
});
test('keeps multiple nonstream tool calls separate and retains unknown fields in raw view',()=>{
  const r=freshRequest({request_id:'two'});
  const raw=JSON.stringify({custom_field:42,choices:[{message:{tool_calls:[{id:'a',function:{name:'a',arguments:'{}'}},{id:'b',function:{name:'b',arguments:'{}'}}]}}]});
  applyRecord(r,{kind:'body',raw});assert.equal(r.tools.size,2);assert.equal(r.raw,raw);assert.equal(r.done,true);
});
test('Hermes result wrapper is never labelled as provider wire even in older captures',()=>{
  const r=freshRequest({request_id:'old',source:'deepseek-upstream'});
  applyRecord(r,{kind:'hermes_output',raw:JSON.stringify({hermes_status:'completed',output:'answer'})});
  assert.equal(r.metadata.source,'hermes-adapter');assert.equal(r.content,'answer');
});

import {freshSession,applySessionRecord,sessionView} from '../apps/web/public/raw-api-core.js';
test('one session contains all interleaved requests without switching or reordering wire data',()=>{
  const s=freshSession();
  for(const request_id of ['first','second'])applySessionRecord(s,{request_id,kind:'request',source:'deepseek-upstream',thinking:{type:request_id==='first'?'disabled':'enabled'}});
  const emit=(request_id,content)=>applySessionRecord(s,{request_id,kind:'sse',raw:`data: ${JSON.stringify({choices:[{delta:{content}}]})}\n\n`});
  emit('first','a');emit('second','b');emit('first','c');
  const v=sessionView(s);
  assert.equal(v.count,2);assert.equal(v.modes.enabled,1);assert.equal(v.modes.disabled,1);
  assert.equal(v.raw,s.raw.join(''));assert.ok(v.raw.indexOf('b')<v.raw.lastIndexOf('c'));
  assert.match(v.content,/first.*\nac/s);assert.match(v.content,/second.*\nb/s);
});
test('empty reset session has no stale previous output',()=>{
  const v=sessionView(freshSession());assert.equal(v.raw,'');assert.equal(v.count,0);assert.equal(v.tools,'');
});
