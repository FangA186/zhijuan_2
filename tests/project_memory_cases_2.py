"""Project record checks, part 2."""
from tests.project_memory_fixture import *

class MemoryCases2Tests(MemoryFixture, unittest.TestCase):
    def test_context_reports_handoff_file_drift(self):
        m.create_handoff(self.root,'M0-01','s1','等待签收','核对范围')
        p=self.root/'configs/business-policy.example.yaml';p.write_text(p.read_text()+'\n# change\n')
        self.assertIn('登记文件变化=True',m.context_markdown(self.root,'M0-01',None,12000))


    def test_latest_handoff_orders_mixed_timezones_by_instant(self):
        self.save('progress/handoffs/M0-01--old.yaml',{'task_id':'M0-01','created_at':'2026-09-22T19:00:00+08:00'})
        self.save('progress/handoffs/M0-01--new.yaml',{'task_id':'M0-01','created_at':'2026-09-22T12:18:00+00:00'})
        self.save('progress/handoffs/M0-01--invalid.yaml',{'task_id':'M0-01','created_at':'invalid'})
        refs=[ref for ref,_ in m.latest_handoffs(self.root,'M0-01')]
        self.assertIn('new.yaml',refs[0])
        self.assertIn('old.yaml',refs[1])
        self.assertIn('invalid.yaml',refs[2])


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


    def test_handoff_scope_excludes_unrelated_untracked_assets(self):
        self.init_git()
        (self.root/'unrelated-image.png').write_bytes(b'image fixture')
        (self.root/'tools/project_memory.py').write_text('task change')
        handoff=m.create_handoff(self.root,'DEV-02','scoped','检查记录','继续核对')
        record=m.read_data(self.root,handoff.resolve().relative_to(self.root.resolve()).as_posix())
        self.assertIn('tools/project_memory.py',record['git']['changed_paths'])
        self.assertNotIn('unrelated-image.png',record['git']['changed_paths'])
        self.assertNotIn('unrelated-image.png',record['scope_patterns'])


    def test_task_mapped_progress_document_is_snapshotted(self):
        extra=m.read_data(self.root,'progress/extra-tasks.yaml')
        next(t for t in extra['tasks'] if t['id']=='DEV-02')['target_files'].append('progress/handoffs/README.md')
        self.save('progress/extra-tasks.yaml',extra)
        self.init_git()
        (self.root/'progress/handoffs/README.md').write_text('updated instructions')
        handoff=m.create_handoff(self.root,'DEV-02','scoped-doc','检查文档','继续核对')
        rel=handoff.resolve().relative_to(self.root.resolve()).as_posix()
        record=m.read_data(self.root,rel)
        self.assertIn('progress/handoffs/README.md',record['files'])
        (self.root/'progress/handoffs/README.md').write_text('changed again')
        result=finish_check(self.root,'DEV-02')
        self.assertTrue(any('快照已过期' in issue for issue in result['issues']))


    def test_finish_detects_unrecorded_and_stale_task_change(self):
        self.init_git()
        (self.root/'tools/project_memory.py').write_text('task change')
        result=finish_check(self.root,'DEV-02')
        self.assertEqual(result['status'],'FAIL')
        self.assertTrue(any('缺少本任务交接' in issue for issue in result['issues']))
        handoff=m.create_handoff(self.root,'DEV-02','scoped','检查记录','继续核对')
        record=m.read_data(self.root,handoff.resolve().relative_to(self.root.resolve()).as_posix())
        record['pending']=['尚未完成']
        self.save(handoff.resolve().relative_to(self.root.resolve()).as_posix(),record)
        (self.root/'tools/project_memory.py').write_text('changed again')
        result=finish_check(self.root,'DEV-02')
        self.assertTrue(any('快照已过期' in issue for issue in result['issues']))


    def test_finish_passes_recorded_in_progress_checkpoint_without_promoting_it(self):
        self.dev['implementation']='IN_PROGRESS';self.save('progress/features.yaml',self.ledger)
        work=m.read_data(self.root,'progress/work.yaml')
        work['tasks']['DEV-02']={'status':'IN_PROGRESS','evidence_refs':[]}
        self.save('progress/work.yaml',work)
        (self.root/'progress/current.md').write_text(m.status_markdown(self.root))
        self.init_git()
        (self.root/'tools/project_memory.py').write_text('task change')
        handoff=m.create_handoff(self.root,'DEV-02','scoped','开发检查点','继续验证')
        rel=handoff.resolve().relative_to(self.root.resolve()).as_posix()
        record=m.read_data(self.root,rel);record['pending']=['继续验证']
        self.save(rel,record)
        result=finish_check(self.root,'DEV-02')
        self.assertEqual(result['status'],'PASS',result['issues'])
        self.assertEqual(result['task_status'],'IN_PROGRESS')


