"""Local teacher planner admission, recovery, activity and cancellation."""
from fastapi import APIRouter, Depends, Header, HTTPException
from services.api.planning_repository import PlanningRepository
from services.api.store import store
from services.exam.planning_service import PlanningService
from .exam_activity_routes import local_teacher
from .exam_route_helpers import require_revision

router = APIRouter(dependencies=[Depends(local_teacher)])


@router.get('/current/planning-jobs/current')
def current_planning():
    job = PlanningService.current()
    visible = PlanningService.public(job)
    if visible:
        visible['stale'] = job['spec_revision'] != store.get_spec_revision()
        if visible['stale']:
            visible.pop('result', None)
    return visible


@router.post('/current/planning-jobs', status_code=202)
def start_planning(if_match: str | None = Header(None), idempotency_key: str | None = Header(None)):
    revision = require_revision(if_match)
    if not idempotency_key or not 8 <= len(idempotency_key) <= 100:
        raise HTTPException(422, '需要有效的 Idempotency-Key')
    try:
        return PlanningService.public(PlanningService.start(idempotency_key, revision))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post('/current/planning-jobs/{job_id}/cancel')
def cancel_planning(job_id: str):
    repo = PlanningRepository()
    job = repo.get('planning:current')
    if not job or job['job_id'] != job_id:
        raise HTTPException(404, '规划任务不存在')
    if job['status'] in {'QUEUED', 'RUNNING', 'RECONCILING'}:
        if job['status'] == 'RECONCILING':
            raise HTTPException(409, '外部执行结果未知，需先核对 Hermes 调用状态')
        job['stop_requested'] = True
        job['status'] = 'RECONCILING' if job['status'] == 'RUNNING' else 'CANCELLED'
        if job['status'] == 'RECONCILING':
            job['error'] = '已请求停止；等待 Hermes 终态核对，期间不会重新调用'
        job = repo.replace(job, job['version'])
    return PlanningService.public(job)
