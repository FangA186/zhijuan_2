from __future__ import annotations

import subprocess
from pathlib import Path

from .memory_base import RecordError, load_records, relative_name
from .memory_graph import closure, keyed, matched

def git_run(root: Path, args: list[str], *, required: bool = True) -> bytes:
    try:
        p = subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        if required:
            raise RecordError('Git is unavailable or timed out') from e
        return b''
    if p.returncode and required:
        raise RecordError('Git query failed; check repository and base reference (no automatic fetch)')
    return p.stdout if p.returncode == 0 else b''


def git_snapshot(root: Path, base: str | None = None) -> dict:
    top = git_run(root, ['rev-parse', '--show-toplevel'], required=False).decode(errors='replace').strip()
    if not top:
        if base:
            raise RecordError('Cannot compare base without a Git repository')
        return {'state': 'NO_GIT', 'head': None, 'branch': None, 'base': None, 'changed_paths': [],
                'hidden_path_count': 0, 'notice': '只有交付文件快照，不能声称已核对 Git 历史'}
    if Path(top).resolve() != root.resolve():
        raise RecordError('Run at the project Git root; enclosing repository is not assumed to be this project')
    head = git_run(root, ['rev-parse', '--verify', 'HEAD'], required=False).decode().strip() or None
    branch = git_run(root, ['symbolic-ref', '--short', '-q', 'HEAD'], required=False).decode().strip() or 'DETACHED'
    paths: set[str] = set()
    queries = [['diff', '--no-ext-diff', '--name-only', '--no-renames', '-z', '--'],
               ['diff', '--no-ext-diff', '--cached', '--name-only', '--no-renames', '-z', '--'],
               ['ls-files', '--others', '--exclude-standard', '-z']]
    resolved_base = None
    if base:
        if not head or not isinstance(base, str) or base.startswith('-'):
            raise RecordError('Invalid base reference')
        resolved_base = git_run(root, ['rev-parse', '--verify', '--end-of-options', base+'^{commit}']).decode().strip()
        merge_base = git_run(root, ['merge-base', resolved_base, head]).decode().strip()
        queries.append(['diff', '--no-ext-diff', '--name-only', '--no-renames', '-z', merge_base, head, '--'])
    for q in queries:
        paths.update(x.decode('utf-8', errors='replace') for x in git_run(root, q).split(b'\x00') if x)
    visible, hidden = [], 0
    for rel in sorted(paths):
        try:
            visible.append(relative_name(rel))
        except RecordError:
            hidden += 1
    return {'state': 'GIT', 'head': head, 'branch': branch, 'base': resolved_base,
            'changed_paths': visible, 'hidden_path_count': hidden,
            'notice': '包含暂存、未暂存与未跟踪路径；有 --base 时加共同祖先到 HEAD 的改动。未读取 diff 正文。'}


def impact(root: Path, paths: list[str], task_id: str | None = None) -> dict:
    ledger, _, plan, catalog, policy = load_records(root)
    by, tasks, suites = keyed(ledger['features']), keyed(plan['tasks']), keyed(catalog['suites'])
    if task_id and task_id not in tasks:
        raise RecordError('Unknown task id')
    direct = {fid for fid, f in by.items() if matched_any(paths, f['watch_paths'])}
    task_features = {fid for fid, f in by.items() if task_id in f['task_ids']} if task_id else set()
    direct |= task_features
    global_change = matched_any(paths, policy['global_watch_paths'])
    affected = set(by) if global_change else closure(direct, by, reverse=True)
    unknown = [p for p in paths if not any(matched(p, f['watch_paths']) for f in by.values()) and not matched(p, policy['global_watch_paths'])]
    desired = {s for fid in affected for s in by[fid]['required_suites']}
    if unknown or global_change:
        desired |= {s['id'] for s in suites.values() if s['mode'] == 'OFFLINE' and s['status'] == 'IMPLEMENTED'}
    return {'direct_features': sorted(direct), 'affected_features': sorted(affected),
            'global_change': global_change, 'unmapped_paths': unknown,
            'manual_review_paths': [p for p in paths if matched(p, policy['manual_review_paths'])],
            'runnable_suites': sorted(s for s in desired if suites[s]['status'] == 'IMPLEMENTED'),
            'not_implemented_suites': sorted(s for s in desired if suites[s]['status'] != 'IMPLEMENTED'),
            'warning': '显式路径与依赖的辅助结果，不是完整影响证明；未映射变化须人工补充，不能当成无影响。'}


def matched_any(paths: list[str], patterns: list[str]) -> bool:
    return any(matched(p, patterns) for p in paths)


def task_paths(root: Path, task_id: str, paths: list[str]) -> list[str]:
    """Keep task context and handoff snapshots on the declared task/feature scope."""
    ledger, _, plan, _, policy = load_records(root)
    tasks = keyed(plan['tasks'], 'task')
    if task_id not in tasks:
        raise RecordError('Unknown task id')
    task = tasks[task_id]
    patterns = task['source_files'] + task['target_files']
    for feature in ledger['features']:
        if feature['task_ids'] == [task_id]:
            patterns += feature['watch_paths']
    patterns += policy['global_watch_paths']
    return sorted(p for p in paths if matched(p, patterns))


def record_metadata_path(path: str) -> bool:
    return (path.startswith('acceptance-runs/') or
            path in {'progress/features.yaml', 'progress/work.yaml', 'progress/extra-tasks.yaml',
                     'progress/current.md'} or
            path.startswith('progress/generated/') or
            (path.startswith('progress/handoffs/') and path.endswith('.yaml')))
