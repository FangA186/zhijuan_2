"""Prevent runtime upgrades from re-enabling hidden model calls/retry ladders."""
import unittest
from pathlib import Path
import yaml


class HermesRuntimeProfileTests(unittest.TestCase):
    def test_exam_profiles_disable_auxiliary_calls_and_nested_retry(self):
        for path in ['infra/workflow-acceptance/profile.yaml','infra/hermes-solver/config.yaml']:
            with self.subTest(path=path):
                data=yaml.safe_load(Path(path).read_text())
                self.assertEqual(data['agent']['api_max_retries'],0)
                self.assertEqual(data['agent']['auto_recovery_cycles'],0)
                self.assertFalse(data['auxiliary']['title_generation']['enabled'])
                self.assertFalse(data['auxiliary']['title_generation']['model_upgrade_enabled'])
                self.assertEqual(data['platform_toolsets']['api_server'],[])
                self.assertEqual(data['toolsets'],[])
                self.assertFalse(data['memory']['memory_enabled'])
