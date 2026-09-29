"""Fast admission and read-only progress for a single bounded planner call."""
import copy
from uuid import uuid4
from services.api.planning_repository import PlanningRepository
from services.api.store import store
from services.blueprint.generator import BlueprintGenerator
from .job_contracts import _now
from .job_service import GenerationJobService


class PlanningService:
    @staticmethod
    def current(repository=None):
        return (repository or PlanningRepository()).get('planning:current')

    @staticmethod
    def public(job):
        if not job:
            return None
        return {k: copy.deepcopy(job[k]) for k in ('job_id', 'status', 'spec_revision', 'version',
            'updated_at', 'activity', 'error', 'result', 'usage', 'request_key') if k in job}

    @staticmethod
    def start(request_key, expected_revision, repository=None):
        repo = repository or PlanningRepository()
        old = repo.get('planning:current')
        if old and (old.get('request_key') == request_key or old['status'] in {'QUEUED', 'RUNNING', 'RECONCILING'}):
            if old['spec_revision'] != expected_revision:
                raise ValueError('旧规划任务尚未结束或待对账，请先核对执行记录')
            return old  # Lost HTTP replies and repeated clicks never duplicate a paid call.
        if store.get_spec_revision() != expected_revision:
            raise ValueError('配置版本已变化，请重新加载')
        spec = store.get_canonical_spec()
        current = store.get_blueprint()
        skeleton = BlueprintGenerator.generate(spec, revision=int(current.get('revision', 0)) + 1,
                                               spec_revision=expected_revision)
        if spec.get('provided_materials') or any(s['kind'] == 'material_group' for s in skeleton['slots']):
            raise ValueError('共享材料规划暂未接通，不能直接开始模型调用')
        if not GenerationJobService.runtime_readiness().get('ready'):
            raise ValueError('规划服务尚未就绪，请检查 Hermes、Worker 和预算服务')
        return repo.admit({'job_id': str(uuid4()), 'exam_id': 'planning:current', 'job_kind': 'planning',
            'status': 'QUEUED', 'version': 1, 'updated_at': _now(), 'started_at': None,
            'spec_revision': expected_revision, 'spec_snapshot': spec, 'skeleton': skeleton,
            'base_plan_hash': current.get('plan_hash'), 'request_key': request_key,
            'activity': [], 'usage': {}, 'max_calls': 1})
