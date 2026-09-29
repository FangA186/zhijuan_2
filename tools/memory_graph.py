from __future__ import annotations

import fnmatch
import hashlib
from pathlib import Path
from typing import Any

from .memory_base import ID, RecordError, relative_name, safe_path, unsafe_name

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
