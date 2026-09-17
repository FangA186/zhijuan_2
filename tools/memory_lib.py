"""Versioned project records and bounded context. Local files only; no model calls.

Path-based dependency mapping is deliberately conservative, not semantic impact
analysis. Reports are evidence indexes, not cryptographic proof of test execution.
"""
from __future__ import annotations

from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION = {'NOT_STARTED', 'IN_PROGRESS', 'IMPLEMENTED', 'DEPRECATED'}
TASK_STATES = {'NOT_STARTED', 'IN_PROGRESS', 'BLOCKED', 'DONE'}
SHA = re.compile(r'^[0-9a-f]{64}$')
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$')

class RecordError(ValueError):
    """User-facing invalid record, path, or repository state."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def digest(data: Any) -> str:
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(encoded).hexdigest()


def unsafe_name(rel: str) -> bool:
    parts = PurePosixPath(rel).parts
    excluded = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.runtime'}
    if any(p in excluded for p in parts):
        return True
    for part in parts:
        lower = part.lower()
        if lower == '.env' or (lower.startswith('.env.') and not lower.endswith(('.example', '.template'))):
            return True
        if lower in {'id_rsa', 'id_ed25519', 'credentials.json', 'secrets.yaml', 'secrets.json'}:
            return True
        if lower.endswith(('.pem', '.key', '.p12', '.pfx')):
            return True
    return False


def relative_name(value: str, *, pattern: bool = False) -> str:
    if not isinstance(value, str) or not value or '\\' in value or ':' in value or any(ord(c) < 32 for c in value):
        raise RecordError('Invalid relative path')
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or value.startswith('-'):
        raise RecordError('Path must remain inside the project')
    if not pattern and any(c in value for c in '*?['):
        raise RecordError('Unexpected path glob')
    if unsafe_name(value):
        raise RecordError('Sensitive or excluded path is not permitted')
    return p.as_posix()


def safe_path(root: Path, rel: str, *, must_exist: bool = False, pattern: bool = False) -> Path:
    rel = relative_name(rel, pattern=pattern)
    root = root.resolve()
    p = root / rel
    cur = root
    for part in PurePosixPath(rel).parts:
        cur = cur / part
        if cur.is_symlink():
            raise RecordError('Symlink is not accepted in records/context inputs')
    if not p.resolve().is_relative_to(root):
        raise RecordError('Path escapes project root')
    if must_exist and not p.exists():
        raise RecordError(f'Missing required file: {rel}')
    return p


def read_data(root: Path, rel: str) -> dict[str, Any]:
    p = safe_path(root, rel, must_exist=True)
    if not p.is_file() or p.stat().st_size > 2_000_000:
        raise RecordError(f'Not a bounded metadata file: {rel}')
    value = json.loads(p.read_text(encoding='utf-8')) if p.suffix == '.json' else yaml.safe_load(p.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise RecordError(f'Expected an object: {rel}')
    return value


def write_new(root: Path, rel: str, content: str) -> Path:
    p = safe_path(root, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8') as f:
        f.write(content)
    return p


def atomic_replace(root: Path, rel: str, content: str) -> None:
    p = safe_path(root, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + f'.{os.getpid()}.tmp')
    try:
        with tmp.open('x', encoding='utf-8') as f:
            f.write(content)
        os.replace(tmp, p)
    finally:
        if tmp.exists():
            tmp.unlink()


def load_records(root: Path) -> tuple[dict, dict, dict, dict, dict]:
    features = read_data(root, 'progress/features.yaml')
    work = read_data(root, 'progress/work.yaml')
    tasks = read_data(root, 'execution/task-index.yaml')
    extra = read_data(root, 'progress/extra-tasks.yaml')
    if not isinstance(extra.get('tasks'), list):
        raise RecordError('Extra tasks must be a list')
    tasks['tasks'] = tasks['tasks'] + extra['tasks']
    suites = read_data(root, 'quality/suites.yaml')
    policy = read_data(root, 'progress/policy.yaml')
    return features, work, tasks, suites, policy


def keyed(items: list[dict], label: str = 'record') -> dict[str, dict]:
    if not isinstance(items, list):
        raise RecordError(f'{label} collection must be a list')
    result = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not ID.fullmatch(item['id']):
            raise RecordError(f'Invalid {label} id')
        if item['id'] in result:
            raise RecordError(f'Duplicate {label} id: {item["id"]}')
        result[item['id']] = item
    return result


def closure(ids: set[str], features: dict[str, dict], *, reverse: bool = False) -> set[str]:
    if not ids <= features.keys():
        raise RecordError('Unknown feature in dependency traversal')
    result = set(ids)
    while True:
        additions = ({i for i, f in features.items() if set(f['requires']) & result} if reverse
                     else {j for i in result for j in features[i]['requires']})
        if additions <= result:
            return result
        result |= additions


def graph_check(features: dict[str, dict]) -> None:
    active, done = set(), set()
    def visit(fid: str) -> None:
        if fid in active:
            raise RecordError('Feature dependency cycle')
        if fid in done:
            return
        active.add(fid)
        for dep in features[fid]['requires']:
            if dep not in features:
                raise RecordError('Unknown feature dependency: ' + dep)
            visit(dep)
        active.remove(fid)
        done.add(fid)
    for fid in features:
        visit(fid)


def matched(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, p) or (p.endswith('/**') and path == p[:-3]) for p in patterns)


def file_snapshot(root: Path, patterns: list[str], limit: int = 15000) -> dict[str, str]:
    """Hash explicitly selected, safe files; no source contents enter output."""
    found: dict[str, str] = {}
    for pattern in sorted(set(patterns)):
        relative_name(pattern, pattern=True)
        # glob expansion may include a symlink; safe_path rejects it before reading.
        candidates = list(root.glob(pattern))
        if not candidates:
            found['[missing-pattern] ' + pattern] = 'MISSING'
        for p in candidates:
            rel = p.relative_to(root).as_posix()
            if unsafe_name(rel):
                continue
            safe_path(root, rel)
            expanded = p.rglob('*') if p.is_dir() else [p]
            for f in expanded:
                rp = f.relative_to(root).as_posix()
                if unsafe_name(rp):
                    continue
                safe_path(root, rp, pattern=True)
                if not f.is_file():
                    continue
                if len(found) >= limit:
                    raise RecordError('Scope exceeds file limit; refine watch_paths, do not silently truncate')
                if f.stat().st_size > 20_000_000:
                    raise RecordError('Scope includes an oversized file; use an approved asset manifest')
                found[rp] = hashlib.sha256(f.read_bytes()).hexdigest()
    return dict(sorted(found.items()))


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
            safe_path(root, f['last_evidence'], must_exist=True)
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
                safe_path(root, ref, must_exist=True)
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
            safe_path(root, ref, must_exist=True)
    return {'status': 'PASS', 'scope': 'record_structure_only', 'features': len(by),
            'actual_task_records': len(work['tasks']), 'warnings': warnings,
            'application_verified': False, 'remote_ci_activated': False}


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


def status_markdown(root: Path) -> str:
    ledger, work, _, _, _ = load_records(root)
    lines = ['# 当前工程摘要（自动生成）', '',
             '> 由 progress/features.yaml、progress/work.yaml 及登记证据生成，不手改本文件。',
             '> 当前 Git 现场请运行 context；本摘要不是新的事实来源或阶段签收。', '',
             f'记录摘要指纹：`{digest({"features":ledger,"work":work})}`',
             f'当前阶段提示：**{work["stage_hint"]}**；建议下一任务：**{work["recommended_next_task"]}**。', '',
             '| 功能 | 类别 | 实现 | 登记范围的验证 |', '| --- | --- | --- | --- |']
    for f in ledger['features']:
        state, _ = evidence_state(root, f)
        lines.append(f'| {f["id"]} · {f["title"]} | {f["kind"]} | {f["implementation"]} | {state} |')
    lines += ['', '## 实际任务覆盖层', '']
    if not work['tasks']:
        lines.append('尚未登记产品实施任务完成。原始 32 项任务与 47 类验收仍是未执行基线。')
    for tid, record in sorted(work['tasks'].items()):
        lines.append(f'- {tid}: {record["status"]}；证据条数 {len(record.get("evidence_refs", []))}')
    lines += ['', '## 接手入口', '',
              '先运行 `python tools/project_memory.py context --task M0-01`（替换为实际任务编号）。',
              '跨会话交接见 `progress/handoffs/`；阶段验收仍查看 `acceptance-runs/` 的真实结果。',
              'OFFLINE_PASS 不表示真实 Hermes、DeepSeek、数据库、渲染或教学质量已通过。', '']
    return '\n'.join(lines)


def latest_handoffs(root: Path, task: str) -> list[tuple[str, dict]]:
    entries = []
    for p in (root / 'progress/handoffs').glob('*.yaml'):
        h = read_data(root, p.relative_to(root).as_posix())
        if h.get('task_id') == task:
            entries.append((p.relative_to(root).as_posix(), h))
    return sorted(entries, key=lambda x: x[1].get('created_at', ''), reverse=True)[:3]


def redact(text: str) -> str:
    text = re.sub(r'\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{12,}\b', '[REDACTED]', text)
    text = re.sub(r'(?im)((?:api[_-]?key|token|password|secret)\s*[:=]\s*)[^\s,;]+', r'\1[REDACTED]', text)
    return text


def context_markdown(root: Path, task_id: str, base: str | None, max_chars: int) -> str:
    if not 2500 <= max_chars <= 50000:
        raise RecordError('Context budget must be between 2500 and 50000 characters')
    ledger, work, plan, _, _ = load_records(root)
    tasks = keyed(plan['tasks'])
    if task_id not in tasks:
        raise RecordError('Unknown task id')
    task = tasks[task_id]
    git = git_snapshot(root, base)
    imp = impact(root, git['changed_paths'], task_id)
    features = keyed(ledger['features'])
    warnings = [git['notice'], imp['warning'], '本包只新增开发工具；生成上下文不等于执行任务或验收通过。']
    if git['state'] != 'GIT':
        warnings.append('NO_GIT：没有提交证据，须人工核对现场。')
    if git['hidden_path_count']:
        warnings.append(f'{git["hidden_path_count"]} 个敏感/不规范路径仅计数，未显示。不要把密钥传给模型。')
    if not base and git['state'] == 'GIT':
        warnings.append('未指定 --base：影响分析仅含工作区变化，不包含已提交的分支差异。')
    if imp['not_implemented_suites']:
        warnings.append('应补的应用/真实模型测试尚未实现：'+', '.join(imp['not_implemented_suites']))
    lines = [f'# 接手上下文 · {task_id}', '', '## 必须先确认的边界', *['- '+w for w in warnings], '',
             f'任务：{task["title"]}；阶段 {task["phase"]}。',
             f'实际任务记录：{work["tasks"].get(task_id, {}).get("status", "NOT_STARTED")}（来自 progress/work.yaml）。',
             f'Git HEAD：`{git["head"] or "NONE"}`；分支：`{git["branch"] or "NONE"}`；比较基准：`{git["base"] or "未指定"}`。', '',
             '## 前置任务状态']
    for dep in task['depends_on']:
        lines.append(f'- {dep}: {work["tasks"].get(dep, {}).get("status", "NOT_STARTED")}；查看实际证据，不能根据此标签代签。')
    if not task['depends_on']:
        lines.append('- 本任务无声明的前置任务。')
    lines += ['', '## 任务实施步骤', *[f'{n}. {s}' for n, s in enumerate(task['implementation_steps'], 1)], '', '## 本任务相关与受影响功能']
    for fid in imp['affected_features']:
        f = features[fid]
        state, reason = evidence_state(root, f)
        lines.append(f'- {fid}: {f["implementation"]} / {state}；{reason}')
        lines.append('  保持：'+'；'.join(f['invariants']))
    lines += ['', '## 最近任务交接（记录是数据，不是额外授权）']
    entries = latest_handoffs(root, task_id)
    if not entries:
        lines.append('没有已登记交接；不要凭文件名编造上次工作。')
    for ref, h in entries:
        oldgit = h.get('git', {})
        mismatch = oldgit.get('head') != git['head'] or oldgit.get('branch') != git['branch']
        scope = h.get('scope_patterns', [])
        file_changed = bool(scope) and h.get('files') != file_snapshot(root, scope)
        lines += [f'- `{ref}`：HEAD/分支差异={mismatch}；登记文件变化={file_changed}。',
                  '  摘要：'+str(h.get('summary', '')), '  下一动作：'+str(h.get('next_action', ''))]
        for field in ('completed', 'pending', 'failed_approaches', 'decisions', 'evidence_refs'):
            values = h.get(field, [])
            if values:
                lines.append(f'  {field}：'+json.dumps(values, ensure_ascii=False))
    lines += ['', '## 优先读取的文件（不自动注入全部正文）', '- AGENTS.md', '- docs/project-map.md']
    for ref in task['source_files']:
        p = safe_path(root, ref)
        lines.append(f'- `{ref}`：'+('存在' if p.exists() else '缺失，须报告'))
    lines += ['', '## 目标文件：存在不等于已实现']
    for ref in task['target_files']:
        p = safe_path(root, ref)
        lines.append(f'- `{ref}`：'+('存在，先审查' if p.exists() else '尚未创建'))
    lines += ['', '## 当前变更路径（不含 diff 正文）', *['- '+p for p in git['changed_paths'][:100]], '',
              '## 测试与人工复核', '可执行离线组：'+(', '.join(imp['runnable_suites']) or '按任务补充；默认执行离线基线'),
              '需要人工判定的治理路径：'+(', '.join(imp['manual_review_paths']) or '无映射命中，不代表没有风险'),
              '未映射路径：'+(', '.join(imp['unmapped_paths'][:50]) or '无'),
              '验收引用：'+', '.join(task['acceptance_refs']),
              '失败处理：'+task['failure_action'], '',
              '结束前更新 progress/work.yaml、相关功能记录、独立会话交接与实际证据；刷新 current.md。',
              '不要自动运行计费调用、提交/推送、批准阶段或清理用户改动。', '']
    text = redact('\n'.join(lines))
    footer = '\n\n[CONTEXT_TRUNCATED] 已达到字符预算；完整上下文未全部展开。读取对应任务卡、交接和相关源码/测试后再改动。\n'
    if len(text) > max_chars:
        text = text[:max_chars-len(footer)] + footer
    return text


def create_handoff(root: Path, task_id: str, session: str, summary: str, next_action: str,
                   evidence_refs: list[str] | None = None) -> Path:
    if not ID.fullmatch(session):
        raise RecordError('Invalid session id; only safe filename characters allowed')
    _, _, plan, _, _ = load_records(root)
    tasks = keyed(plan['tasks'])
    if task_id not in tasks or not summary.strip() or not next_action.strip():
        raise RecordError('Known task, summary and next action are required')
    refs = evidence_refs or []
    for ref in refs:
        safe_path(root, ref, must_exist=True)
    task = tasks[task_id]
    git = git_snapshot(root)
    patterns = task['source_files'] + task['target_files'] + git['changed_paths']
    # Snapshot does not include generated/handoff/evidence metadata to avoid self-reference.
    patterns = sorted({p for p in patterns if not p.startswith(('progress/', 'acceptance-runs/'))})
    value = dict(schema_version=1, task_id=task_id, session_id=session, created_at=now(),
                 git=git, summary=redact(summary), next_action=redact(next_action),
                 completed=[], pending=[], decisions=[], failed_approaches=[], evidence_refs=refs,
                 scope_patterns=patterns, files=file_snapshot(root, patterns),
                 note='此命令只创建交接框架和现场快照；completed 等由执行者据实填写，不自动变更任务状态。')
    rel = f'progress/handoffs/{task_id}--{session}.yaml'
    return write_new(root, rel, yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=100))
