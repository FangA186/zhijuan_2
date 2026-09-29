"""Pure seed specification and the real HTTP acceptance contract."""
from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen

def build_seed_spec() -> dict:
    """单学段 primary、单节 1 题 single_choice、score_each_x100=100、total 100 的合法规格。

    结构对齐 examples/exam-spec-primary.json 与 test_queue_runtime.py 的种子写法；
    通过 validate_spec 与 BlueprintGenerator 的分值配平约束。
    """
    return {
        "title": "L01 单题真实验收（单学段 single_choice 1 题）",
        "curriculum_system": "中国大陆普通教育（教师确认）",
        "region": "用户自报地区",
        "stage": "primary",
        "stage_year": 4,
        "grade_label": "四年级",
        "subject_code": "math",
        "subject_label": "数学",
        "textbook": None,
        "module": None,
        "taught_scope": {
            "topics": ["整数四则运算"],
            "excluded_topics": [],
            "permitted_methods": ["仅使用教师确认的已教方法"],
            "scope_confirmed": True,
        },
        "purpose": "review",
        "usage_context": "personal_learning",
        "delivery_mode": "paper",
        "total_score_x100": 100,
        "duration_minutes": 30,
        "sections": [
            {
                "id": "p1",
                "title": "选择题",
                "question_type": "single_choice",
                "count": 1,
                "score_each_x100": 100,
                "topics": ["整数四则运算"],
            },
        ],
        "difficulty_distribution": {"basic": 100, "medium": 0, "advanced": 0},
        "output_preferences": {"paper_size": "A4", "font_size_pt": 12, "include_answer_space": True},
        "provided_materials": [],
    }


def http_request(method: str, api_base: str, path: str, *, timeout: float,
                  headers: dict[str, str] | None = None, body: Any = None, urlopen_fn=urlopen) -> tuple[int, dict[str, str], Any]:
    """urllib 封装：返回 (status, headers, json-body)；网络层交给 urlopen（可 mock）。"""
    payload = None if body is None else json.dumps(body).encode("utf-8")
    req_headers = dict(headers or {})
    if payload is not None:
        req_headers["Content-Type"] = "application/json"
    req = Request(api_base + path, data=payload, method=method, headers=req_headers)
    with urlopen_fn(req, timeout=timeout) as resp:
        raw_headers = {k.lower(): v for k, v in resp.headers.items()}
        raw = resp.read().decode("utf-8")
        parsed = json.loads(raw) if raw else None
        return resp.status, raw_headers, parsed


def run_acceptance_chain(api_base: str, seed_spec: dict, *, timeout: float = 30.0, hooks) -> dict[str, Any]:
    """真实 HTTP 受理链路：

    GET /v1/exams/current/spec 取 ETag（响应头）
      -> PUT 规格（If-Match）
      -> POST /v1/exams/current/plans/generate（If-Match）
      -> POST /v1/exams/current/plans/{plan_id}/confirm（If-Match）
      -> POST /v1/exams/current/generation-jobs（If-Match，预期 202，走真实预算门禁）

    返回 {job_id, status, ...}。任何一步非预期即抛 RuntimeError（fail-closed）。
    ETag 来自每次响应头 ``etag``（exams.py 在响应头写入当前规格版本）。"""
    def etag_of(step: str, status: int, headers: dict[str, str], payload: Any) -> str:
        if status != 200:
            raise RuntimeError(f"{step} 失败 HTTP {status}: {payload}")
        value = headers.get("etag", "")
        if not value:
            raise RuntimeError(f"{step} 未返回 ETag 头")
        return value

    status, headers, spec = hooks._http_request("GET", api_base, "/v1/exams/current/spec", timeout=timeout)
    etag = etag_of("GET /v1/exams/current/spec", status, headers, spec)

    status, headers, updated = hooks._http_request(
        "PUT", api_base, "/v1/exams/current/spec", timeout=timeout,
        headers={"If-Match": etag}, body=seed_spec)
    etag = etag_of("PUT spec", status, headers, updated)

    status, headers, plan = hooks._http_request(
        "POST", api_base, "/v1/exams/current/plans/generate", timeout=timeout,
        headers={"If-Match": etag}, body=seed_spec)
    if status != 200 or not isinstance(plan, dict) or not plan.get("plan_id"):
        raise RuntimeError(f"plans/generate 失败 HTTP {status}: {plan}")
    plan_id = plan["plan_id"]
    # plans/generate 响应不带 ETag 头；confirm 沿用 PUT spec 时返回的
    # 当前规格版本 ETag（与 tests/integration/test_workflow_integration.py 同款用法）。

    status, headers, confirmed = hooks._http_request(
        "POST", api_base, f"/v1/exams/current/plans/{plan_id}/confirm", timeout=timeout,
        headers={"If-Match": etag})
    if status != 200 or not isinstance(confirmed, dict) or confirmed.get("confirmed") is not True:
        raise RuntimeError(f"plans/{plan_id}/confirm 失败 HTTP {status}: {confirmed}")
    # confirm 亦不回传 ETag；generation-jobs 的 If-Match 继续用 PUT spec 的版本。

    status, headers, job = hooks._http_request(
        "POST", api_base, "/v1/exams/current/generation-jobs", timeout=timeout,
        headers={"If-Match": etag})
    if status != 202 or not isinstance(job, dict) or not job.get("job_id"):
        raise RuntimeError(f"generation-jobs 失败 HTTP {status}（预期 202）: {job}")
    return {"job_id": job["job_id"], "status": job.get("status"), "job": job}
