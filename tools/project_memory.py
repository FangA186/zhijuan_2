#!/usr/bin/env python3
"""CLI for project records, session handoff and bounded task context."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.memory_lib import (ROOT, RecordError, atomic_replace, context_markdown, create_handoff,
                              git_snapshot, impact, relative_name, safe_path, status_markdown,
                              validate_memory, write_new)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='project root; defaults to script repository')
    subs = parser.add_subparsers(dest='command', required=True)
    check = subs.add_parser('check', help='check record consistency, not product readiness')
    check.add_argument('--strict-evidence', action='store_true', help='also fail stale/missing evidence for implemented features')
    status = subs.add_parser('status', help='derive current.md from the records')
    status.add_argument('--write', action='store_true')
    status.add_argument('--check-current', action='store_true', help='fail if current.md is out of date')
    context = subs.add_parser('context', help='bounded task context; does not read source/diff bodies')
    context.add_argument('--task', required=True)
    context.add_argument('--base', help='optional local base commit/ref; never fetches automatically')
    context.add_argument('--max-chars', type=int, default=12000)
    context.add_argument('--out', help='new file under progress/generated/; existing file not overwritten')
    diff = subs.add_parser('impact', help='path/dependency impact hints; not a semantic proof')
    diff.add_argument('--task')
    diff.add_argument('--base')
    diff.add_argument('--path', action='append', default=[], help='explicit changed path; may be repeated')
    handoff = subs.add_parser('handoff', help='create a new task/session record without overwrite')
    handoff.add_argument('--task', required=True)
    handoff.add_argument('--session', required=True)
    handoff.add_argument('--summary', required=True)
    handoff.add_argument('--next', dest='next_action', required=True)
    handoff.add_argument('--evidence', action='append', default=[])
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == 'check':
            print(json.dumps(validate_memory(root, args.strict_evidence), ensure_ascii=False, indent=2))
        elif args.command == 'status':
            text = status_markdown(root)
            p = safe_path(root, 'progress/current.md')
            if args.check_current and (not p.exists() or p.read_text(encoding='utf-8') != text):
                raise RecordError('current.md is stale; run status --write and review the diff')
            if args.write:
                atomic_replace(root, 'progress/current.md', text)
                print('Updated progress/current.md (derived summary only).')
            elif not args.check_current:
                print(text)
        elif args.command == 'context':
            text = context_markdown(root, args.task, args.base, args.max_chars)
            if args.out:
                if not relative_name(args.out).startswith('progress/generated/'):
                    raise RecordError('Context output must stay under progress/generated/')
                p = write_new(root, args.out, text)
                print('Created '+p.relative_to(root).as_posix())
            else:
                print(text)
        elif args.command == 'impact':
            git = git_snapshot(root, args.base)
            paths = sorted(set(git['changed_paths'] + [relative_name(p) for p in args.path]))
            print(json.dumps({'git': git, 'changed_paths': paths, **impact(root, paths, args.task)}, ensure_ascii=False, indent=2))
        elif args.command == 'handoff':
            p = create_handoff(root, args.task, args.session, args.summary, args.next_action, args.evidence)
            print('Created '+p.relative_to(root).as_posix()+'. Fill evidence-based completion/blocked details; no task auto-approved.')
        return 0
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
