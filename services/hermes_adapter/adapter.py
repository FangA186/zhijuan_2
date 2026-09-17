"""Hermes DeepSeek Adapter implementation.

Conforms to reference_code/adapter_contract.py.
Handles DeepSeek official API requests with Hermes Skills and JSON Schema outputs.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
from typing import Any, Callable, Literal, Mapping
import httpx

from .skills_loader import load_skill, HermesSkill
from .schema_validator import validate_candidate, SchemaValidationError

Role = Literal["planner", "author", "solver", "reviewer", "exam_reviewer"]

@dataclass(frozen=True)
class RunRequest:
    task_ref: str
    provider: Literal["deepseek"]
    model_id: str
    role: Role
    input_payload: Mapping[str, Any]
    schema_name: str
    skill_bundle_hash: str = "default_bundle"
    policy_hash: str = "default_policy"
    max_iterations: int = 1
    deadline_utc: str = ""
    capability_grant_ref: str = "grant_default"

@dataclass(frozen=True)
class RunResult:
    status: Literal["SUCCEEDED", "FAILED", "CANCELLED", "TIMED_OUT", "BUDGET_EXCEEDED", "UNKNOWN"]
    payload: Mapping[str, Any] | None
    provider_request_ids: tuple[str, ...]
    usage: Mapping[str, Any]
    error_code: str | None = None

def _load_env_file() -> None:
    """Load .env file if present without external python-dotenv dependency."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k and k not in os.environ:
                os.environ[k] = v

class HermesDeepSeekAdapter:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout: float = 60.0,
    ):
        _load_env_file()
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "").strip()
        self.base_url = (
            base_url
            or os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
        )
        self.default_model = (
            default_model
            or os.environ.get("ZHIJUAN_DEEPSEEK_MODEL_ID", "deepseek-chat").strip()
        )
        self.timeout = timeout
        self.cancelled_tasks: set[str] = set()

    def health(self) -> Mapping[str, Any]:
        """Return pinned Hermes runtime status and DeepSeek configuration."""
        has_key = bool(self.api_key)
        return {
            "agent_framework": "hermes",
            "provider": "deepseek",
            "model_id": self.default_model,
            "api_configured": has_key,
            "base_url": self.base_url,
            "skills_available": ["exam-planner", "question-author", "blind-solver", "question-reviewer", "exam-reviewer"],
        }

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "supported_providers": ["deepseek"],
            "supported_models": ["deepseek-chat", "deepseek-reasoner"],
            "structured_json": True,
            "tool_calling": True,
            "max_tokens": 8192,
        }

    def cancel(self, task_ref: str) -> None:
        """Flag a task as cancelled."""
        self.cancelled_tasks.add(task_ref)

    def _call_deepseek_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model_id: str,
        json_mode: bool = True,
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        """Make direct official API call to DeepSeek chat completions."""
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured in environment or .env file.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        body: dict[str, Any] = {
            "model": model_id or self.default_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        if json_mode:
            body["response_format"] = {"type": "json_object"}

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                raise RuntimeError(f"DeepSeek API error ({resp.status_code}): {resp.text}")

            res_json = resp.json()

        request_id = res_json.get("id", f"req_{int(time.time()*1000)}")
        usage = res_json.get("usage", {})
        content_str = res_json["choices"][0]["message"]["content"]

        def _parse_json_robust(text: str) -> dict[str, Any]:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
            open_braces = cleaned.count("{") - cleaned.count("}")
            open_brackets = cleaned.count("[") - cleaned.count("]")
            if open_brackets > 0 or open_braces > 0:
                patched = cleaned + ("]" * max(0, open_brackets)) + ("}" * max(0, open_braces))
                try:
                    return json.loads(patched)
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"DeepSeek response is not valid JSON: {text}")

        parsed_payload = _parse_json_robust(content_str)

        return parsed_payload, usage, request_id

    def run_stage(
        self,
        request: RunRequest,
        emit_event: Callable[[Mapping[str, Any]], None] | None = None,
        cancellation_requested: Callable[[], bool] | None = None,
    ) -> RunResult:
        """Run a single Hermes stage using the specified role skill."""
        if request.task_ref in self.cancelled_tasks or (cancellation_requested and cancellation_requested()):
            return RunResult(
                status="CANCELLED",
                payload=None,
                provider_request_ids=(),
                usage={},
                error_code="TASK_CANCELLED",
            )

        # Map role to skill directory
        role_skill_map: dict[Role, str] = {
            "planner": "exam-planner",
            "author": "question-author",
            "solver": "blind-solver",
            "reviewer": "question-reviewer",
            "exam_reviewer": "exam-reviewer",
        }

        skill_name = role_skill_map.get(request.role, "question-author")
        try:
            skill = load_skill(skill_name)
        except FileNotFoundError as e:
            return RunResult(
                status="FAILED",
                payload=None,
                provider_request_ids=(),
                usage={},
                error_code=f"SKILL_NOT_FOUND: {e}",
            )

        if emit_event:
            emit_event({"event": "skill_loaded", "skill": skill_name, "role": request.role})

        # Augment system prompt with output format instructions
        enhanced_system_prompt = (
            f"{skill.system_prompt}\n\n"
            "【输出格式严格约束】\n"
            "你必须且仅输出严格合法的 JSON 对象，不包含任何外部 Markdown ```json 标记或问候语。\n"
        )

        user_prompt = json.dumps(request.input_payload, ensure_ascii=False)

        try:
            payload, usage, req_id = self._call_deepseek_chat(
                system_prompt=enhanced_system_prompt,
                user_prompt=user_prompt,
                model_id=request.model_id,
                json_mode=True,
            )

            # If authoring, enforce candidate schema
            if request.role == "author":
                validate_candidate(payload)

            return RunResult(
                status="SUCCEEDED",
                payload=payload,
                provider_request_ids=(req_id,),
                usage=usage,
                error_code=None,
            )
        except Exception as e:
            return RunResult(
                status="FAILED",
                payload=None,
                provider_request_ids=(),
                usage={},
                error_code=str(e),
            )

    def execute_author_role(
        self,
        slot_spec: dict[str, Any],
        stage: str,
        subject: str,
        model_id: str = "deepseek-chat",
    ) -> dict[str, Any]:
        """Convenience method to generate a candidate question."""
        skill = load_skill("question-author")
        sys_prompt = (
            f"{skill.system_prompt}\n\n"
            "【严格输出格式】\n"
            "请直接输出符合 candidate.schema.json 的 JSON 结构，包含 public 和 private 属性。\n"
            "public 中必须包含 local_id, kind, prompt (Block 数组), options (如果是选择题/判断题), score_x100, material_ids, children, answer_space_lines。\n"
            "private 中必须包含 answers 数组，每项必须且仅包含：\n"
            "- local_question_id: 对应题目的 local_id\n"
            "- answer_kind: selection | expression | free_text | rubric 之一\n"
            "- correct_option_ids: 正确选项 id 列表 (如 [\"opt_A\"]，非选择题为空数组)\n"
            "- accepted_answers: 接受答案列表，如 [{\"value\": \"A\", \"format\": \"text\", \"conditions\": \"唯一正确选项\"}]\n"
            "- solution: 解析过程 (Block 数组，每项含 type 和 text 或 latex)\n"
            "- rubric: 评分细则列表，每项含 id, description, score_x100, acceptable_variants\n"
            "Block 类型为 {\"type\": \"text\", \"text\": \"...\"} 或 {\"type\": \"math\", \"latex\": \"...\"}。\n"
            "分值单位全部使用 score_x100 整数 (如 4 分存 400，18 分存 1800)。"
        )

        user_content = {
            "stage": stage,
            "subject": subject,
            "slot": slot_spec,
            "instruction": "请根据给定的槽位知识点与考查目标，原创命制一道高质量题目。",
        }

        payload, _, _ = self._call_deepseek_chat(
            system_prompt=sys_prompt,
            user_prompt=json.dumps(user_content, ensure_ascii=False),
            model_id=model_id,
            json_mode=True,
        )

        validate_candidate(payload)
        return payload

    def execute_solver_role(
        self,
        public_question: dict[str, Any],
        model_id: str = "deepseek-chat",
    ) -> dict[str, Any]:
        """Convenience method to run blind solver on an isolated public question."""
        skill = load_skill("blind-solver")
        sys_prompt = (
            f"{skill.system_prompt}\n\n"
            "【严格输出格式】\n"
            "请直接输出独立解题分析结果 JSON，字段必须包含：\n"
            "- derived_answer: 最终答案字符串 (如 'A' 或 'x=2 或 x=-3')\n"
            "- selected_option_ids: 如果是选择题，输出选中的选项 id 数组 (如 [\"opt_A\"])\n"
            "- steps: 解题步骤数组，每项包含 {\"step_number\": 1, \"description\": \"...\"}\n"
            "- reasoning_summary: 简要推理说明"
        )

        user_content = {
            "public_question": public_question,
            "task": "你是一个独立的盲审解题专家，请在没有任何参考答案的情况下，仅依据题面独立作答。",
        }

        payload, _, _ = self._call_deepseek_chat(
            system_prompt=sys_prompt,
            user_prompt=json.dumps(user_content, ensure_ascii=False),
            model_id=model_id,
            json_mode=True,
        )

        return payload
