from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any
import yaml

from .memory_base import ID, RecordError, atomic_replace, digest, load_records, now, read_data, safe_path, write_new
from .memory_evidence import evidence_scope, evidence_state
from .memory_git import git_snapshot, impact, record_metadata_path, task_paths
from .memory_graph import file_snapshot, keyed
from .bug_workflow import context_bugs

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
    return sorted(entries, key=lambda x: handoff_time(x[1].get('created_at')), reverse=True)[:3]


def handoff_time(value: object) -> datetime:
    """Order handoffs by instant; existing timezone-less dates are UTC."""
    try:
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else None
        if parsed:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
    except ValueError:
        pass
    return datetime.min.replace(tzinfo=timezone.utc)


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
    scoped = task_paths(root, task_id, git['changed_paths'])
    git['outside_task_path_count'] = len(git['changed_paths']) - len(scoped)
    git['changed_paths'] = scoped
    imp = impact(root, git['changed_paths'], task_id)
    features = keyed(ledger['features'])
    warnings = [git['notice'], imp['warning'], '本包只新增开发工具；生成上下文不等于执行任务或验收通过。']
    if git['state'] != 'GIT':
        warnings.append('NO_GIT：没有提交证据，须人工核对现场。')
    if git['hidden_path_count']:
        warnings.append(f'{git["hidden_path_count"]} 个敏感/不规范路径仅计数，未显示。不要把密钥传给模型。')
    if git['outside_task_path_count']:
        warnings.append(f'{git["outside_task_path_count"]} 个路径不在本任务声明范围内；若相关，先补映射或用 finish --path 明确核对。')
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
    lines += context_bugs(root, task_id, task['source_files'] + task['target_files'])
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
    scoped = task_paths(root, task_id, git['changed_paths'])
    git['outside_task_path_count'] = len(git['changed_paths']) - len(scoped)
    git['changed_paths'] = scoped
    patterns = task['source_files'] + task['target_files'] + git['changed_paths']
    # Snapshot does not include generated/handoff/evidence metadata to avoid self-reference.
    patterns = sorted({p for p in patterns if not record_metadata_path(p)})
    files = file_snapshot(root, patterns)
    for path in scoped:
        if not record_metadata_path(path) and not safe_path(root, path).exists():
            files[path] = 'DELETED'
    value = dict(schema_version=1, task_id=task_id, session_id=session, created_at=now(),
                 git=git, summary=redact(summary), next_action=redact(next_action),
                 completed=[], pending=[], decisions=[], failed_approaches=[], evidence_refs=refs,
                 scope_patterns=patterns, files=files,
                 note='此命令只创建交接框架和现场快照；completed 等由执行者据实填写，不自动变更任务状态。')
    rel = f'progress/handoffs/{task_id}--{session}.yaml'
    return write_new(root, rel, yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=100))
