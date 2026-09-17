"""Offline tests of project-record tools. No live Hermes/DeepSeek or product claims."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import yaml
from tools import memory_lib as m
from tools.project_memory import main as cli
from tools.run_unittests import summarize
from tools.run_quality_checks import result_status, run

class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='zhijuan-memory-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/'repo'
        shutil.copytree(m.ROOT, self.root, ignore=shutil.ignore_patterns('.git','__pycache__','acceptance-runs','generated','*.log'))
        self.ledger = m.read_data(self.root, 'progress/features.yaml')
        for f in self.ledger['features']:
            f['last_evidence'] = None
        self.save('progress/features.yaml', self.ledger)
        self.dev = self.ledger['features'][-1]

    def save(self, rel, data):
        p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(data,ensure_ascii=False,indent=2) if p.suffix=='.json' else yaml.safe_dump(data,allow_unicode=True,sort_keys=False),encoding='utf-8')

    def report(self):
        # Explicitly synthetic evidence in a temporary test fixture only.
        report = dict(report_kind='offline-quality-v1', requested_features=[self.dev['id']], overall='PASS',
                      scope_changed_during_run=False, scope=m.evidence_scope(self.root,[self.dev['id']]),
                      results=[dict(id=s,status='PASS',exit_code=0,unit_summary=None) for s in self.dev['required_suites']])
        for item in report['results']:
            rel='acceptance-runs/fixture/'+item['id']+'.log'
            path=self.root/rel;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('SYNTHETIC TEST FIXTURE ONLY\n')
            item['log']=rel;item['log_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        self.save('acceptance-runs/fixture/report.json',report)
        f=deepcopy(self.dev);f['last_evidence']='acceptance-runs/fixture/report.json'
        return f,report

    def test_record_consistency(self):
        self.assertEqual(m.validate_memory(self.root)['features'],15)

    def test_product_not_marked_implemented(self):
        self.assertTrue(all(f['implementation']=='NOT_STARTED' for f in self.ledger['features'] if f['kind']=='PRODUCT'))

    def test_duplicate_feature_rejected(self):
        self.ledger['features'].append(deepcopy(self.dev));self.save('progress/features.yaml',self.ledger)
        with self.assertRaisesRegex(m.RecordError,'Duplicate'):m.validate_memory(self.root)

    def test_dependency_cycle_rejected(self):
        self.ledger['features'][0]['requires']=['FEAT-PLAN'];self.save('progress/features.yaml',self.ledger)
        with self.assertRaisesRegex(m.RecordError,'cycle'):m.validate_memory(self.root)

    def test_unknown_dependency_rejected(self):
        self.ledger['features'][0]['requires']=['FEAT-UNKNOWN'];self.save('progress/features.yaml',self.ledger)
        with self.assertRaisesRegex(m.RecordError,'Unknown'):m.validate_memory(self.root)

    def test_fake_implementation_paths_rejected(self):
        self.dev['implementation_paths']=['services/not-built.py'];self.save('progress/features.yaml',self.ledger)
        with self.assertRaisesRegex(m.RecordError,'Missing'):m.validate_memory(self.root)

    def test_empty_implementation_rejected(self):
        self.dev['implementation_paths']=[];self.save('progress/features.yaml',self.ledger)
        with self.assertRaisesRegex(m.RecordError,'IMPLEMENTED'):m.validate_memory(self.root)

    def test_done_without_evidence_rejected(self):
        w=m.read_data(self.root,'progress/work.yaml');w['tasks']['M0-01']={'status':'DONE'};self.save('progress/work.yaml',w)
        with self.assertRaisesRegex(m.RecordError,'DONE'):m.validate_memory(self.root)

    def test_actual_progress_does_not_require_editing_baseline(self):
        w=m.read_data(self.root,'progress/work.yaml');w['tasks']['M0-01']={'status':'IN_PROGRESS'};self.save('progress/work.yaml',w)
        self.assertEqual(m.validate_memory(self.root)['actual_task_records'],1)
        self.assertEqual(m.read_data(self.root,'execution/task-index.yaml')['tasks'][0]['status'],'NOT_STARTED')

    def test_missing_evidence_not_pass(self):
        self.assertEqual(m.evidence_state(self.root,self.dev)[0],'NOT_RUN')

    def test_matching_scope_is_offline_only(self):
        f,_=self.report();self.assertEqual(m.evidence_state(self.root,f)[0],'OFFLINE_PASS')

    def test_changed_code_stales_evidence(self):
        f,_=self.report()
        with (self.root/'tools/project_memory.py').open('a') as out:out.write('\n# test change\n')
        self.assertEqual(m.evidence_state(self.root,f)[0],'STALE')

    def test_new_watched_file_stales_evidence(self):
        f,_=self.report();self.save('quality/new-config.yaml',{'changed':True})
        self.assertEqual(m.evidence_state(self.root,f)[0],'STALE')

    def test_dependency_scope_stales_evidence(self):
        self.dev['requires']=['FEAT-ADAPTER'];self.save('progress/features.yaml',self.ledger)
        f,_=self.report()
        p=self.root/'configs/hermes-reviewed-fragment.yaml';p.write_text(p.read_text()+'\n# changed\n')
        self.assertEqual(m.evidence_state(self.root,f)[0],'STALE')

    def test_changing_scope_declaration_stales_evidence(self):
        f,_=self.report();self.dev['watch_paths']=['tools/project_memory.py'];self.save('progress/features.yaml',self.ledger)
        self.assertEqual(m.evidence_state(self.root,f)[0],'STALE')

    def test_unrelated_handoff_does_not_stale_code_evidence(self):
        f,_=self.report();self.save('progress/handoffs/fixture.yaml',{'unrelated':'not inspected by scope'})
        self.assertEqual(m.evidence_state(self.root,f)[0],'OFFLINE_PASS')

    def test_missing_required_suite_rejected(self):
        f,r=self.report();r['results']=r['results'][:1];self.save('acceptance-runs/fixture/report.json',r)
        self.assertEqual(m.evidence_state(self.root,f)[0],'INCOMPLETE')

    def test_report_failed_not_pass(self):
        f,r=self.report();r['overall']='FAIL';self.save('acceptance-runs/fixture/report.json',r)
        self.assertEqual(m.evidence_state(self.root,f)[0],'FAILED')

    def test_report_changed_during_run_is_stale(self):
        f,r=self.report();r['scope_changed_during_run']=True;self.save('acceptance-runs/fixture/report.json',r)
        self.assertEqual(m.evidence_state(self.root,f)[0],'STALE')

    def test_strict_evidence_needs_evidence(self):
        with self.assertRaisesRegex(m.RecordError,'NOT_RUN'):m.validate_memory(self.root,True)

    def test_public_projection_change_reaches_exports(self):
        i=m.impact(self.root,['services/api/domain/public_projection.py'])
        self.assertIn('FEAT-BLIND',i['direct_features'])
        self.assertIn('FEAT-EXPORT',i['affected_features'])
        self.assertIn('FEAT-PUBLISH',i['affected_features'])

    def test_revision_change_reaches_exports(self):
        i=m.impact(self.root,['services/api/domain/revisions.py'])
        self.assertIn('FEAT-EXPORT',i['affected_features'])

    def test_unknown_path_not_treated_as_safe(self):
        i=m.impact(self.root,['new_component/a.py'])
        self.assertTrue(i['unmapped_paths']);self.assertIn('baseline-unit',i['runnable_suites'])

    def test_global_contract_change_expands_scope(self):
        self.assertEqual(len(m.impact(self.root,['contracts/candidate.schema.json'])['affected_features']),15)

    def test_sensitive_paths_rejected(self):
        for path in ['.env','sub/.env.prod','secret.key','../outside','/etc/passwd','C:\\secret','a\n.txt']:
            with self.subTest(path=path),self.assertRaises(m.RecordError):m.safe_path(self.root,path)

    def test_example_env_allowed(self):
        self.assertTrue(m.safe_path(self.root,'configs/deepseek.env.example',must_exist=True).is_file())

    def test_symlink_rejected(self):
        (self.root/'link').symlink_to(Path(self.tmp.name))
        with self.assertRaisesRegex(m.RecordError,'Symlink'):m.safe_path(self.root,'link/file')

    def test_no_git_explicit(self):
        self.assertEqual(m.git_snapshot(self.root)['state'],'NO_GIT')
        with self.assertRaises(m.RecordError):m.git_snapshot(self.root,'main')

    def test_context_is_bounded_and_does_not_dump_full_docs(self):
        text=m.context_markdown(self.root,'M1-03',None,3000)
        self.assertLessEqual(len(text),3000);self.assertIn('NO_GIT',text)
        self.assertNotIn('DEEPSEEK_API_KEY=',text)

    def test_invalid_task_rejected(self):
        with self.assertRaises(m.RecordError):m.context_markdown(self.root,'M9-99',None,12000)

    def test_handoffs_are_per_task_session_and_never_overwritten(self):
        p=m.create_handoff(self.root,'M0-01','session-a','范围仍待审核','核对范围')
        self.assertTrue(p.exists())
        with self.assertRaises(FileExistsError):m.create_handoff(self.root,'M0-01','session-a','覆盖','覆盖')
        q=m.create_handoff(self.root,'M0-01','session-b','第二个会话','检查依赖')
        self.assertNotEqual(p,q)

    def test_handoff_does_not_mark_task_done(self):
        m.create_handoff(self.root,'M0-01','s1','进行了检查','继续')
        self.assertEqual(m.read_data(self.root,'progress/work.yaml')['tasks'],{})

    def test_context_reports_handoff_file_drift(self):
        m.create_handoff(self.root,'M0-01','s1','等待签收','核对范围')
        p=self.root/'configs/business-policy.example.yaml';p.write_text(p.read_text()+'\n# change\n')
        self.assertIn('登记文件变化=True',m.context_markdown(self.root,'M0-01',None,12000))

    def test_redaction(self):
        self.assertNotIn('abcdefghijklmnop',m.redact('api_key=abcdefghijklmnop'))
        self.assertNotIn('sk-abcdefghijklmnop',m.redact('sk-abcdefghijklmnop'))

    def test_derived_status_reproducible(self):
        self.assertEqual(m.status_markdown(self.root),m.status_markdown(self.root))

    def test_skips_and_zero_tests_fail(self):
        r=unittest.TestResult();self.assertEqual(summarize(r)['status'],'FAIL')
        r.testsRun=1;r.skipped=[('fixture','skip')];self.assertEqual(summarize(r)['status'],'FAIL')

    def test_quality_status_semantics(self):
        self.assertEqual(result_status(None),'NOT_RUN')
        self.assertEqual(result_status(0,{'status':'PASS','tests_run':5,'skipped':1}),'FAIL')
        self.assertEqual(result_status(0,None,True),'TIMED_OUT')
        self.assertEqual(result_status(0,{'status':'PASS','tests_run':5,'skipped':0}),'PASS')

    def test_planned_suite_does_not_become_green(self):
        r,code=run(self.root,'acceptance-runs/fixture-planned',['APP-E2E'],['FEAT-DEV-MEMORY'])
        self.assertEqual(code,1);self.assertEqual(r['results'][0]['status'],'NOT_RUN')

    def test_unknown_suite_rejected(self):
        with self.assertRaises(m.RecordError):run(self.root,'acceptance-runs/fixture-unknown',['unknown'],['FEAT-DEV-MEMORY'])

    def test_cli_generated_output_guard(self):
        self.assertEqual(cli(['--root',str(self.root),'context','--task','M0-01','--out','README.md']),2)

    def test_extra_task_supported_without_baseline_change(self):
        extra=deepcopy(m.read_data(self.root,'execution/task-index.yaml')['tasks'][0])
        extra['id']='FIX-001';extra['title']='Approved follow-up fixture'
        self.save('progress/extra-tasks.yaml',{'schema_version':1,'tasks':[extra]})
        self.assertIn('FIX-001',m.context_markdown(self.root,'FIX-001',None,12000))
        self.assertEqual(len(m.read_data(self.root,'execution/task-index.yaml')['tasks']),32)

    def test_duplicate_extra_task_rejected(self):
        task=deepcopy(m.read_data(self.root,'execution/task-index.yaml')['tasks'][0])
        self.save('progress/extra-tasks.yaml',{'schema_version':1,'tasks':[task]})
        with self.assertRaisesRegex(m.RecordError,'Duplicate'):m.validate_memory(self.root)

    def test_tampered_log_invalidates_evidence(self):
        f,r=self.report();(self.root/r['results'][0]['log']).write_text('modified log')
        self.assertEqual(m.evidence_state(self.root,f)[0],'INVALID')

    def test_ci_has_always_summary_and_no_secret_trigger(self):
        wf=m.read_data(self.root,'.github/workflows/ci.yml')
        trigger=wf.get('on',wf.get(True))
        self.assertIn('pull_request',trigger);self.assertNotIn('pull_request_target',trigger)
        self.assertIn('always()',wf['jobs']['required-checks']['if'])
        self.assertEqual(wf['permissions'],{'contents':'read'})
        self.assertEqual(wf['jobs']['required-checks']['needs'],['offline'])
        for step in wf['jobs']['offline']['steps']:
            self.assertNotIn('continue-on-error',step)
            if 'uses' in step:
                self.assertRegex(step['uses'],r'@[0-9a-f]{40}$')

    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.root),*args],stderr=subprocess.DEVNULL).decode().strip()

    def init_git(self):
        self.git('init','-q','-b','main')
        self.git('config','user.name','Temporary Fixture')
        self.git('config','user.email','fixture@example.invalid')
        (self.root/'.gitignore').write_text('.env\nacceptance-runs/\n__pycache__/\n')
        self.git('add','.');self.git('commit','-qm','test fixture only')
        return self.git('rev-parse','HEAD')

    def test_git_staged_unstaged_untracked_and_committed(self):
        base=self.init_git();self.git('checkout','-qb','feature')
        (self.root/'committed.txt').write_text('x');self.git('add','committed.txt');self.git('commit','-qm','test commit')
        (self.root/'staged.txt').write_text('y');self.git('add','staged.txt')
        (self.root/'README.md').write_text('unstaged')
        (self.root/'untracked.txt').write_text('z')
        snap=m.git_snapshot(self.root,base)
        self.assertTrue({'committed.txt','staged.txt','README.md','untracked.txt'} <= set(snap['changed_paths']))

    def test_git_rename_reports_old_and_new(self):
        base=self.init_git();self.git('mv','README.md','renamed.md')
        snap=m.git_snapshot(self.root,base)
        self.assertIn('README.md',snap['changed_paths']);self.assertIn('renamed.md',snap['changed_paths'])

    def test_missing_base_fails_closed(self):
        self.init_git()
        with self.assertRaises(m.RecordError):m.git_snapshot(self.root,'does-not-exist')

    def test_nested_repository_not_assumed(self):
        self.init_git()
        with self.assertRaisesRegex(m.RecordError,'Git root'):m.git_snapshot(self.root/'docs')

if __name__=='__main__':unittest.main()
