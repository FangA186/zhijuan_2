"""Offline tests only. The invented model ID below is never sent to any API."""
from pathlib import Path
import copy
import unittest
import yaml
from reference_code.runtime_policy import ROLES, validate_runtime_policy

ROOT = Path(__file__).resolve().parents[1]


def example():
    return yaml.safe_load((ROOT / "configs/business-policy.example.yaml").read_text())


def resolved():
    p = example()
    for role in ROLES:
        p["models"][role]["model_id"] = "offline-test-only-model"
    return p


class RuntimePolicyTests(unittest.TestCase):
    def test_resolved_same_model_policy(self):
        result = validate_runtime_policy(resolved())
        self.assertEqual(result, {"provider": "deepseek", "model_id": "offline-test-only-model", "verification_label": "SAME_MODEL"})

    def test_shipped_placeholder_cannot_deploy(self):
        with self.assertRaises(ValueError): validate_runtime_policy(example())

    def test_other_framework_rejected(self):
        p=resolved(); p["ai_runtime"]["agent_framework"]="langgraph"
        with self.assertRaises(ValueError): validate_runtime_policy(p)

    def test_nested_agent_framework_rejected(self):
        p=resolved(); p["ai_runtime"]["additional_agent_frameworks"]=["langchain"]
        with self.assertRaises(ValueError): validate_runtime_policy(p)

    def test_other_provider_rejected(self):
        p=resolved(); p["models"]["solver"]["provider"]="other"
        with self.assertRaises(ValueError): validate_runtime_policy(p)

    def test_automatic_fallback_rejected(self):
        p=resolved(); p["ai_runtime"]["automatic_provider_fallback"]=True
        with self.assertRaises(ValueError): validate_runtime_policy(p)

    def test_auxiliary_other_route_rejected(self):
        p=resolved(); p["ai_runtime"]["auxiliary_provider_policy"]="any"
        with self.assertRaises(ValueError): validate_runtime_policy(p)

    def test_missing_role_rejected(self):
        p=resolved(); del p["models"]["exam_reviewer"]
        with self.assertRaises(ValueError): validate_runtime_policy(p)

    def test_inconsistent_model_ids_rejected(self):
        p=resolved(); p["models"]["solver"]["model_id"]="different-offline-id"
        with self.assertRaises(ValueError): validate_runtime_policy(p)

    def test_wrong_same_model_label_rejected(self):
        p=resolved(); p["ai_runtime"]["verification_label"]="HETEROGENEOUS"
        with self.assertRaises(ValueError): validate_runtime_policy(p)

    def test_retry_owner_cannot_be_queue(self):
        p=resolved(); p["execution_ownership"]["request_retry"]="celery"
        with self.assertRaises(ValueError): validate_runtime_policy(p)

    def test_hermes_native_fragment(self):
        native=yaml.safe_load((ROOT/"configs/hermes-reviewed-fragment.yaml").read_text())
        self.assertEqual(native["model"]["provider"],"deepseek")
        self.assertNotIn("models",native)
        self.assertNotIn("api_key",native["model"])

    def test_empty_model_rejected(self):
        p=resolved(); p["models"]["author"]["model_id"]=""
        with self.assertRaises(ValueError): validate_runtime_policy(p)

    def test_config_type_rejected(self):
        with self.assertRaises(ValueError): validate_runtime_policy(None)

    def test_secret_template_has_no_key(self):
        env=(ROOT/"configs/deepseek.env.example").read_text()
        self.assertIn("DEEPSEEK_API_KEY=\n",env)

    def test_api_metadata_runtime_and_paths(self):
        api=yaml.safe_load((ROOT/"contracts/openapi.yaml").read_text())
        self.assertEqual(api["info"]["version"],"1.3.0")
        self.assertEqual(api["info"]["x-zhijuan-runtime"]["provider"],"deepseek")
        self.assertTrue(all(path.startswith("/v1/") for path in api["paths"]))

if __name__ == "__main__": unittest.main()
