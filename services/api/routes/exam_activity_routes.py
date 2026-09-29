"""Private local-teacher activity view, separate from public job progress."""
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from services.exam.job_service import GenerationJobService


def local_teacher(request: Request):
    # This workbench has no production identity yet. Never expose answer-bearing events remotely.
    if not request.client or request.client.host not in {'127.0.0.1', '::1', 'testclient'}:
        raise HTTPException(403, '模型输出仅供本机教师工作台访问')


router = APIRouter(dependencies=[Depends(local_teacher)])


def activity_snapshot():
    visible = GenerationJobService.get_current_job('current')
    if not visible:
        raise HTTPException(404, 'No generation job found')
    raw = GenerationJobService.repository().get('current')
    if not raw or raw['job_id'] != visible['job_id'] or raw['version'] != visible['version']:
        return None
    activity = raw.get('activity', [])
    if not activity:
        saved = GenerationJobService.repository().results(raw['job_id'])
        if saved:
            activity = [{'role': 'system', 'level': 'info', 'kind': 'history.notice',
                'timestamp': raw.get('updated_at', ''),
                'message': '这次任务没有实时事件记录。以下是已保存的题目结果，不是当时的实时输出。'}]
            for index, result in enumerate(saved):
                output = json.dumps(result['candidate'], ensure_ascii=False)
                activity.append({'id': f'saved-{index}', 'role': 'author', 'level': 'info',
                    'kind': 'saved.result', 'slot_id': result.get('slot_id', ''),
                    'timestamp': raw.get('updated_at', ''), 'message': output,
                    'data': {'source': 'generation_job_results', 'output': output}})
    visible['logs'] = activity + visible.get('logs', [])
    visible['activity_dropped'] = raw.get('activity_dropped', 0)
    visible['activity_available'] = bool(raw.get('activity'))
    if visible['activity_dropped']:
        visible['logs'].insert(0, {'role': 'system', 'level': 'warn', 'kind': 'storage.truncated',
            'timestamp': raw.get('updated_at', ''),
            'message': f"记录容量上限已到，较早的 {visible['activity_dropped']} 条事件已移出，当前显示保留记录。"})
    return visible


@router.get('/current/generation-jobs/activity')
def get_activity():
    snapshot = activity_snapshot()
    if snapshot is None:
        raise HTTPException(409, '任务正在更新，请重新读取')
    return snapshot


@router.get('/current/generation-jobs/activity/stream')
def stream_activity():
    async def events():
        previous = None
        while True:
            try:
                snapshot = await asyncio.to_thread(activity_snapshot)
            except HTTPException:
                yield 'event: error\ndata: {"detail":"Activity unavailable"}\n\n'
                return
            if snapshot and snapshot['version'] != previous:
                yield f"event: init\ndata: {json.dumps(snapshot, ensure_ascii=False)}\n\n"
                previous = snapshot['version']
            if snapshot and snapshot['status'] in {'COMPLETED', 'PARTIAL_FAILED', 'FAILED', 'CANCELLED'}:
                yield f"event: completed\ndata: {json.dumps(snapshot, ensure_ascii=False)}\n\n"
                return
            await asyncio.sleep(.4)
    return StreamingResponse(events(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
