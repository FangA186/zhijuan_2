"""Bounded, local defect records shared by CLI and project dashboard."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from tools.memory_base import read_data, safe_path

BUG_ID = re.compile(r"BUG-\d{8}-\d{3}$")
STATUSES = {"OPEN": "待处理", "FIXED": "已修复", "REOPENED": "复发"}


def fingerprint(record):
    return hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def notion_url(value):
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and parsed.hostname in {"www.notion.so", "notion.so", "app.notion.com"}


def validate_record(root, record, path):
    if not BUG_ID.fullmatch(str(record.get("id", ""))) or Path(path).stem != record["id"]:
        raise ValueError(f"{path}: Bug ID 与文件名不匹配")
    for key in ("title", "module", "symptom", "updated_at"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f"{path}: 缺少 {key}")
    if record.get("status") not in STATUSES:
        raise ValueError(f"{path}: 无效状态")
    for key in ('root_cause', 'resolution', 'verified_at', 'verification'):
        if key in record and not isinstance(record[key], str):
            raise ValueError(f"{path}: {key} 必须为文本")
    for key in ("task_ids", "keywords", "reproduction", "affected_files", "regression", "evidence_refs", "events"):
        values = record.get(key)
        if not isinstance(values, list) or any(not isinstance(x, str) or not x.strip() for x in values):
            raise ValueError(f"{path}: {key} 必须是文本列表")
    for ref in record["affected_files"] + record["evidence_refs"]:
        safe_path(root, ref)
    if record["status"] == "FIXED":
        for key in ("root_cause", "resolution", "verified_at", "verification"):
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise ValueError(f"{path}: 已修复必须填写 {key}")
        for key in ('task_ids', 'keywords', 'reproduction', 'affected_files', 'regression', 'evidence_refs', 'events'):
            if not record[key]:
                raise ValueError(f"{path}: 已修复必须填写 {key}")
    hashes = record.get('source_hashes', {})
    if not isinstance(hashes, dict):
        raise ValueError(f"{path}: source_hashes 必须为路径到指纹的对象")
    for ref, value in hashes.items():
        safe_path(root, ref)
        if Path(ref).parts[0] not in {'apps', 'services', 'tools', 'tests', 'reference_code'}:
            raise ValueError(f"{path}: 只对自有代码记录源码指纹")
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"{path}: 源码指纹无效")


def load_bugs(root, check_evidence=False):
    root = root.resolve()
    records = []
    directory = safe_path(root, "progress/bugs")
    if directory.is_dir():
        for path in sorted(directory.glob("BUG-*.yaml")):
            rel = path.relative_to(root).as_posix()
            record = read_data(root, rel)
            validate_record(root, record, rel)
            if check_evidence and record['status'] == 'FIXED':
                for ref in record['evidence_refs']:
                    safe_path(root, ref, must_exist=True)
            records.append(record)
    return records


def search_bugs(records, query="", task=None, paths=()):
    terms = query.lower().split()
    scored = []
    for bug in records:
        haystack = json.dumps(bug, ensure_ascii=False).lower()
        score = sum(term in haystack for term in terms)
        score += 4 if task and task in bug["task_ids"] else 0
        score += sum(any(p == ref or p.startswith(ref.rstrip("/") + "/") or
                         ref.startswith(p.rstrip("/") + "/") for ref in bug["affected_files"]) for p in paths)
        if score or not (terms or task or paths):
            scored.append((score, bug))
    return [b for _, b in sorted(scored, key=lambda pair: (-pair[0], pair[1]["id"]))]


def bug_snapshot(root):
    records = load_bugs(root)
    config_path = safe_path(root, "progress/bugs/notion-sync.json")
    config = read_data(root, "progress/bugs/notion-sync.json") if config_path.exists() else {}
    pages = config.get("pages", {})
    items = []
    for bug in records:
        sync = pages.get(bug["id"], {})
        url = sync.get("url", "")
        synced = notion_url(url) and sync.get("content_hash") == fingerprint(bug)
        hashes = bug.get("source_hashes", {})
        unchanged = bool(hashes) and all(safe_path(root, p).is_file() and
            hashlib.sha256(safe_path(root, p).read_bytes()).hexdigest() == sha for p, sha in hashes.items())
        items.append({**bug, "path": f"progress/bugs/{bug['id']}.yaml",
                      "evidence_available": all(safe_path(root, p).is_file() for p in bug['evidence_refs']),
                      "notion_url": url if notion_url(url) else "",
                      "sync_status": "已同步" if synced else "待同步",
                      "source_state": "记录后相关文件未变" if unchanged else "当前代码需重新核对"})
    database = config.get("database_url", "")
    return {"items": items, "database_url": database if notion_url(database) else ""}
