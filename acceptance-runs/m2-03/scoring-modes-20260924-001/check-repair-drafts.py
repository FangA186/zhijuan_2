"""Blind-check local repair proposals through the isolated solver; never publish/apply."""
import json
import hashlib
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from reference_code.adapter_contract import RunRequest
from services.api.settings import settings
from services.exam.question_service import QuestionService
from services.hermes_adapter.blind_runtime import BlindSolverRuntime
from services.hermes_adapter.comparator import compare_answers
from services.hermes_adapter.solver_output import valid_solver_steps
from services.validators import validate_candidate

p=Path(__file__).parent
spec=json.loads((p/'before-spec.json').read_text());spec['multiple_choice_partial_score_x100']=200
old=json.loads((p/'before-job.json').read_text())
summary=[]
for order in [11,13]:
    file=p/f'q{order}-repair-draft.json';draft=json.loads(file.read_text());candidate=draft['candidate']
    adapter=QuestionService.get_adapter();public=BlindSolverRuntime(adapter).prepare_blind_input(candidate['public'])
    events=[]
    def event(e):
        events.append(dict(e));(p/f'q{order}-blind-events.json').write_text(json.dumps(events,ensure_ascii=False,indent=2))
    result=adapter.run_stage(RunRequest(task_ref=f'repair-draft-{order}-{uuid4().hex}',provider='deepseek',model_id=settings.deepseek_model_id,
        role='solver',input_payload={'public_question':public},schema_name='blind_solver',
        skill_bundle_hash=hashlib.sha256(Path('skills/blind-solver/SKILL.md').read_bytes()).hexdigest(),policy_hash='repair-draft-verification',
        max_iterations=1,deadline_utc=(datetime.now(timezone.utc)+timedelta(seconds=120)).isoformat(),capability_grant_ref='isolated-repair-draft-check'),event)
    if result.status!='SUCCEEDED' or result.payload is None:raise RuntimeError('Repair draft solver did not complete; no retry')
    solved=result.payload
    assert valid_solver_steps(solved.get('steps',[]))
    answer=candidate['private']['answers'][0]
    report=compare_answers('',answer['correct_option_ids'],solved['derived_answer'],solved['selected_option_ids'],settings.deepseek_model_id,steps=solved.get('steps',[])).to_dict()
    slot=next(s for s in old['slots'] if s['order']==order)
    slot={**slot,'question_revision_id':f'draft-not-applied:{slot["slot_id"]}:v2'}
    draft['validation']=validate_candidate(candidate,slot,spec,report)
    draft['blind_usage']=dict(result.usage)
    file.write_text(json.dumps(draft,ensure_ascii=False,indent=2))
    summary.append({'question':order,'status':draft['validation']['overall_status'],'blind_agreement':report['match_reference']})
    print(summary[-1],flush=True)
(p/'repair-blind-checks.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
