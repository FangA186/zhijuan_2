"""Defect memory lookup, validation and finish gates in temporary directories."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from tools.bug_records import bug_snapshot, fingerprint, load_bugs, search_bugs
from tools.bug_workflow import bug_finish_issues, lookup
from tools.bug_notion import export_pages, mark_synced


class BugMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'progress/bugs').mkdir(parents=True)
        (self.root / 'acceptance-runs').mkdir()
        (self.root / 'acceptance-runs/check.md').write_text('fixture check passed')
        self.record = dict(id='BUG-20260924-001', title='长公式溢出', status='FIXED', module='frontend',
            updated_at='2026-09-24', task_ids=['DEV-04'], keywords=['KaTeX', 'scrollWidth'],
            symptom='长公式撑宽页面', reproduction=['在窄屏读取题目'], root_cause='flex最小宽度',
            resolution='局部滚动', affected_files=['apps/web/example.tsx'], regression=['fixture regression'],
            verified_at='2026-09-24', verification='OFFLINE_PASS', evidence_refs=['acceptance-runs/check.md'],
            events=['2026-09-24 fixture'], source_hashes={})
        self.save()
        (self.root / 'progress/bugs/notion-sync.json').write_text(json.dumps({'pages': {}}))

    def save(self):
        (self.root / 'progress/bugs/BUG-20260924-001.yaml').write_text(yaml.safe_dump(self.record, allow_unicode=True))

    def search(self):
        with patch('tools.bug_workflow.load_records', return_value=({}, {}, {'tasks': [{'id': 'DEV-04'}]}, {}, {})):
            return lookup(self.root, 'KaTeX 不存在词', 'DEV-04')

    def test_keyword_and_related_path_search_returns_root_cause(self):
        results = self.search()
        self.assertEqual(results['matches'][0]['root_cause'], 'flex最小宽度')
        self.assertTrue((self.root / results['receipt']).exists())
        self.assertEqual(len(search_bugs(load_bugs(self.root), paths=['apps/web/example.tsx'])), 1)
        self.assertEqual(len(search_bugs(load_bugs(self.root), paths=['apps/web'])), 1)
        self.assertEqual(search_bugs(load_bugs(self.root), '完全未命中'), [])

    def test_declared_bugfix_cannot_finish_without_lookup_ids_and_sync(self):
        handoff = {'bug_ids': [self.record['id']]}
        self.assertTrue(any('检索' in x for x in bug_finish_issues(self.root, 'DEV-04', handoff, 'DONE', {})))
        self.search()
        self.assertTrue(any('bug_ids' in x for x in bug_finish_issues(self.root, 'DEV-04', {}, 'DONE', {})))
        self.assertTrue(any('Notion' in x for x in bug_finish_issues(self.root, 'DEV-04', handoff, 'DONE', {})))
        mark_synced(self.root, self.record['id'], 'https://www.notion.so/fixture', fingerprint(self.record))
        self.assertEqual(bug_finish_issues(self.root, 'DEV-04', handoff, 'DONE', {}), [])

    def test_reopened_or_changed_record_is_not_still_synced(self):
        mark_synced(self.root, self.record['id'], 'https://www.notion.so/fixture', fingerprint(self.record))
        self.assertEqual(export_pages(self.root)['pages'], [])
        old_hash = fingerprint(self.record)
        self.record['status'] = 'REOPENED'
        self.record['events'].append('复发')
        self.save()
        self.assertEqual(bug_snapshot(self.root)['items'][0]['sync_status'], '待同步')
        self.assertEqual(len(export_pages(self.root)['pages']), 1)
        with self.assertRaises(ValueError):
            mark_synced(self.root, self.record['id'], 'https://www.notion.so/fixture', old_hash)

    def test_fixed_requires_evidence_and_safe_paths(self):
        self.record['evidence_refs'] = []
        self.save()
        with self.assertRaises(ValueError):
            load_bugs(self.root)
        self.record['status'] = 'OPEN'
        self.record['affected_files'] = ['../../.env']
        self.save()
        with self.assertRaises(ValueError):
            load_bugs(self.root)

    def test_not_bugfix_is_unaffected_and_bad_task_id_rejected(self):
        self.assertEqual(bug_finish_issues(self.root, 'DEV-04', {}, 'DONE', {}), [])
        with self.assertRaises(ValueError):
            lookup(self.root, 'KaTeX', '../../escape')

    def test_prior_checkpoint_receipt_cannot_cover_next_repair(self):
        self.search()
        directory = self.root / 'progress/handoffs'
        directory.mkdir()
        (directory / 'prior.yaml').write_text(yaml.safe_dump({
            'task_id': 'DEV-04', 'session_id': 'prior', 'created_at': '2026-09-24T00:00:00Z'}))
        current = {'session_id': 'current', 'bug_ids': [self.record['id']]}
        issues = bug_finish_issues(self.root, 'DEV-04', current, 'IN_PROGRESS', {})
        self.assertTrue(any('上一检查点' in x for x in issues))
        self.search()
        self.assertEqual(bug_finish_issues(self.root, 'DEV-04', current, 'IN_PROGRESS', {}), [])

    def test_missing_historical_evidence_remains_visible_but_fails_check(self):
        (self.root / 'acceptance-runs/check.md').unlink()
        self.assertFalse(bug_snapshot(self.root)['items'][0]['evidence_available'])
        with self.assertRaises(ValueError):
            load_bugs(self.root, check_evidence=True)

    def test_dashboard_rejects_external_sync_links_and_private_hash_paths(self):
        sync = {'database_url': 'javascript:alert(1)', 'pages': {self.record['id']: {
            'url': 'https://example.invalid', 'content_hash': fingerprint(self.record)}}}
        (self.root / 'progress/bugs/notion-sync.json').write_text(json.dumps(sync))
        value = bug_snapshot(self.root)
        self.assertEqual(value['database_url'], '')
        self.assertEqual(value['items'][0]['notion_url'], '')
        self.record['source_hashes'] = {'uploads/private.docx': 'a' * 64}
        self.save()
        with self.assertRaises(ValueError):
            load_bugs(self.root)

    def test_legacy_undated_handoff_does_not_break_search_receipt(self):
        from tools.bug_workflow import previous_session
        folder=self.root/'progress/handoffs';folder.mkdir()
        for name,stamp in [('old',None),('new','2026-09-22T00:00:00+00:00')]:
            record={'task_id':'DEV-04','session_id':name}
            if stamp:record['created_at']=stamp
            (folder/f'{name}.yaml').write_text(yaml.safe_dump(record))
        self.assertEqual(previous_session(self.root,'DEV-04'),'new')


if __name__ == '__main__':
    unittest.main()
