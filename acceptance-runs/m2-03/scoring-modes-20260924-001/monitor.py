"""Observe the one job started through the actual teacher form; never submit/retry."""
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

p=Path(__file__).parent
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
base='http://127.0.0.1:8000/v1/exams/current/'
def get(path):return json.load(op.open(base+path,timeout=20))
def save(name,data):(p/name).write_text(json.dumps(data,ensure_ascii=False,indent=2))
old=json.loads((p/'before-job.json').read_text())['job_id']
for _ in range(20):
    try:
        job=get('generation-jobs/current')
        if job['job_id']!=old:break
    except urllib.error.HTTPError as e:
        if e.code!=404:raise
    time.sleep(1)
else:raise RuntimeError('No new job observed; not resubmitting')
save('started-job.json',job)
spec=get('spec');assert spec['multiple_choice_partial_score_x100']==(int(sys.argv[1]) if len(sys.argv)>1 else 200)
save('input-spec.json',spec)
last=None
for _ in range(180):
    job=get('generation-jobs/current')
    assert job['job_id']!=old
    save('latest-job.json',job)
    key=(job['status'],job['completed_slots'])
    if key!=last:print(key,flush=True);last=key
    if job['status'] in {'COMPLETED','PARTIAL_FAILED','RECONCILING','FAILED','CANCELLED'}:break
    time.sleep(10)
else:raise RuntimeError('Observation timeout')
records=get('validation');candidates=get('questions')
summary=[]
for candidate in candidates:
    q=candidate['public'];a=candidate['private']['answers'][0];v=records.get(q['local_id'],{})
    summary.append({'question':q['local_id'],'kind':q['kind'],'scoring_mode':a.get('scoring_mode'),
                    'partial_score_x100':a.get('partial_score_x100'),'rubric_count':len(a.get('rubric',[])),
                    'checks':[(c['rule_id'],c['status']) for c in v.get('rule_checks',[])]})
save('scoring-results.json',summary)
print('FINAL',job['status'],{s:sum(slot['status']==s for slot in job['slots']) for s in {slot['status'] for slot in job['slots']}},flush=True)
