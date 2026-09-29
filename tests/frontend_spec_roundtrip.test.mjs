import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from '../apps/web/node_modules/esbuild/lib/main.js';

test('saving a teacher-selected partial score keeps it in the canonical API body', async t => {
  const built=await build({entryPoints:['apps/web/src/lib/apiBase.ts'],bundle:true,write:false,
    format:'esm',platform:'node',define:{'import.meta.env':'{}'},logLevel:'silent'});
  const {ApiBase}=await import('data:text/javascript;base64,'+Buffer.from(built.outputFiles[0].text).toString('base64'));
  const original=Object.getOwnPropertyDescriptor(globalThis,'localStorage');
  Object.defineProperty(globalThis,'localStorage',{configurable:true,value:{setItem(){}}});
  t.after(()=>original ? Object.defineProperty(globalThis,'localStorage',original) : delete globalThis.localStorage);
  let written;
  t.mock.method(globalThis,'fetch',async (_url, options) => {
    if(options?.method==='PUT')written=JSON.parse(options.body);
    return new Response(JSON.stringify(written || {stage:'senior',stage_year:1}),{headers:{ETag:'"7"'}});
  });
  const saved=await new ApiBase().saveExamSpec({title:'test',stage:'senior',stage_year:1,
    multiple_choice_partial_score_x100:200,total_score_x100:400,
    sections:[{id:'m',title:'多选',question_type:'multiple_choice',count:1,score_each_x100:400,topics:['集合']}],
  });
  assert.equal(written.multiple_choice_partial_score_x100,200);
  assert.equal(saved.multiple_choice_partial_score_x100,200);
});


test('student projection excludes new private grading fields and correct options', async () => {
  const built=await build({entryPoints:['apps/web/src/lib/projection.ts'],bundle:true,write:false,
    format:'esm',platform:'node',logLevel:'silent'});
  const {makePublicProjection}=await import('data:text/javascript;base64,'+Buffer.from(built.outputFiles[0].text).toString('base64'));
  const projected=makePublicProjection({public:{local_id:'q',children:[]},private:{answers:[{
    scoring_mode:'exclusive',partial_score_x100:200,correct_option_ids:['C'],rubric:[],
  }]}});
  assert.deepEqual(projected,{local_id:'q',children:[]});
  assert.doesNotMatch(JSON.stringify(projected),/scoring_mode|partial_score|correct_option|private/);
});
