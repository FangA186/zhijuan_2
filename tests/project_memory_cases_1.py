"""Project record checks, part 1."""
from tests.project_memory_fixture import *

class MemoryCases1Tests(MemoryFixture, unittest.TestCase):
    def test_record_consistency(self):
        self.assertEqual(m.validate_memory(self.root)['features'],16)


    def test_product_status_not_promoted_by_tools(self):
        for state in ('NOT_STARTED', 'IN_PROGRESS'):
            with self.subTest(state=state):
                for feature in self.ledger['features']:
                    if feature['kind'] == 'PRODUCT':
                        feature['implementation'] = state
                self.save('progress/features.yaml', self.ledger)
                m.validate_memory(self.root)
                m.status_markdown(self.root)
                recorded = m.read_data(self.root, 'progress/features.yaml')
                self.assertEqual(recorded, self.ledger)
                for feature in recorded['features']:
                    if feature['kind'] == 'PRODUCT':
                        self.assertEqual(feature['implementation'], state)
                        self.assertEqual(m.evidence_state(self.root, feature)[0], 'NOT_RUN')


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
        self.assertEqual(len(m.impact(self.root,['contracts/candidate.schema.json'])['affected_features']),16)


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

