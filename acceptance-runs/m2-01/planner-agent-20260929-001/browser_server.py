"""Isolated HTTP/PostgreSQL browser acceptance. Hermes is an explicit fixture."""
import json
import threading
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.api.routes.exams import router
from services.api.planning_repository import PlanningRepository
from services.api.store import store
from services.exam.job_service import GenerationJobService
from services.blueprint.generator import BlueprintGenerator
from services.worker.planning import run_planning
from reference_code.adapter_contract import RunResult
import services.api.routes.exams as exams

repo = PlanningRepository()
with repo.psycopg.connect(repo.dsn) as conn:
    assert conn.execute('SELECT current_database()').fetchone()[0] == 'planner_test'
    for table in ['generation_jobs', 'generation_job_outbox', 'generation_exam_state', 'generation_exam_revisions', 'generation_job_history']:
        conn.execute(f'DELETE FROM {table}')
spec = json.loads(Path('acceptance-runs/m2-01/topic-diversity-20260928-001/preview.json').read_text())['canonical_spec']
store._load()
store._store_version = 0
store.update_spec(spec)
GenerationJobService.runtime_readiness = staticmethod(lambda: {'ready': True})
exams.generation_configuration = lambda: {'configured': True}


class FixtureAdapter:
    def run_stage(self, request, emit, cancelled):
        emit({'event': 'hermes_run_admitted', 'run_id': 'run_offline_planner_fixture'})
        for text in ['【离线验收夹具】规划角色已受理。\n', '正在检查整卷结构、范围与难度配额。\n', '设计完成，交给确定性检查器校验。\n']:
            time.sleep(2)
            if cancelled():return RunResult('CANCELLED', None, (), {}, 'cancelled_fixture')
            emit({'event': 'activity', 'data': {'event': 'message.delta', 'delta': text}})
        skeleton = BlueprintGenerator.generate(spec)
        design = {'summary': '【离线合成结果】验证规划角色的输出、持久化、刷新恢复与教师确认流程；不是 DeepSeek 实际教学设计。', 'conflicts': [], 'slots': []}
        for s in skeleton['slots']:
            design['slots'].append({'slot_id': s['slot_id'], 'knowledge_ids': s['knowledge_ids'], 'difficulty': s['estimated_difficulty'],
                'cognitive_target': '概念应用', 'design_brief': f"第{s['order']}题围绕{s['target_topic']}安排不同条件的分析任务。", 'rationale': '离线夹具验证设计字段传递'})
        emit({'event': 'activity', 'data': {'event': 'run.result', 'output': json.dumps(design, ensure_ascii=False)}})
        return RunResult('SUCCEEDED', design, (), {}, None)


def dispatch():
    while True:
        for id, job_id in repo.pending_dispatches():
            job = repo.get_by_job_id(job_id)
            if job and job.get('job_kind') == 'planning':
                repo.mark_dispatched(id)
                run_planning(job_id, repo, FixtureAdapter())
        time.sleep(.4)


app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['http://127.0.0.1:3001'], allow_methods=['*'], allow_headers=['*'], expose_headers=['ETag'])
app.include_router(router)
threading.Thread(target=dispatch, daemon=True).start()
