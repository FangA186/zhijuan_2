"""One authorized full-paper generation; read-only polling never resubmits."""
import json
import time
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler
from datetime import datetime, timezone

ROOT = Path(__file__).parent
BASE = 'http://127.0.0.1:8000/v1/exams/current'
opener = build_opener(ProxyHandler({}))


def call(path, method='GET', data=None, etag=None):
    headers = {'Content-Type': 'application/json'}
    if etag:
        headers['If-Match'] = etag
    body = json.dumps(data).encode() if data is not None else None
    with opener.open(Request(BASE+path, data=body, headers=headers, method=method), timeout=30) as r:
        return json.load(r), r.headers.get('ETag')


def save(name, data):
    (ROOT/name).write_text(json.dumps(data, ensure_ascii=False, indent=2))


spec, etag = call('/spec')
old, _ = call('/generation-jobs/current')
if old['status'] not in {'COMPLETED', 'PARTIAL_FAILED', 'FAILED', 'CANCELLED'}:
    raise RuntimeError('Another job is active or unresolved; do not start')
save('before-job.json', old)
save('input-spec.json', spec)
plan, _ = call('/plans/generate', 'POST', etag=etag)
assert len(plan['slots']) == 23, 'Unexpected paper size'
save('plan.json', plan)
call('/plans/'+plan['plan_id']+'/confirm', 'POST', etag=etag)
job, _ = call('/generation-jobs', 'POST', etag=etag)
assert job['job_id'] != old['job_id'], 'Idempotent replay is not a new test'
save('started-job.json', job)
print('NEW_JOB_STARTED',job['status'],job['total_slots'], flush=True)
terminal = {'COMPLETED', 'PARTIAL_FAILED', 'FAILED', 'CANCELLED', 'RECONCILING'}
last = None
for _ in range(180):
    current, _ = call('/generation-jobs/current')
    assert current['job_id'] == job['job_id'], 'Current task changed externally'
    save('latest-job.json', current)
    key = (current['status'], current['completed_slots'], tuple(s['status'] for s in current['slots']))
    if key != last:
        with (ROOT/'transitions.jsonl').open('a') as f:
            f.write(json.dumps({'at':datetime.now(timezone.utc).isoformat(), 'status':current['status'],
                               'completed':current['completed_slots'], 'slots':current['slots']},ensure_ascii=False)+'\n')
        print('PROGRESS',current['status'],current['completed_slots'],'/',current['total_slots'],flush=True)
        last = key
    if current['status'] in terminal:
        break
    time.sleep(10)
else:
    raise RuntimeError('Observation timeout; task not restarted or cancelled')
validation, _ = call('/validation')
# Keep check evidence, not private answers or model reasoning.
safe = {qid: {k:v for k,v in record.items() if k != 'blind_evidence'} for qid,record in validation.items()}
for qid,record in validation.items():
    blind = record.get('blind_evidence') or {}
    safe[qid]['blind_summary'] = {k:blind.get(k) for k in ['match_reference','is_same_model']}
save('validation-evidence.json',safe)
rows=[]
for slot in current['slots']:
    record = next((v for v in safe.values() if v.get('revision',{}).get('question_revision_id') == f"{job['job_id']}:{slot['slot_id']}"), {})
    rows.append({'order':slot['order'],'kind':slot['kind'],'status':slot['status'],
                 'failure':slot.get('failure'), 'checks':[c for c in record.get('rule_checks',[]) if c['status']!='PASS'],
                 'blind_summary':record.get('blind_summary')})
save('per-question.json',rows)
print('TERMINAL',current['status'], 'COUNTS', {s:sum(r['status']==s for r in rows) for s in set(r['status'] for r in rows)},flush=True)
