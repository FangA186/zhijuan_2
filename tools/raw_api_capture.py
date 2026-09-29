"""Opt-in local tap of provider response bodies before any Hermes conversion."""
import base64
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

_LOCK = threading.Lock()
MAX_BYTES = 64 * 1024 * 1024


class RawCapture:
    def __init__(self, request, *, source="deepseek-upstream"):
        directory = os.getenv('ZHIJUAN_RAW_API_DIR', '')
        self.path = Path(directory) / 'responses.ndjson' if directory else None
        self.id = uuid.uuid4().hex
        self.source = source
        self.disabled = False
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.write('request', model=request.get('model'), role=request.get('role'), thinking=request.get('thinking'),
                       tool_choice=request.get('tool_choice'), max_tokens=request.get('max_tokens'),
                       reasoning_effort=request.get('reasoning_effort'), stream=request.get('stream'),
                       tools=[t.get('function', {}).get('name') for t in request.get('tools', [])])

    def write(self, kind, **fields):
        if not self.path or self.disabled:
            return
        record = {'request_id': self.id, 'source': self.source, 'kind': kind,
                  'timestamp': datetime.now(timezone.utc).isoformat(), **fields}
        encoded = (json.dumps(record, ensure_ascii=False) + '\n').encode()
        try:
            with _LOCK:
                if self.path.exists() and self.path.stat().st_size + len(encoded) > MAX_BYTES:
                    self.disabled = True
                    kind = 'capture_stopped'
                    fields = {'reason': '64 MiB capture limit reached; no more frames saved'}
                    record.update(kind=kind, **fields)
                    record.pop('raw', None)
                    record.pop('raw_base64', None)
                    encoded = (json.dumps(record) + '\n').encode()
                fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
                with os.fdopen(fd, 'ab') as out:
                    out.write(encoded)
                print(f'\n[raw-api {self.id} {kind}]', flush=True)
                if 'raw' in fields:
                    print(fields['raw'], end='' if fields['raw'].endswith('\n') else '\n', flush=True)
                else:
                    print(json.dumps(fields, ensure_ascii=False), flush=True)
        except OSError as exc:
            self.disabled = True
            print(f'[raw-api] Capture unavailable: {type(exc).__name__}', flush=True)

    def body(self, raw, kind='body'):
        try:
            text = raw.decode('utf-8') if isinstance(raw, bytes) else raw
            self.write(kind, raw=text)
        except UnicodeDecodeError:
            self.write(kind, raw_base64=base64.b64encode(raw).decode(), encoding='base64')
        return raw

    def lines(self, response):
        for line in response:
            self.body(line, 'sse')
            yield line


def apply_diagnostic_thinking(body):
    enabled = os.getenv('ZHIJUAN_DIAGNOSTIC_THINKING', 'disabled') == 'enabled'
    body['thinking'] = {'type': 'enabled' if enabled else 'disabled'}
    body['reasoning_effort'] = 'high' if enabled else 'none'
