"""Read-only, task-scoped completion gate for development records."""
from __future__ import annotations

import hashlib
from pathlib import Path
from tools.bug_workflow import bug_finish_issues

from tools.memory_lib import (RecordError, evidence_state, file_snapshot, git_snapshot, keyed,
                              latest_handoffs, load_records, matched, read_data, record_metadata_path,
                              safe_path, status_markdown, task_paths)


def accepted_application_report(root: Path, task_id: str, task: dict,
                                actual: dict, refs: set[str], changed: list[str]) -> tuple[bool, str]:
    """Check a claimed independent application acceptance record, without signing it."""
    scope = set(task['source_files'] + task['target_files'])
    scope.update(p for p in changed if not record_metadata_path(p))
    expected = file_snapshot(root, sorted(scope))
    missing = [p for p in expected if p.startswith('[missing-pattern] ')]
    if missing:
        return False, '验收范围文件缺失：' + ', '.join(missing[:10])
    errors = []
    for ref in sorted(refs):
        if not ref.startswith('acceptance-runs/'):
            continue
        try:
            report = read_data(root, ref)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f'{ref}: 无法读取：{exc}')
            continue
        if report.get('report_kind') != 'application-acceptance-v1':
            continue
        if report.get('status') != 'PASS' or report.get('application_verified') is not True:
            errors.append(f'{ref}: 验收未通过或未验证应用')
        elif not isinstance(report.get('task_ids'), list) or task_id not in report['task_ids']:
            errors.append(f'{ref}: 未覆盖本任务')
        elif not isinstance(report.get('reviewer'), str) or not report['reviewer'].strip() or report['reviewer'] == actual.get('completed_by'):
            errors.append(f'{ref}: 缺独立 reviewer 或与 completed_by 相同')
        elif not report.get('environment') or not report.get('command') or not isinstance(report.get('not_run'), list):
            errors.append(f'{ref}: 缺环境、命令或未执行项记录')
        elif report.get('source_files') != expected:
            errors.append(f'{ref}: 受测 source_files 与当前内容不一致')
        else:
            return True, ref
    return False, '；'.join(errors[:3]) if errors else '缺少 application-acceptance-v1 报告'


def finish_check(root: Path, task_id: str, paths: list[str] | None = None) -> dict:
    ledger, work, plan, _, policy = load_records(root)
    tasks = keyed(plan['tasks'], 'task')
    if task_id not in tasks:
        raise RecordError('Unknown task id')
    features = [f for f in ledger['features'] if task_id in f['task_ids']]
    git = git_snapshot(root)
    changed = task_paths(root, task_id, git['changed_paths'])
    outside_count = len(git['changed_paths']) - len(changed)
    explicit = paths or []
    for path in explicit:
        safe_path(root, path)
    changed = sorted(set(changed + explicit))
    issues: list[str] = []
    if not features:
        issues.append('任务没有功能映射；先核对 progress/features.yaml')
    patterns = tasks[task_id]['source_files'] + tasks[task_id]['target_files']
    patterns += [p for f in features if f['task_ids'] == [task_id] for p in f['watch_paths']]
    patterns += policy['global_watch_paths']
    unmapped = [p for p in changed if not matched(p, patterns)]
    if unmapped:
        issues.append('变更路径未映射到任务或功能范围：' + ', '.join(unmapped[:20]))
    entries = latest_handoffs(root, task_id)
    handoff_ref = entries[0][0] if entries else None
    handoff = entries[0][1] if entries else {}
    if not handoff:
        issues.append('缺少本任务交接')
    else:
        if not handoff.get('completed') and not handoff.get('pending'):
            issues.append('最新交接没有据实填写 completed 或 pending')
        source_changed = [p for p in changed if not record_metadata_path(p)]
        if source_changed:
            files = handoff.get('files', {})
            uncovered = [p for p in source_changed if p not in files]
            stale = []
            for p in source_changed:
                if p not in files:
                    continue
                file = safe_path(root, p)
                if files[p] == 'DELETED':
                    if file.exists():
                        stale.append(p)
                elif not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != files[p]:
                    stale.append(p)
            if uncovered:
                issues.append('最新交接未覆盖本任务变更：' + ', '.join(uncovered[:20]))
            if stale:
                issues.append('最新交接文件快照已过期：' + ', '.join(stale[:20]))
        for ref in handoff.get('evidence_refs', []):
            safe_path(root, ref, must_exist=True)
    actual = work['tasks'].get(task_id, {})
    state = actual.get('status', 'NOT_STARTED')
    try:
        issues += bug_finish_issues(root, task_id, handoff, state, actual)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        issues.append('Bug 记录核对失败：' + str(exc))
    if changed and state == 'NOT_STARTED':
        issues.append('已有任务变更，但 work.yaml 未登记实际进度')
    if state == 'DONE':
        if not actual.get('completed_by') or not actual.get('completed_at'):
            issues.append('DONE 缺少完成身份或时间')
        if not handoff or not handoff.get('completed') or not handoff.get('evidence_refs'):
            issues.append('DONE 缺少已完成交接和证据引用')
        if not actual.get('evidence_refs'):
            issues.append('DONE 缺少 work.yaml 证据引用')
        elif not set(actual['evidence_refs']) & set(handoff.get('evidence_refs', [])):
            issues.append('DONE 的任务证据与最新交接没有共同引用')
        if any(f['kind'] == 'PRODUCT' for f in features):
            shared_refs = set(actual.get('evidence_refs', [])) & set(handoff.get('evidence_refs', []))
            accepted, reason = accepted_application_report(root, task_id, tasks[task_id], actual, shared_refs, changed)
            if not accepted:
                issues.append('产品任务 DONE 缺少可核对的独立应用验收：' + reason)
    evidence = {}
    for feature in features:
        name, reason = evidence_state(root, feature)
        evidence[feature['id']] = name
        if feature['implementation'] == 'IMPLEMENTED' and name != 'OFFLINE_PASS':
            issues.append(f'{feature["id"]} 已登记 IMPLEMENTED，但证据为 {name}：{reason}')
    current = safe_path(root, 'progress/current.md')
    if not current.exists() or current.read_text(encoding='utf-8') != status_markdown(root):
        issues.append('current.md 与账本不一致；账本更新后运行 status --write')
    return {'status': 'PASS' if not issues else 'FAIL', 'task_id': task_id,
            'task_status': state, 'changed_paths': changed,
            'outside_task_path_count': outside_count, 'latest_handoff': handoff_ref,
            'feature_evidence': evidence, 'issues': issues,
            'note': '只读记录检查；PASS 不等于产品验收或阶段签收'}
