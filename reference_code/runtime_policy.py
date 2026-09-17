"""Local configuration checks for Zhijuan v1.2, NOT live Hermes integration.

This module makes no network calls and enforces no OS isolation. The application
must call it on trusted server configuration, then separately verify the model,
credentials, network routing, runtime isolation and tool capabilities.
"""
from collections.abc import Mapping
from typing import Any

ROLES = ("planner", "author", "solver", "reviewer", "exam_reviewer")
EXPECTED_OWNERS = {
    "agent_loop": "hermes",
    "request_retry": "hermes_request_layer",
    "repair_actions": "hermes",
    "repair_budget": "business_backend",
    "state": "business_backend",
    "tool_permissions": "tool_gateway",
    "delivery_recovery": "celery",
    "adapter": "thin_python_boundary",
}


def _object(parent: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be a mapping")
    return value


def validate_runtime_policy(policy: Mapping[str, Any]) -> dict[str, str]:
    """Reject incomplete/wrong v1.2 routes; return approved provider/model label.

    A successful return validates ONLY the fields inspected here. It is not a
    certificate of account access, tool-call support, model quality or isolation.
    """
    if not isinstance(policy, Mapping):
        raise ValueError("policy must be a mapping")
    runtime = _object(policy, "ai_runtime")
    if runtime.get("agent_framework") != "hermes":
        raise ValueError("Hermes must be the sole agent framework")
    if runtime.get("model_provider") != "deepseek":
        raise ValueError("DeepSeek is the approved v1.2 provider")
    if runtime.get("connection_mode") != "direct_official_api":
        raise ValueError("v1.2 requires direct official API routing")
    if runtime.get("additional_agent_frameworks") != []:
        raise ValueError("Additional agent frameworks are not allowed in v1.2")
    if runtime.get("automatic_provider_fallback") is not False:
        raise ValueError("Automatic provider fallback must be disabled")
    if runtime.get("auxiliary_provider_policy") != "same_provider_or_disabled":
        raise ValueError("Auxiliary calls must stay on the approved route or be disabled")
    if runtime.get("verification_label") != "SAME_MODEL":
        raise ValueError("Default same-model runs must be labeled SAME_MODEL")
    models = _object(policy, "models")
    if set(models) != set(ROLES):
        raise ValueError("Exactly the five documented roles must be configured")
    ids: set[str] = set()
    for role in ROLES:
        route = _object(models, role)
        if route.get("provider") != "deepseek":
            raise ValueError(f"{role}: provider must be deepseek")
        model_id = route.get("model_id")
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError(f"{role}: model_id is required")
        if model_id != model_id.strip() or any(c.isspace() for c in model_id):
            raise ValueError(f"{role}: model_id contains whitespace")
        if any(x in model_id.upper() for x in ("REPLACE", "SET_AFTER", "${", "<MODEL")):
            raise ValueError(f"{role}: replace the example model_id before deployment")
        ids.add(model_id)
    if len(ids) != 1:
        raise ValueError("This v1.2 default policy requires one shared model_id")
    owners = _object(policy, "execution_ownership")
    for field, expected in EXPECTED_OWNERS.items():
        if owners.get(field) != expected:
            raise ValueError(f"{field}: expected owner {expected}")
    return {"provider": "deepseek", "model_id": next(iter(ids)), "verification_label": "SAME_MODEL"}
