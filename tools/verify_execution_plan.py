"""Validate written implementation assets only. No network or application execution.

All paths named target_files are future application deliverables. This validator
checks the completeness of the PLAN, not whether those deliverables are built.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import json
import yaml

ROOT = Path(__file__).resolve().parents[1]
METHODS = {'get','post','put','patch','delete','head','options'}
PHASES = ('M0','M1','M2','M3')

def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)

def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding='utf-8'))

def validate_task_graph(tasks: list[dict[str, Any]]) -> None:
    ids = [t['id'] for t in tasks]
    require(len(ids)==len(set(ids)), 'Duplicate task ID')
    by_id={t['id']:t for t in tasks}
    for t in tasks:
        require(t['phase'] in PHASES, f"Invalid phase: {t['id']}")
        require(t['id'].startswith(t['phase']+'-'), 'Task phase prefix mismatch')
        for dep in t['depends_on']:
            require(dep in by_id, f'Unknown dependency: {dep}')
            require(PHASES.index(by_id[dep]['phase'])<=PHASES.index(t['phase']), 'Dependency on later phase')
    visiting:set[str]=set(); visited:set[str]=set()
    def visit(task_id: str) -> None:
        require(task_id not in visiting, f'Cycle at {task_id}')
        if task_id in visited:return
        visiting.add(task_id)
        for dep in by_id[task_id]['depends_on']:visit(dep)
        visiting.remove(task_id); visited.add(task_id)
    for task_id in ids:visit(task_id)

def validate_case(case: dict[str, Any], task_ids: set[str]) -> None:
    require(case['status']=='NOT_RUN' and case['automation_implemented'] is False, 'Unexecuted case claims implementation')
    require(case['actual_result'] is None and case['executed_at'] is None and not case['evidence_refs'], 'Invented runtime evidence')
    require(len(case['steps'])>=4 and all(isinstance(x,str) and len(x)>10 for x in case['steps']), 'Insufficient implementation-level case steps')
    require(bool(case.get('cleanup')), 'Case cleanup missing')
    require(bool(case['implementation_tasks']) and set(case['implementation_tasks'])<=task_ids, 'Invalid case/task mapping')

def validate_execution(root: Path=ROOT) -> dict[str, Any]:
    plan=read_yaml(root/'execution/task-index.yaml'); tasks=plan['tasks']
    require(plan['document_version']=='1.3','Wrong plan version')
    require(len(tasks)==32,'Expected 32 task cards')
    validate_task_graph(tasks)
    by_id={t['id']:t for t in tasks}; ids=set(by_id)
    require([sum(t['phase']==p for t in tasks) for p in PHASES]==[6,9,9,8], 'Phase task counts differ')
    manual=(root/'docs/08_阶段开发执行手册.md').read_text(encoding='utf-8')
    master=(root/'deliverables/zhijuan_product_development_v1_3.md').read_text(encoding='utf-8')
    require(manual.strip() in master,'Full execution manual missing from master')
    for t in tasks:
        require(t['status']=='NOT_STARTED' and t['runtime_implemented'] is False, 'Task falsely claims implementation')
        for field in ['owner_role','reviewer_role','target_files','verification','failure_action','acceptance_refs','evidence_required']:
            require(bool(t.get(field)),f"Task {t['id']} missing {field}")
        require(len(t['implementation_steps'])>=4,f"Task {t['id']} needs ordered steps")
        for rel in t['source_files']:
            path=(root/rel).resolve()
            require(path.is_relative_to(root.resolve()) and path.is_file(), f'Missing bundled input: {rel}')
        require(t['id'] in manual and t['title'] in manual, 'Task absent from full manual')
        phase_doc=(root/f"execution/{t['phase']}_实施手册.md").read_text(encoding='utf-8')
        require(t['title'] in phase_doc, 'Task absent from phase manual')
        for step in t['implementation_steps']:
            require(step in manual and step in phase_doc,'Task steps drift from task index')
    cases=[]
    for scope in ('minimum','full'):
        cases.extend(read_yaml(root/f'acceptance/{scope}-cases.yaml')['cases'])
    require(len(cases)==47,'Case inventory differs')
    case_ids={c['id'] for c in cases}
    for c in cases:
        validate_case(c,ids)
        expected={t['id'] for t in tasks if c['id'] in t['acceptance_refs']}
        require(set(c['implementation_tasks'])==expected,'Case reverse mapping drift')
    for t in tasks:require(set(t['acceptance_refs'])<=case_ids,'Unknown acceptance reference')
    api=read_yaml(root/'contracts/openapi.yaml')
    actual={op['operationId']:(method.upper(),path) for path,item in api['paths'].items() for method,op in item.items() if method in METHODS}
    mapping=read_yaml(root/'execution/api-task-map.yaml')['operations']
    require(len(actual)==len(mapping)==25,'Expected 25 actual and mapped operations')
    require({x['operation_id'] for x in mapping}==set(actual),'API operation mapping incomplete')
    for m in mapping:
        require((m['method'],m['path'])==actual[m['operation_id']],'API method/path drift')
        require(bool(m['task_ids']) and set(m['task_ids'])<=ids,'API task mapping invalid')
        require(m['first_phase']==min((by_id[x]['phase'] for x in m['task_ids']), key=PHASES.index),'Wrong API first phase')
    public=json.loads((root/'contracts/public-question.schema.json').read_text(encoding='utf-8'))
    require(api['components']['schemas']['PlanSlot']['properties']['kind']['enum']==public['properties']['kind']['enum'],'PlanSlot/PublicQuestion kinds drift')
    links=read_yaml(root/'execution/traceability.yaml')['links']
    require(len(links)==32 and {x['task_id'] for x in links}==ids,'Traceability task coverage incomplete')
    for link in links:
        t=by_id[link['task_id']]
        require(link['case_ids']==t['acceptance_refs'] and link['source_files']==t['source_files'] and link['planned_outputs']==t['target_files'],'Traceability detail drift')
    return {'result':'PASS','scope':'written_execution_materials_only','task_cards':32,'api_operations':25,'case_definitions':47,'application_executed':False,'hermes_installed':False,'live_model_called':False}

if __name__=='__main__':
    print(json.dumps(validate_execution(),ensure_ascii=False,indent=2))
    print('NOT RUN: application build/startup, upstream installation, model calls, phase gates, G-MIN, G-FULL.')
