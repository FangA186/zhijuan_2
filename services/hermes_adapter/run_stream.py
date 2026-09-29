"""Read native Hermes SSE; only publish explicit output and safe event fields."""
import json
import queue
import re
import threading

import httpx


def safe_text(value):
    text = str(value or '')
    text = re.sub(r'(?i)(bearer\s+|(?:api[_-]?key|authorization|password|token)\s*[=:]\s*)[^\s,;"}]+', r'\1[hidden]', text)
    return re.sub(r'\bsk-[A-Za-z0-9_-]+', '[hidden]', text)


def public_event(raw):
    """No reasoning.available, headers, tool arguments, or arbitrary result objects."""
    kind = raw.get('event')
    fields = {
        'message.delta': ('delta',), 'message.interim': ('text',),
        'tool.started': ('tool',), 'tool.completed': ('tool', 'duration', 'error'),
        'run.started': (), 'run.completed': (), 'run.failed': ('error',),
        'run.cancelled': (), 'run.interrupted': ('error',),
    }
    if kind not in fields:
        return None
    return {'event': kind, **{k: safe_text(raw[k]) if isinstance(raw[k], str) else raw[k]
                            for k in fields[kind] if k in raw and isinstance(raw[k], (str, int, float, bool))}}


class RunStream:
    def __init__(self, adapter, request, emit):
        self.adapter, self.request, self.emit = adapter, request, emit
        self.events = queue.Queue(maxsize=1024)
        self.stop = threading.Event()
        self.thread = None
        self.response = None
        self.run_id = None
        self.error = None
        self.saw_delta = False

    def start(self, run_id):
        self.run_id = run_id
        self.thread = threading.Thread(target=self.read, daemon=True)
        self.thread.start()

    def read(self):
        try:
            with self.adapter.client.stream('GET', self.adapter.base_url + f'/v1/runs/{self.run_id}/events',
                    headers={'Authorization': f'Bearer {self.adapter.api_key}'}, timeout=30) as response:
                self.response = response
                response.raise_for_status()
                if 'text/event-stream' not in response.headers.get('content-type', ''):
                    raise ValueError('NOT_SSE')
                data = []
                for line in response.iter_lines():
                    if self.stop.is_set():
                        return
                    if line.startswith('data:'):
                        data.append(line[5:].lstrip())
                    elif not line and data:
                        raw = json.loads('\n'.join(data))
                        data = []
                        if raw.get('run_id') != self.run_id:
                            raise ValueError('RUN_ID_MISMATCH')
                        event = public_event(raw)
                        if event:
                            while not self.stop.is_set():
                                try:
                                    self.events.put(event, timeout=.2)
                                    break
                                except queue.Full:
                                    continue
        except (httpx.HTTPError, ValueError, TypeError):
            self.error = '实时事件连接中断或不可用；继续查询原调用，最终输出将单独显示。'

    def drain(self):
        batch = []
        while True:
            try:
                item = self.events.get_nowait()
            except queue.Empty:
                break
            if item['event'] == 'message.delta' and batch and batch[-1]['event'] == 'message.delta':
                batch[-1]['delta'] += item.get('delta', '')
            else:
                batch.append(item)
        for item in batch:
            self.saw_delta |= item['event'] == 'message.delta'
            self.emit({'event': 'activity', 'task_ref': self.request.task_ref,
                       'run_id': self.run_id, 'data': item})
        if self.error:
            message, self.error = self.error, None
            self.emit({'event': 'activity', 'task_ref': self.request.task_ref,
                       'data': {'event': 'stream.unavailable', 'text': message}})

    def close(self):
        self.stop.set()
        if self.response is not None:
            self.response.close()
        if self.thread:
            self.thread.join(timeout=2.5)


class TransportInfo:
    def health(self):
        return {"agent_framework": "hermes", "gateway_configured": bool(self.base_url and self.api_key)}

    def capabilities(self):
        return {"native_runs": True, "native_events": True, "tested_tool_isolation": False, "tested_json_output": False}


def terminal_failure(state, usage):
    from reference_code.adapter_contract import RunResult
    if 'upstream_result_unknown' in str(state.get('error', '')):
        return RunResult('UNKNOWN', None, (), usage, 'HERMES_PROVIDER_RECONCILE')
    return RunResult('FAILED', None, (), usage, 'HERMES_PARTIAL' if state.get('partial') else 'HERMES_FAILED')
