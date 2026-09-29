"""Local-only response capture reader: provider wire and Hermes results keep distinct sources."""
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import StreamingResponse
from tools.raw_api_server import read_records

_DEFAULT_DIR = Path(__file__).resolve().parents[3] / '.runtime/raw-api'


def local_diagnostics(request: Request):
    if not request.client or request.client.host not in {'127.0.0.1', '::1', 'testclient'}:
        raise HTTPException(403, '原始响应仅供本机诊断')
    origin = request.headers.get('origin')
    if origin and urlparse(origin).hostname not in {'localhost', '127.0.0.1', '::1'}:
        raise HTTPException(403, '不允许跨站读取或修改诊断记录')


router = APIRouter(prefix='/v1/raw-api', tags=['Diagnostics'], dependencies=[Depends(local_diagnostics)])


def _capture_path():
    return Path(os.getenv('ZHIJUAN_RAW_API_DIR') or _DEFAULT_DIR) / 'responses.ndjson'


@router.get('/status')
def raw_api_status():
    path = _capture_path()
    receipt_path = _DEFAULT_DIR / 'settings.json'
    try:
        receipt = json.loads(receipt_path.read_text())
    except (OSError, ValueError):
        receipt = {}
    return {'capture_enabled': receipt.get('capture_enabled'),
            'file_exists': path.exists(), 'file_size': path.stat().st_size if path.exists() else 0,
            'thinking_mode': receipt.get('thinking_mode', 'unknown'),
            'api_capture_enabled': bool(os.getenv('ZHIJUAN_RAW_API_DIR'))}


async def _event_stream(after=0):
    path, offset = _capture_path(), after
    while True:
        found = False
        for offset, record in read_records(path, offset):
            yield f'id: {offset}\ndata: {json.dumps(record, ensure_ascii=False)}\n\n'
            found = True
        if not found:
            yield ': waiting for captured response\n\n'
        await asyncio.sleep(.3)


@router.get('/events')
async def raw_api_events(after: int = 0, last_event_id: str | None = Header(None)):
    try:
        offset = int(last_event_id) if last_event_id else after
    except ValueError as exc:
        raise HTTPException(400, 'Invalid event cursor') from exc
    return StreamingResponse(_event_stream(offset), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@router.post('/clear')
def raw_api_clear():
    """Archive captures instead of deleting the only raw evidence."""
    path = _capture_path()
    archive = None
    if path.exists():
        archive = path.with_name('responses-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.ndjson')
        path.rename(archive)
    return {'cleared': True, 'archive': archive.name if archive else None}
