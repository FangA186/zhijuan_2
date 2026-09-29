"""Regression: clean Git checkout excludes local evidence, not required source."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.memory_base import RecordError
from tools.memory_local_evidence import historical_reference
from tools.run_quality_checks import run


class CleanCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root / '.gitignore').write_text('acceptance-runs/**/*.log\nacceptance-runs/**/verification.json\n')

    def test_explicit_local_evidence_warns_but_never_passes_strict_gate(self):
        ref = 'acceptance-runs/history/verification.json'
        warnings = []
        historical_reference(self.root, ref, warnings)
        self.assertIn('LOCAL_EVIDENCE_UNAVAILABLE', warnings[0])
        with self.assertRaises(RecordError):
            historical_reference(self.root, ref, [], strict=True)
        for required in ['acceptance-runs/history/report.md', 'services/required.py', '../outside.log']:
            with self.assertRaises(RecordError):historical_reference(self.root, required, [])

    def test_tracked_evidence_is_required_even_if_ignore_rule_matches(self):
        ref = 'acceptance-runs/history/verification.json'
        file = self.root / ref
        file.parent.mkdir(parents=True)
        file.write_text('{}')
        subprocess.run(['git','-C',str(self.root),'add','-f','--',ref],check=True)
        file.unlink()
        with self.assertRaises(RecordError):historical_reference(self.root,ref,[])

    def test_preflight_failure_writes_failure_report_and_keeps_exit_failure(self):
        with patch('tools.run_quality_checks.validate_memory', side_effect=RecordError('missing required source')):
            with self.assertRaises(RecordError):
                run(self.root, 'acceptance-runs/ci/run1', ['all-offline'], ['FEAT-DEV-MEMORY'])
        path = self.root / 'acceptance-runs/ci/run1/report.json'
        result = json.loads(path.read_text())
        self.assertEqual(result['overall'], 'FAIL')
        self.assertEqual(result['results'], [])
        before = path.read_bytes()
        with self.assertRaises(RecordError):run(self.root,'acceptance-runs/ci/run1',[],[])
        self.assertEqual(before,path.read_bytes())
