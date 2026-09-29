"""Project record checks, part 3."""
from tests.project_memory_fixture import *

class MemoryCases3Tests(MemoryFixture, unittest.TestCase):
    def test_finish_tracks_deleted_file_without_faking_a_hash(self):
        self.dev['implementation']='IN_PROGRESS';self.save('progress/features.yaml',self.ledger)
        self.init_git()
        deleted=self.root/'tools/project_memory.py'
        deleted.unlink()
        handoff=m.create_handoff(self.root,'DEV-02','deleted','删除旧入口','核对迁移')
        rel=handoff.resolve().relative_to(self.root.resolve()).as_posix()
        record=m.read_data(self.root,rel)
        self.assertEqual(record['files']['tools/project_memory.py'],'DELETED')
        issues=finish_check(self.root,'DEV-02')['issues']
        self.assertFalse(any('未覆盖本任务变更' in x or '快照已过期' in x for x in issues),issues)
        deleted.write_text('restored')
        self.assertTrue(any('快照已过期' in x for x in finish_check(self.root,'DEV-02')['issues']))
        deleted.unlink();deleted.mkdir()
        self.assertTrue(any('快照已过期' in x for x in finish_check(self.root,'DEV-02')['issues']))

    def test_product_done_requires_current_independent_application_acceptance(self):
        task=next(t for t in m.read_data(self.root,'execution/task-index.yaml')['tasks'] if t['id']=='M0-01')
        report_ref='acceptance-runs/fixture/application.json'
        for rel in task['target_files']:
            path=self.root/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture output')
        source=m.file_snapshot(self.root,task['source_files']+task['target_files'])
        report={'report_kind':'application-acceptance-v1','status':'PASS','application_verified':True,
                'task_ids':['M0-01'],'reviewer':'independent-reviewer','environment':'local test fixture',
                'command':'fixture acceptance command','not_run':[],'source_files':source}
        self.save(report_ref,report)
        work=m.read_data(self.root,'progress/work.yaml')
        work['tasks']['M0-01']={'status':'DONE','completed_by':'implementer','completed_at':'2026-09-22T00:00:00Z',
                                'evidence_refs':[report_ref]}
        self.save('progress/work.yaml',work)
        (self.root/'progress/current.md').write_text(m.status_markdown(self.root))
        self.init_git()
        handoff=m.create_handoff(self.root,'M0-01','acceptance','完成并验收','归档记录',[report_ref])
        rel=handoff.resolve().relative_to(self.root.resolve()).as_posix()
        h=m.read_data(self.root,rel);h['completed']=['临时夹具验收记录'];self.save(rel,h)
        self.assertEqual(finish_check(self.root,'M0-01')['status'],'PASS')
        report['reviewer']='implementer';self.save(report_ref,report)
        self.assertTrue(any('独立 reviewer' in x for x in finish_check(self.root,'M0-01')['issues']))
        report['reviewer']='independent-reviewer';self.save(report_ref,report)
        (self.root/task['target_files'][0]).write_text('target changed')
        self.assertTrue(any('source_files 与当前内容不一致' in x for x in finish_check(self.root,'M0-01')['issues']))
        (self.root/task['target_files'][0]).write_text('fixture output')
        (self.root/'configs/late-contract.yaml').write_text('new global contract')
        self.assertTrue(any('source_files 与当前内容不一致' in x for x in finish_check(self.root,'M0-01')['issues']))
        (self.root/'configs/late-contract.yaml').unlink()
        (self.root/task['source_files'][0]).write_text('source changed')
        self.assertTrue(any('source_files 与当前内容不一致' in x for x in finish_check(self.root,'M0-01')['issues']))
        report['source_files']={};self.save(report_ref,report)
        self.assertTrue(any('source_files 与当前内容不一致' in x for x in finish_check(self.root,'M0-01')['issues']))
        h['evidence_refs']=[];self.save(rel,h)
        self.assertTrue(any('缺少 application-acceptance-v1' in x for x in finish_check(self.root,'M0-01')['issues']))
