"""Temporary Vite page + local SSE fixture; no database or model calls. Ctrl-C removes HTML."""
import json
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / 'apps/web/review-activity-test.html'
HTML = '''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>审核输出离线验收</title><body>
<div id="fixture"></div><script type="module">
import React from 'react'; import {createRoot} from 'react-dom/client';
import {AgentActivityConsole} from '/src/pages/job-progress/AgentActivityConsole.tsx';
import '/src/index.css';
function Fixture(){const [data,setData]=React.useState({logs:[],terminal:false});
React.useEffect(()=>{const stream=new EventSource('http://127.0.0.1:8769/events');
stream.onmessage=e=>{const next=JSON.parse(e.data);setData(next);if(next.terminal)stream.close()};return()=>stream.close()},[]);
return React.createElement('main',{className:'max-w-4xl mx-auto p-4'},
React.createElement('h1',{className:'p-3 text-red-700 font-bold'},'离线验收夹具 · 模拟事件 · 无模型调用'),
React.createElement(AgentActivityConsole,{logs:data.logs,terminal:data.terminal,status:'验收题槽：审核 → 修订 → 重新盲解（模拟）'}))}
createRoot(document.getElementById('fixture')).render(React.createElement(Fixture));
</script></body></html>'''
EVENTS = [
    ('author', 'message.delta', '{"public":{"kind":"multiple_choice"},'),
    ('author', 'message.delta', '"private":{"answers":[{"correct_option_ids":["A"]}]}}'),
    ('reviewer', 'run.result', '{"action":"repair","issues":["多选题只有一个正确选项"],"summary":"修改选项后重新检查"}'),
    ('author', 'repair_reserved', '已登记第1轮修订'),
    ('author', 'message.delta', '{"correct_option_ids":["A","B"]}'),
    ('solver', 'message.delta', '{"selected_option_ids":["A","B"],"steps":[{"text":"逐项核验两项成立"}]}'),
    ('reviewer', 'run.result', '{"action":"no_change","summary":"修订完成，仍需教师复核"}'),
]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/events':
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Access-Control-Allow-Origin', 'http://localhost:3000')
        self.end_headers()
        logs = []
        for index, (role, kind, message) in enumerate(EVENTS):
            logs.append({'id': index, 'role': role, 'kind': kind, 'timestamp': '2026-09-25T00:00:00Z',
                'slot_id': 'fixture_q12', 'message': message, 'level': 'info',
                'attempt': 1 if index >= 3 else 0, 'data': {'event': kind, 'text': message}})
            payload = {'logs': logs, 'terminal': index == len(EVENTS) - 1}
            try:
                self.wfile.write(('data: ' + json.dumps(payload, ensure_ascii=False) + '\n\n').encode())
                self.wfile.flush()
            except BrokenPipeError:
                return
            time.sleep(1)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    PAGE.write_text(HTML)
    print('Fixture: http://localhost:3000/review-activity-test.html', flush=True)
    try:
        ThreadingHTTPServer(('127.0.0.1', 8769), Handler).serve_forever()
    finally:
        PAGE.unlink(missing_ok=True)
