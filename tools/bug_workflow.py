"""Bug lookup receipts and completion checks; never calls external services."""
import json
from datetime import datetime

from tools.bug_records import bug_snapshot, load_bugs, search_bugs
from tools.memory_base import ID, atomic_replace, load_records, now, read_data, safe_path


def receipt_path(task):
    if not ID.fullmatch(task):
        raise ValueError("无效任务 ID")
    return f"progress/generated/bug-search/{task}.json"


def previous_session(root, task, current=None):
    from tools.memory_context import handoff_time
    entries = []
    for path in (root / 'progress/handoffs').glob('*.yaml'):
        record = read_data(root, path.relative_to(root).as_posix())
        if record.get('task_id') != task or record.get('session_id') == current:
            continue
        stamp = handoff_time(record.get('created_at'))
        entries.append((stamp, record['session_id']))
    return max(entries)[1] if entries else None


def lookup(root, query, task=None):
    if not query.strip():
        raise ValueError("请填写症状、报错或模块关键词")
    records = search_bugs(load_bugs(root), query)
    receipt = None
    if task:
        _, _, plan, _, _ = load_records(root)
        if task not in {t["id"] for t in plan["tasks"]}:
            raise ValueError("请先登记有效任务 ID")
        receipt = receipt_path(task)
        value = {"task_id": task, "query": query, "created_at": now(),
                 "matches": [b["id"] for b in records], "base_session": previous_session(root, task)}
        atomic_replace(root, receipt, json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    return {"matches": [{k: b.get(k) for k in ("id", "title", "status", "root_cause", "resolution", "affected_files", "regression")} for b in records],
            "receipt": receipt, "note": "匹配只是线索；先核对当前调用链、适用版本与失败复现。"}


def context_bugs(root, task, paths):
    found = search_bugs(load_bugs(root), task=task, paths=paths)[:5]
    return ["", "## 相关 Bug 记忆（历史修复不是当前验收）", *[
        f"- {b['id']} [{b['status']}] {b['title']} → progress/bugs/{b['id']}.yaml" for b in found],
        "修 Bug 前运行 bug_memory.py search --task <任务ID> --query '<症状 关键词>'，未命中也保留检索记录。"]


def bug_finish_issues(root, task, handoff, state, actual):
    receipt = receipt_path(task)
    ids = handoff.get("bug_ids", [])
    marked = bool(ids) or actual.get("work_type") == "BUGFIX"
    exists = safe_path(root, receipt).exists()
    if not marked and not exists:
        return []
    issues = []
    if not exists:
        issues.append("Bug 修复缺少修前检索记录：先运行 bug_memory.py search --task")
    else:
        search = read_data(root, receipt)
        try:
            datetime.fromisoformat(search.get("created_at", ""))
            valid = search.get("task_id") == task and bool(search.get("query", "").strip())
        except (ValueError, TypeError):
            valid = False
        if not valid:
            issues.append("Bug 检索记录无效")
        elif search.get('base_session') != previous_session(root, task, handoff.get('session_id')):
            issues.append('Bug 检索记录早于上一检查点；本次修复需要重新检索')
    if not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids):
        return issues + ["Bug 修复交接必须填写 bug_ids"]
    bugs = {b["id"]: b for b in bug_snapshot(root)["items"]}
    for bug_id in ids:
        bug = bugs.get(bug_id)
        if not bug or task not in bug["task_ids"]:
            issues.append(f"{bug_id} 不存在或未关联本任务")
        elif state == "DONE":
            if bug["status"] != "FIXED":
                issues.append(f"{bug_id} 尚未修复，任务不能 DONE")
            if bug["sync_status"] != "已同步":
                issues.append(f"{bug_id} 尚未回读并登记 Notion 同步")
            if not bug['evidence_available']:
                issues.append(f"{bug_id} 验证证据文件缺失")
    return issues
