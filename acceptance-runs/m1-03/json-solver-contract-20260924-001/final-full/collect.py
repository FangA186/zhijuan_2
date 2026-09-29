"""Collect bounded, non-content evidence for the final live regression."""
import json
import sqlite3
import urllib.request
from pathlib import Path

p=Path(__file__).parent
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
base='http://127.0.0.1:8000/v1/exams/current/'
job=json.load(op.open(base+'generation-jobs/current',timeout=10))
assert job['job_id']==json.loads((p/'started-job.json').read_text())['job_id']
assert job['status'] in {'COMPLETED','PARTIAL_FAILED','FAILED','RECONCILING','CANCELLED'}
records=json.load(op.open(base+'validation',timeout=10))
steps=[{'question':qid,'steps':len((record.get('blind_evidence') or {}).get('steps',[])),
        'status':record['overall_status']} for qid,record in records.items() if record.get('blind_evidence')]
a=json.loads((p/'ledger-before.json').read_text())['max_id']
with sqlite3.connect('file:/tmp/zhijuan-workflow-20260922/budget/acceptance.sqlite?mode=ro',uri=True) as c:
    values=c.execute('select id,status,http_status,content_json_valid,finish_reason,completion_tokens from reservations where id>? order by id',(a,)).fetchall()
rows=[dict(zip(['id','status','http_status','json_valid','finish_reason','completion_tokens'],v)) for v in values]
result={'job_status':job['status'],'processed':job['completed_slots'],'total':job['total_slots'],
        'slot_counts':{s:sum(x['status']==s for x in job['slots']) for s in {x['status'] for x in job['slots']}},
        'requests':len(rows),'valid_json':sum(x['json_valid']==1 for x in rows),
        'invalid_json':sum(x['json_valid']==0 for x in rows),'steps_over_four':[s for s in steps if s['steps']>4]}
(p/'transport-results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
(p/'solver-step-counts.json').write_text(json.dumps(steps,ensure_ascii=False,indent=2))
(p/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))
