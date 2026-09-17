#!/usr/bin/env python3
"""unittest runner with explicit counts: skipped/zero tests cannot silently pass."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.memory_lib import safe_path, write_new


def summarize(result: unittest.TestResult) -> dict:
    value = dict(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                 skipped=len(result.skipped), expected_failures=len(result.expectedFailures),
                 unexpected_successes=len(result.unexpectedSuccesses))
    value['status'] = ('PASS' if result.wasSuccessful() and value['tests_run'] > 0
                       and not value['skipped'] and not value['expected_failures'] else 'FAIL')
    return value


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pattern', default='test_*.py')
    p.add_argument('--report', required=True, help='new JSON report under acceptance-runs/')
    args = p.parse_args()
    if not args.report.startswith('acceptance-runs/'):
        p.error('report must stay under acceptance-runs/')
    safe_path(ROOT, args.report)
    suite = unittest.defaultTestLoader.discover(str(ROOT/'tests'), pattern=args.pattern)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = dict(report_kind='unittest-counts-v1', created_at=datetime.now(timezone.utc).isoformat(),
                  pattern=args.pattern, **summarize(result))
    write_new(ROOT, args.report, json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['status'] == 'PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
