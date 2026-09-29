"""Explicit one-slot live probe using existing queue/DB, preserving the current paper."""
import argparse
import copy
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.local_runtime import load_dotenv
from services.api.repositories import PostgresJobRepository
from services.blueprint.generator import BlueprintGenerator
from services.exam.job_service import GenerationJobService

IDENTITY = ROOT / '.runtime/live-review-job.json'
PAGE = ROOT / 'apps/web/live-review.html'


def start():
    repo = PostgresJobRepository()
    current = repo.get('current')
    if not current or current['status'] not in {'COMPLETED', 'PARTIAL_FAILED', 'FAILED', 'CANCELLED'}:
        raise RuntimeError('Current paper must be idle')
    spec = copy.deepcopy(current['spec_snapshot'])
    section = copy.deepcopy(next(s for s in spec['sections'] if s['question_type'] == 'multiple_choice'))
    section.update(count=1)
    section.pop('item_scores_x100', None)
    spec.update(title='真实单题审核与输出流验收', sections=[section], total_score_x100=section['score_each_x100'])
    exam_id, job_id = 'live-review-' + uuid.uuid4().hex[:12], str(uuid.uuid4())
    plan = BlueprintGenerator.generate(spec, exam_id=exam_id)
    plan['confirmed'] = True
    with repo.psycopg.connect(repo.dsn) as db:
        if db.execute('SELECT current_database()').fetchone()[0] != 'zhijuan_local':
            raise RuntimeError('Only the verified local database is allowed')
        db.execute('INSERT INTO generation_exam_revisions VALUES (%s,1)', (exam_id,))
        db.execute('INSERT INTO generation_exam_state VALUES (%s,1,%s::jsonb)',
                   (exam_id, json.dumps({'spec_revision': 1, 'blueprint': plan})))
    job = {'job_id': job_id, 'exam_id': exam_id, 'revision': 1, 'spec_revision': 1,
        'version': 1, 'status': 'QUEUED', 'total_slots': 1, 'completed_slots': 0,
        'tokens_used': None, 'estimated_cost_cny': None, 'usage_status': 'UNKNOWN',
        'started_at': None, 'updated_at': datetime.now(timezone.utc).isoformat(),
        'slots': [{**slot, 'status': 'PENDING'} for slot in plan['slots']], 'logs': [],
        'spec_snapshot': spec, 'plan_snapshot': plan}
    repo.create(job)
    IDENTITY.write_text(json.dumps({'exam_id': exam_id, 'job_id': job_id}))
    print(json.dumps({'job_id': job_id, 'exam_id': exam_id, 'slots': 1}), flush=True)


def snapshot():
    identity = json.loads(IDENTITY.read_text())
    job = PostgresJobRepository().get(identity['exam_id'])
    if job['job_id'] != identity['job_id']:
        raise RuntimeError('Job identity changed')
    visible = GenerationJobService._public(job)
    visible['logs'] = job.get('activity', []) + job.get('logs', [])
    return visible


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/events':
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Access-Control-Allow-Origin', 'http://localhost:3000')
        self.end_headers()
        version = None
        while True:
            job = snapshot()
            if job['version'] != version:
                try:
                    self.wfile.write(('data: ' + json.dumps(job, ensure_ascii=False) + '\n\n').encode())
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return
                version = job['version']
            if job['status'] in {'COMPLETED', 'PARTIAL_FAILED', 'FAILED', 'CANCELLED', 'RECONCILING'}:
                return
            time.sleep(.4)

    def log_message(self, *args):
        pass


def serve():
    PAGE.write_text('''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>知卷 · 真实单题执行</title><body><div id="root"></div><script type="module">
import React from 'react'; import {createRoot} from 'react-dom/client';
import {AgentActivityConsole} from '/src/pages/job-progress/AgentActivityConsole.tsx'; import '/src/index.css';
function View(){const [job,setJob]=React.useState(null); React.useEffect(()=>{const s=new EventSource('http://127.0.0.1:8769/events');
s.onmessage=e=>{const j=JSON.parse(e.data);setJob(j);if(!['QUEUED','RUNNING'].includes(j.status))s.close()};return()=>s.close()},[]);
return React.createElement('main',{className:'max-w-4xl mx-auto p-4'},React.createElement('h1',{className:'text-lg font-bold p-3'},'真实单题验收 · DeepSeek / Hermes'),
job ? React.createElement(AgentActivityConsole,{logs:job.logs,terminal:!['QUEUED','RUNNING'].includes(job.status),status:job.status+' · '+job.job_id}):'连接执行记录…')}
createRoot(document.getElementById('root')).render(React.createElement(View));</script></body></html>''')
    print('http://localhost:3000/live-review.html', flush=True)
    try:
        ThreadingHTTPServer(('127.0.0.1', 8769), Handler).serve_forever()
    finally:
        PAGE.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['start', 'serve', 'status'])
    args = parser.parse_args()
    load_dotenv()
    if args.command == 'start':
        start()
    elif args.command == 'serve':
        serve()
    else:
        job = snapshot()
        print(json.dumps({'status': job['status'], 'job_id': job['job_id'],
            'events': len(job['logs']), 'kinds': sorted(set(l.get('kind','legacy') for l in job['logs'])),
            'roles': sorted(set(l['role'] for l in job['logs']))}, ensure_ascii=False))
