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
from tools.memory_finish import finish_check
from tools.project_memory import main as cli
from tools.run_unittests import summarize
from tools.run_quality_checks import result_status, run


class MemoryFixture:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='zhijuan-memory-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/'repo'
        shutil.copytree(m.ROOT, self.root, ignore=shutil.ignore_patterns('.git','__pycache__','acceptance-runs','generated','*.log','node_modules','.venv','vendor','smartedu_data','dist','教材单词图片*','scratch_test_img'))
        self.ledger = m.read_data(self.root, 'progress/features.yaml')
        for f in self.ledger['features']:
            f['last_evidence'] = None
        self.save('progress/features.yaml', self.ledger)
        for p in (self.root / 'progress/handoffs').glob('*.yaml'):
            p.unlink()
        w = m.read_data(self.root, 'progress/work.yaml')
        w['tasks'] = {}
        self.save('progress/work.yaml', w)
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


    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.root),*args],stderr=subprocess.DEVNULL).decode().strip()


    def init_git(self):
        self.git('init','-q','-b','main')
        self.git('config','user.name','Temporary Fixture')
        self.git('config','user.email','fixture@example.invalid')
        self.git('config','gc.auto','0')
        self.git('config','maintenance.auto','false')
        (self.root/'.gitignore').write_text('.env\nacceptance-runs/\n__pycache__/\n')
        self.git('add','.');self.git('commit','-qm','test fixture only')
        return self.git('rev-parse','HEAD')

