#!/usr/bin/env python3
"""Run named offline suites and save honest versioned evidence. No installs/live calls.

Only the checked-in suite catalog is executed. Review repository code before
running; shell=False is not a sandbox against malicious Python tests.
"""
from __future__ import annotations
import argparse
import hashlib
from importlib.metadata import version, PackageNotFoundError
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.memory_lib import (ROOT, RecordError, atomic_replace, evidence_scope, git_snapshot, keyed,
                              load_records, now, read_data, redact, safe_path, validate_memory, write_new)


def result_status(exit_code: int | None, summary: dict | None = None, timed_out: bool = False) -> str:
    if timed_out:
        return 'TIMED_OUT'
    if exit_code is None:
        return 'NOT_RUN'
    if exit_code != 0:
        return 'FAIL'
    if summary is not None and (summary.get('status') != 'PASS' or summary.get('tests_run', 0) < 1
                                or summary.get('skipped', 0) or summary.get('expected_failures', 0)):
        return 'FAIL'
    return 'PASS'


def run(root: Path, out: str, selections: list[str], features: list[str]) -> tuple[dict, int]:
    validate_memory(root)
    if not out.startswith('acceptance-runs/'):
        raise RecordError('Reports must stay in acceptance-runs/')
    target = safe_path(root, out)
    if target.exists():
        raise RecordError('Run directory already exists; use a new name to preserve evidence')
    _, _, _, catalog, _ = load_records(root)
    by = keyed(catalog['suites'])
    if selections == ['all-offline']:
        selections = [s['id'] for s in catalog['suites'] if s['status'] == 'IMPLEMENTED' and s['mode'] == 'OFFLINE']
    if not selections or len(set(selections)) != len(selections) or not set(selections) <= by.keys():
        raise RecordError('Unknown, duplicate, or empty suite selection')
    if not features:
        raise RecordError('Provide at least one feature whose scope the report will bind')
    scope = evidence_scope(root, features)
    packages = {}
    for package in ['PyYAML', 'jsonschema', 'referencing', 'rpds-py', 'attrs', 'jsonschema-specifications']:
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = 'NOT_INSTALLED'
    report = dict(report_kind='offline-quality-v1', started_at=now(), ended_at=None,
                  requested_features=features, scope=scope, scope_changed_during_run=False,
                  environment={'python': platform.python_version(), 'platform': platform.platform(), 'packages': packages},
                  git=git_snapshot(root), results=[], overall='RUNNING',
                  application_executed=False, live_model_called=False, remote_ci_executed=False,
                  note='Offline evidence only. File hashes do not authenticate the author or prove test adequacy.')
    target.mkdir(parents=True, exist_ok=False)
    def save() -> None:
        atomic_replace(root, out+'/report.json', json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    save()
    for sid in selections:
        suite = by[sid]
        entry = {'id': sid, 'status': 'NOT_RUN', 'exit_code': None, 'unit_summary': None}
        report['results'].append(entry)
        save()
        if suite['status'] != 'IMPLEMENTED' or suite['mode'] != 'OFFLINE':
            entry['reason'] = 'Suite is not implemented as an offline command; not skipped as a success'
            save()
            continue
        argv = [arg.replace('{python}', sys.executable).replace('{run_dir}', out) for arg in suite['argv']]
        entry['argv'] = ['{python}' if a == sys.executable else a for a in argv]
        start = time.monotonic()
        print('RUN '+sid+': '+' '.join(entry['argv']), flush=True)
        timed_out = False
        env = dict(os.environ)
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        # No credentials are needed by these tools. This is a reduction in exposure, not a sandbox.
        for k in list(env):
            if any(x in k.upper() for x in ['API_KEY', 'API_SERVER_KEY', 'PASSWORD', 'SECRET', 'TOKEN']):
                env.pop(k, None)
        try:
            p = subprocess.run(argv, cwd=root, env=env, shell=False, capture_output=True, text=True,
                               timeout=suite['timeout_seconds'], check=False)
            entry['exit_code'] = p.returncode
            output = p.stdout+'\n'+p.stderr
        except subprocess.TimeoutExpired:
            timed_out = True
            output = 'TIMEOUT: no command output retained after deadline.'
        except OSError as e:
            entry['exit_code'] = 127
            output = 'Process could not start: '+str(e)
        entry['duration_seconds'] = round(time.monotonic()-start, 3)
        if suite.get('unit_report') and not timed_out:
            try:
                entry['unit_summary'] = read_data(root, out+'/'+suite['unit_report'])
            except (OSError, ValueError):
                entry['unit_summary'] = {'status': 'MISSING', 'tests_run': 0}
        entry['status'] = result_status(entry['exit_code'], entry['unit_summary'], timed_out)
        log = redact(output)
        if len(log) > 300_000:
            log = log[:300_000]+'\n[LOG_TRUNCATED]'
        log_rel = out+'/'+sid+'.log'
        write_new(root, log_rel, log)
        entry['log'] = log_rel
        entry['log_sha256'] = hashlib.sha256(log.encode()).hexdigest()
        print(f'{sid}: {entry["status"]}', flush=True)
        save()
    report['scope_changed_during_run'] = evidence_scope(root, features) != scope
    report['ended_at'] = now()
    report['overall'] = ('PASS' if report['results'] and all(x['status'] == 'PASS' for x in report['results'])
                         and not report['scope_changed_during_run'] else 'FAIL')
    save()
    return report, 0 if report['overall'] == 'PASS' else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--suite', action='append', help='repeat named suite or use all-offline')
    parser.add_argument('--feature', action='append', default=[])
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    try:
        report, code = run(args.root.resolve(), args.out, args.suite or ['all-offline'], args.feature)
        print(json.dumps({'overall':report['overall'], 'report':args.out+'/report.json',
                          'application_verified':False}, ensure_ascii=False))
        return code
    except (OSError, ValueError, KeyError, TypeError) as e:
        print('ERROR: '+str(e), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
