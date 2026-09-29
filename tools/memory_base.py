from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
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
