"""Local temporary fixtures only: no app imports, credentials, HTTP or model calls."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import hashlib
import json
import subprocess

from tools import project_overview as page
from tools.memory_lib import evidence_scope


class OverviewTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.feature = {'id':'FEAT-A','title':'测试功能','kind':'PRODUCT','implementation':'IN_PROGRESS','task_ids':['T-1'],'requires':[],'watch_paths':['services/example.py'],'implementation_paths':['services/example.py'],'required_suites':['unit'],'last_evidence':None,'invariants':[],'limitations':['尚未验收']}
        self.write('progress/features.yaml',{'features':[self.feature]})
        self.write('progress/work.yaml',{'stage_hint':'M1','recommended_next_task':'T-1','tasks':{'T-1':{'status':'IN_PROGRESS','previous_completion_claim':{'status':'DONE'}}}})
        self.write('execution/task-index.yaml',{'tasks':[{'id':'T-1','title':'基线任务','phase':'M1','status':'NOT_STARTED','depends_on':[],'target_files':[],'implementation_steps':[]}]})
        self.write('progress/extra-tasks.yaml',{'tasks':[{'id':'T-2','title':'追加任务','phase':'M1'}]})
        self.write('progress/file-guide.yaml',{'directories':{'services':'服务代码'},'files':{'AGENTS.md':'开发入口'}})
        self.write('quality/suites.yaml',{'suites':[]})
        self.write('progress/policy.yaml',{'global_watch_paths':[],'max_scope_files':100})
        self.write('docs/archive/v1.4-bundle/BUNDLE_INFO.json',{'bundle_version':'1.4','product_documents_version':'1.3'})
        self.write('apps/web/package.json',{'version':'1.4.0'})
        self.write('services/example.py','print("example")')
        self.write('AGENTS.md','[任务](progress/work.yaml) [缺失](missing.md) `services/` `progress/features.yaml`')
        self.git=patch.object(page.subprocess,'run',return_value=subprocess.CompletedProcess([],1,stdout='',stderr=''))
        self.git.start();self.addCleanup(self.git.stop)

    def write(self,path,value):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(value if isinstance(value,str) else json.dumps(value),encoding='utf-8')

    def test_actual_status_and_versions_are_not_fabricated(self):
        value=page.snapshot(self.root)
        self.assertEqual(value['tasks'][0]['status'],'IN_PROGRESS')
        self.assertEqual(value['tasks'][0]['previous_completion_claim']['status'],'DONE')
        self.assertEqual(value['tasks'][1]['status'],'NOT_STARTED')
        self.assertEqual(value['features'][0]['verification'],'NOT_RUN')
        self.assertEqual(value['features'][0]['implementation'],'IN_PROGRESS')
        self.assertEqual(value['features'][0]['commits'],[])
        self.assertEqual(value['versions']['product'],'1.3')

    def test_real_evidence_hash_detects_stale_code(self):
        self.write('acceptance-runs/test/unit.log','passed')
        self.feature['last_evidence']='acceptance-runs/test/report.json'
        self.write('progress/features.yaml',{'features':[self.feature]})
        self.write('acceptance-runs/test/report.json',{'report_kind':'offline-quality-v1','requested_features':['FEAT-A'],'overall':'PASS','scope':evidence_scope(self.root,['FEAT-A']),'results':[{'id':'unit','status':'PASS','exit_code':0,'log':'acceptance-runs/test/unit.log','log_sha256':hashlib.sha256(b'passed').hexdigest()}]})
        self.assertEqual(page.snapshot(self.root)['features'][0]['verification'],'OFFLINE_PASS')
        self.write('services/example.py','changed')
        self.assertEqual(page.snapshot(self.root)['features'][0]['verification'],'STALE')

    def test_handoffs_associate_by_task_or_path_and_bad_record_warns(self):
        self.write('progress/handoffs/task.yaml',{'task_id':'T-1','summary':'旧声明','created_at':'2026-09-20','scope_patterns':[]})
        self.write('progress/handoffs/path.yaml',{'task_id':'T-2','summary':'文件改动','created_at':'2026-09-21','scope_patterns':['services/example.py']})
        self.write('progress/handoffs/broken.yaml','[invalid')
        value=page.snapshot(self.root)
        self.assertEqual(len(value['handoffs']),2)
        self.assertEqual(value['handoffs'][0]['features'][0]['id'],'FEAT-A')
        self.assertIn('路径关联',value['handoffs'][0]['features'][0]['basis'])
        self.assertIn('同任务',value['handoffs'][1]['features'][0]['basis'])
        self.assertEqual(len(value['warnings']),1)

    def test_handoffs_sort_mixed_timezones_by_instant(self):
        self.write('progress/handoffs/old.yaml',{'task_id':'T-1','summary':'old','created_at':'2026-09-22T19:00:00+08:00'})
        self.write('progress/handoffs/new.yaml',{'task_id':'T-1','summary':'new','created_at':'2026-09-22T12:18:00+00:00'})
        self.write('progress/handoffs/invalid.yaml',{'task_id':'T-1','summary':'invalid','created_at':'invalid'})
        self.assertEqual([h['summary'] for h in page.snapshot(self.root)['handoffs']],['new','old','invalid'])

    def test_references_follow_actual_agents_paths(self):
        refs=page.snapshot(self.root)['references']
        self.assertIn('progress/work.yaml',[r['path'] for r in refs])
        self.assertIn('services',[r['path'] for r in refs])
        self.assertNotIn('missing.md',[r['path'] for r in refs])

    def test_stage_receipts_are_visible_without_promoting_full_acceptance(self):
        ref='acceptance-runs/live/single-question.json'
        self.write(ref,{'status':'PASS','validation_statuses':['REVIEW']})
        self.write('progress/work.yaml',{'stage_hint':'M1','recommended_next_task':'T-1','tasks':{'T-1':{'status':'IN_PROGRESS','evidence_refs':[ref,ref,'services/example.py','acceptance-runs/missing.json']}}})
        self.write('progress/handoffs/task.yaml',{'task_id':'T-1','created_at':'2026-09-22','evidence_refs':[ref,'acceptance-runs/../../.env']})
        self.write('acceptance-runs/unrelated/report.json',{'overall':'PASS'})
        self.write('progress/handoffs/unrelated.yaml',{'task_id':'T-2','scope_patterns':['services/example.py'],'evidence_refs':['acceptance-runs/unrelated/report.json']})
        feature=page.snapshot(self.root)['features'][0]
        self.assertEqual(feature['stage_evidence_refs'],[ref])
        self.assertEqual(feature['verification'],'NOT_RUN')
        self.assertEqual(feature['implementation'],'IN_PROGRESS')
        self.assertIsNone(feature['last_evidence'])

    def test_traversal_symlinks_and_sensitive_files_are_not_readable(self):
        self.write('.env','SECRET_TEST_MARKER')
        self.write('uploads/private.md','PRIVATE_EXAM_MARKER')
        self.write('acceptance-runs/raw.md','PRIVATE_LOG_MARKER')
        self.write('docs/allowed.md','# Allowed')
        (self.root/'docs/linked.md').symlink_to(self.root/'.env')
        for path in ['../outside','/etc/passwd','.env','uploads/private.md','acceptance-runs/raw.md','docs/linked.md','services/example.py']:
            with self.subTest(path=path),self.assertRaises(ValueError):page.document(self.root,path)
        for path in ['../','.git','uploads/../../']:
            with self.subTest(path=path),self.assertRaises(ValueError):page.tree(self.root,path)
        entries=page.tree(self.root)['entries']
        self.assertTrue(next(e for e in entries if e['name']=='.env')['restricted'])
        self.assertNotIn('SECRET_TEST_MARKER',json.dumps(entries))
        self.assertEqual(page.document(self.root,'docs/allowed.md')['content'],'# Allowed')

    def test_full_directory_pagination_search_and_description_origin(self):
        for i in range(153):self.write(f'items/file-{i:03}.txt','x')
        first=page.tree(self.root,'items');second=page.tree(self.root,'items',150)
        self.assertEqual(first['total'],153);self.assertEqual(len(first['entries']),150)
        self.assertEqual(len(second['entries']),3);self.assertIsNone(second['next_offset'])
        self.assertEqual(page.tree(self.root,'items',query='file-152')['total'],1)
        self.assertIn('推断',first['entries'][0]['description_source'])
        with self.assertRaises(ValueError):page.tree(self.root,'items',-1)

    def test_doc_size_and_secret_redaction(self):
        self.write('docs/large.md','x'*160_001)
        with self.assertRaises(ValueError):page.document(self.root,'docs/large.md')
        self.write('docs/example.md','api_key: fake_secret_marker')
        self.assertNotIn('fake_secret_marker',page.document(self.root,'docs/example.md')['content'])
