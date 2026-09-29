from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .memory_base import ID, IMPLEMENTATION, TASK_STATES, RecordError, digest, load_records, read_data, relative_name, safe_path
from .memory_local_evidence import historical_reference
from .memory_graph import closure, file_snapshot, graph_check, keyed

def evidence_scope(root: Path, ids: list[str]) -> dict:
    ledger, _, _, _, policy = load_records(root)
    by = keyed(ledger['features'], 'feature')
    selected = closure(set(ids), by)
    patterns = list(policy['global_watch_paths'])
    contracts = {}
    for fid in sorted(selected):
        f = by[fid]
        patterns += f['watch_paths']
        # Evidence pointer is excluded to avoid the report->ledger->report hash cycle.
        contracts[fid] = {k: v for k, v in f.items() if k != 'last_evidence'}
    return {'feature_ids': sorted(selected), 'feature_contract_hash': digest(contracts),
            'files': file_snapshot(root, patterns, policy['max_scope_files'])}


def evidence_state(root: Path, feature: dict) -> tuple[str, str]:
    ref = feature.get('last_evidence')
    if not ref:
        return 'NOT_RUN', '没有登记运行报告'
    try:
        report = read_data(root, ref)
        if report.get('report_kind') != 'offline-quality-v1':
            return 'INVALID', '不是受支持的离线证据格式；产品验收另查 acceptance-runs'
        ids = report.get('requested_features', [])
        if feature['id'] not in ids:
            return 'INVALID', '报告未覆盖本功能'
        results = report.get('results', [])
        rb = keyed(results, 'suite result')
        if report.get('overall') != 'PASS':
            return 'FAILED', '最近登记的运行未全部通过'
        if not feature['required_suites'] or not set(feature['required_suites']) <= rb.keys():
            return 'INCOMPLETE', '缺少功能要求的测试组'
        for sid in feature['required_suites']:
            r = rb[sid]
            if r.get('status') != 'PASS' or r.get('exit_code') != 0:
                return 'INCOMPLETE', '测试未执行或未通过'
            log_path = safe_path(root, r.get('log', ''), must_exist=True)
            if not log_path.is_file() or hashlib.sha256(log_path.read_bytes()).hexdigest() != r.get('log_sha256'):
                return 'INVALID', '日志缺失或字节指纹不一致'
            if r.get('unit_summary') and (r['unit_summary'].get('skipped', 0) or r['unit_summary'].get('tests_run', 0) < 1):
                return 'INCOMPLETE', '测试为空或被跳过'
        if report.get('scope_changed_during_run'):
            return 'STALE', '测试运行中相关文件发生变化'
        if report.get('scope') != evidence_scope(root, ids):
            return 'STALE', '相关文件、登记范围或依赖已变化，需要重测'
        return 'OFFLINE_PASS', '只代表登记范围的离线验证，不等于应用、真实模型或阶段验收'
    except (OSError, ValueError, KeyError, TypeError) as e:
        return 'INVALID', '证据不可核对：' + str(e)


def validate_memory(root: Path, strict_evidence: bool = False) -> dict:
    ledger, work, plan, catalog, policy = load_records(root)
    by = keyed(ledger['features'], 'feature')
    tasks = keyed(plan['tasks'], 'task')
    suites = keyed(catalog['suites'], 'suite')
    warnings = []
    for task in tasks.values():
        for field in ('depends_on', 'source_files', 'target_files', 'implementation_steps', 'acceptance_refs'):
            if not isinstance(task.get(field), list):
                raise RecordError('Task missing required list: '+field)
        if not task.get('title') or not task.get('failure_action') or task.get('phase') not in {'M0', 'M1', 'M2', 'M3'}:
            raise RecordError('Task needs phase/title/failure_action')
        for path in task['source_files']:
            safe_path(root, path, must_exist=True)
        for path in task['target_files']:
            safe_path(root, path)
    graph_check({tid: {'requires': t['depends_on']} for tid,t in tasks.items()})
    for f in by.values():
        if f.get('implementation') not in IMPLEMENTATION or f.get('kind') not in {'PRODUCT', 'DEVTOOL', 'REFERENCE'}:
            raise RecordError('Invalid feature implementation/kind')
        for name in ('task_ids', 'requires', 'watch_paths', 'implementation_paths', 'invariants', 'required_suites', 'limitations'):
            if not isinstance(f.get(name), list):
                raise RecordError(f'Missing list: {f["id"]}.{name}')
        if not set(f['task_ids']) <= tasks.keys() or not set(f['required_suites']) <= suites.keys():
            raise RecordError('Feature links to an unknown task or suite')
        if not f['watch_paths'] or not f['invariants']:
            raise RecordError('Feature must declare scope and protected behaviors')
        for p in f['watch_paths']:
            relative_name(p, pattern=True)
        for p in f['implementation_paths']:
            safe_path(root, p, must_exist=True)
        if f['implementation'] == 'IMPLEMENTED' and not f['implementation_paths']:
            raise RecordError('IMPLEMENTED needs existing implementation paths, not target path names')
        if f['last_evidence']:
            historical_reference(root, f['last_evidence'], warnings, strict=strict_evidence)
    graph_check(by)
    if work.get('stage_hint') not in {'M0', 'M1', 'M2', 'M3'} or work.get('recommended_next_task') not in tasks:
        raise RecordError('Invalid current stage or recommended next task')
    if not isinstance(work.get('tasks'), dict):
        raise RecordError('Actual work overlay must be an object')
    for tid, record in work['tasks'].items():
        if tid not in tasks or record.get('status') not in TASK_STATES:
            raise RecordError('Unknown actual task or task status')
        if record.get('status') == 'DONE':
            if not record.get('evidence_refs') or not record.get('completed_by') or not record.get('completed_at'):
                raise RecordError('DONE requires real evidence and completion attribution')
            for ref in record['evidence_refs']:
                historical_reference(root, ref, warnings, strict=strict_evidence)
            # No automatic human stage signature is produced by this structural check.
    for s in suites.values():
        if s.get('status') not in {'IMPLEMENTED', 'PLANNED'}:
            raise RecordError('Invalid suite status')
        if s['status'] == 'IMPLEMENTED':
            argv = s.get('argv')
            if not isinstance(argv, list) or len(argv) < 2 or argv[0] != '{python}' or s['mode'] != 'OFFLINE':
                raise RecordError('Only explicitly listed offline Python suites may run here')
            safe_path(root, argv[1], must_exist=True)
        elif s.get('argv'):
            raise RecordError('Planned suite must not masquerade as runnable')
        if not isinstance(s.get('timeout_seconds'), int) or not 1 <= s['timeout_seconds'] <= 600:
            raise RecordError('Invalid suite time limit')
    for ref in policy['always_read']:
        safe_path(root, ref, must_exist=True)
    for rule in read_data(root, 'quality/regression-map.yaml')['rules']:
        if rule['feature_id'] not in by or rule['suite_id'] not in suites:
            raise RecordError('Unknown regression mapping')
        for p in rule['actual_test_paths']:
            safe_path(root, p, must_exist=True)
        if rule['application_test_status'] == 'IMPLEMENTED' and not rule['actual_test_paths']:
            raise RecordError('Regression test claimed without a file')
    for f in by.values():
        state, reason = evidence_state(root, f)
        if f['implementation'] == 'IMPLEMENTED' and state != 'OFFLINE_PASS':
            warning = f'{f["id"]}: {state}: {reason}'
            if strict_evidence:
                raise RecordError(warning)
            warnings.append(warning)
    for p in sorted((root / 'progress/handoffs').glob('*.yaml')):
        h = read_data(root, p.relative_to(root).as_posix())
        if h.get('task_id') not in tasks or not ID.fullmatch(str(h.get('session_id', ''))):
            raise RecordError('Invalid handoff task/session')
        if not h.get('summary') or not h.get('next_action'):
            raise RecordError('Handoff needs summary and next action')
        for ref in h.get('evidence_refs', []):
            historical_reference(root, ref, warnings, strict=strict_evidence)
    return {'status': 'PASS', 'scope': 'record_structure_only', 'features': len(by),
            'actual_task_records': len(work['tasks']), 'warnings': warnings,
            'application_verified': False, 'remote_ci_activated': False}
