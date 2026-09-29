"""Versioned local repair proposals only: no database writes, approval or model calls."""
import copy
import json
from pathlib import Path
from services.api.settings import settings
from services.api.repositories import PostgresJobRepository
from services.hermes_adapter.http_adapter import HermesHttpAdapter
from services.validators import validate_candidate

root=Path(__file__).resolve().parents[3]
p=Path(__file__).parent
source=json.loads((root/'acceptance-runs/m1-03/hermes-upgrade-20260924-001/live-full/latest-job.json').read_text())
repo=PostgresJobRepository();job=repo.get_by_job_id(source['job_id'])
assert job is not None
results={r['slot_id']:r for r in repo.results(job['job_id'])}
summary=[]
for order in [11,13]:
    sid=f'slot_{order:03d}';slot=next(s for s in job['slots'] if s['slot_id']==sid)
    original=results.get(sid,{}).get('candidate')
    if original is None:
        run=job['run_refs'][sid]['author']['run_id']
        original=json.loads(HermesHttpAdapter()._request('GET','/v1/runs/'+run).json()['output'])
    fixed=copy.deepcopy(original);answer=fixed['private']['answers'][0]
    answer.update(scoring_mode='exclusive',partial_score_x100=200,rubric=[])
    if order==13:
        answer['correct_option_ids']=[fixed['public']['options'][i]['id'] for i in [0,2]]
        answer['solution']=[{'type':'text','text':'A=[1,2]，B=[a-1,a+1]。a=2时A是B的真子集，因此选项A正确；a=2也证明选项C所述存在性。两集合不相等，且并非所有a都满足包含关系。正确选项为A、C。'}]
    spec=copy.deepcopy(job['spec_snapshot']);spec['multiple_choice_partial_score_x100']=200
    draft_slot={**slot,'question_revision_id':f'draft-not-applied:{sid}:v2'}
    old_check=validate_candidate(original,slot,job['spec_snapshot'])
    new_check=validate_candidate(fixed,draft_slot,spec)
    assert old_check['overall_status']=='FAIL'
    assert new_check['overall_status']=='REVIEW'
    assert old_check['content_hash']!=new_check['content_hash']
    record={'status':'DRAFT_NOT_APPLIED','source_job_id':job['job_id'],'source_slot_id':sid,
            'revision':'v2-local-proposal','teacher_partial_score_x100_to_confirm':200,
            'candidate':fixed,'validation':new_check}
    (p/f'q{order}-repair-draft.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
    summary.append({'order':order,'before':old_check['overall_status'],'after':new_check['overall_status'],
                    'checks':[(c['rule_id'],c['status']) for c in new_check['rule_checks']]})
(p/'repair-checks.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(summary)
