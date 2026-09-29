"""Prepare small, explicit Bug page payloads; MCP writes are performed by the agent."""
import json

from tools.bug_records import fingerprint, load_bugs, notion_url, STATUSES
from tools.memory_base import atomic_replace, now, read_data, safe_path

SYNC_PATH = "progress/bugs/notion-sync.json"


def content(bug):
    lines = [f"本地记录：`progress/bugs/{bug['id']}.yaml`",
             "历史修复记录；重用前核对当前代码和复现条件。", "## 症状", bug["symptom"]]
    for title, key in (("复现", "reproduction"), ("根因", "root_cause"), ("修复方法", "resolution"),
                       ("代码位置", "affected_files"), ("回归检查", "regression"),
                       ("验证证据", "evidence_refs"), ("发生与修复历史", "events")):
        value = bug.get(key)
        lines += [f"## {title}"]
        lines += ["- " + v for v in value] if isinstance(value, list) else [value or "待查明"]
    lines += ["## 证据边界", f"{bug.get('verified_at') or '未验证'} · {bug.get('verification') or 'NOT_RUN'}",
              "Notion 是本地记录的展示副本。网页和已修复标签不会自动证明当前产品通过。"]
    return "\n".join(lines)


def export_pages(root):
    sync = read_data(root, SYNC_PATH) if safe_path(root, SYNC_PATH).exists() else {}
    pages = []
    for bug in load_bugs(root):
        previous = sync.get("pages", {}).get(bug["id"], {})
        sha = fingerprint(bug)
        if previous.get("content_hash") == sha and notion_url(previous.get("url", "")):
            continue
        pages.append({"bug_id": bug["id"], "content_hash": sha, "existing_url": previous.get("url"),
                      "properties": {"名称": f"{bug['id']} · {bug['title']}", "状态": STATUSES[bug["status"]],
                                     "模块": bug["module"], "任务": ", ".join(bug["task_ids"]),
                                     "关键词": ", ".join(bug["keywords"]),
                                     "本地路径": f"progress/bugs/{bug['id']}.yaml"},
                      "content": content(bug)})
    return {"data_source_id": sync.get("data_source_id"), "pages": pages}


def mark_synced(root, bug_id, url, expected_hash):
    bugs = {b["id"]: b for b in load_bugs(root)}
    if bug_id not in bugs or fingerprint(bugs[bug_id]) != expected_hash:
        raise ValueError("本地记录已变化或 ID 不存在，需重新导出并同步")
    if not notion_url(url):
        raise ValueError("需登记回读成功的 Notion 页面 URL")
    sync = read_data(root, SYNC_PATH)
    sync.setdefault("pages", {})[bug_id] = {"url": url, "content_hash": expected_hash, "synced_at": now()}
    atomic_replace(root, SYNC_PATH, json.dumps(sync, ensure_ascii=False, indent=2) + "\n")
