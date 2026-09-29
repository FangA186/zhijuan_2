"""One planner call per admitted task; unknown outcomes are never auto-retried."""
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from reference_code.adapter_contract import RunRequest
from services.api.job_run_events import append_activity
from services.api.planning_repository import PlanningRepository
from services.api.settings import settings
from services.api.store import store
from services.blueprint.planner import planning_input, bind_design
from services.exam.job_contracts import _now
from services.exam.question_service import QuestionService

ROOT = Path(__file__).resolve().parents[2]


def run_planning(job_id, repository=None, adapter=None):
    repo = repository or PlanningRepository()
    job = repo.get_by_job_id(job_id)
    if not job or job['status'] != 'QUEUED':
        return
    job.update(status='RUNNING', started_at=_now())
    job = repo.replace(job, job['version'])  # Claim before external work, including redelivery.
    ref = f'{job_id}:planner'

    def cancelled():
        current = repo.get('planning:current')
        return (not current or current['job_id'] != job_id or current['status'] != 'RUNNING'
                or store.get_spec_revision() != job['spec_revision'])

    def emit(event):
        nonlocal job
        if cancelled():
            raise ValueError('规划任务已取消或配置已变化')
        kind = event['event']
        if kind == 'hermes_run_admitted':
            job['run_id'] = event['run_id']
        if kind == 'hermes_run_completed':
            job['usage'] = dict(event.get('usage', {}))
        data = event.get('data') if kind == 'activity' else {'event': kind, 'text': {'started': '规划 Agent 正在设计整卷蓝图'}.get(kind, kind)}
        append_activity(job, 'plan', 'planner', 0, data or {}, job.get('run_id'))
        job = repo.replace(job, job['version'])

    try:
        emit({'event': 'started'})
        result = (adapter or QuestionService.get_adapter()).run_stage(RunRequest(
            task_ref=ref, provider='deepseek', model_id=settings.deepseek_model_id, role='planner',
            input_payload=planning_input(job['spec_snapshot'], job['skeleton']), schema_name='blueprint-design',
            skill_bundle_hash=hashlib.sha256((ROOT / 'skills/exam-planner/SKILL.md').read_bytes()).hexdigest(),
            policy_hash=hashlib.sha256((ROOT / 'configs/business-policy.example.yaml').read_bytes()).hexdigest(),
            max_iterations=1, deadline_utc=(datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat(),
            capability_grant_ref='isolated-local-generation'), emit, cancelled)
        job['usage'] = dict(result.usage)
        if result.status == 'CANCELLED':
            current = repo.get('planning:current')
            if current and current['job_id'] == job_id and current.get('stop_requested'):
                current.update(status='CANCELLED', usage=dict(result.usage))
                repo.replace(current, current['version'])
                return
        if result.status != 'SUCCEEDED' or result.payload is None:
            job['status'] = 'RECONCILING' if result.status in {'UNKNOWN', 'TIMED_OUT'} else 'FAILED'
            job['error'] = result.error_code or result.status
            repo.replace(job, job['version'])
            return
        plan = bind_design(job['skeleton'], result.payload, {'task_ref': ref, 'run_id': job.get('run_id'),
            'model_id': settings.deepseek_model_id, 'usage': job['usage']})
        repo.commit_plan(job, plan)
    except ValueError as exc:
        current = repo.get('planning:current')
        if current and current['job_id'] == job_id and current['status'] == 'RUNNING':
            current.update(status='FAILED', error=str(exc)[:1200])
            repo.replace(current, current['version'])
    except Exception:
        current = repo.get('planning:current')
        if current and current['job_id'] == job_id and current['status'] == 'RUNNING':
            current.update(status='RECONCILING', error='规划执行结果未知，请核对已保存的调用记录，不会自动重发')
            repo.replace(current, current['version'])
