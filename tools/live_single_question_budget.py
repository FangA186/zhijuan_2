"""Budget read-only endpoint and urllib wrapper for the L01 preflight."""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.request import Request, urlopen

def http_get(url: str, *, timeout: float, token: str | None = None,
              headers: dict[str, str] | None = None, urlopen_fn=urlopen) -> tuple[int, Any]:
    """最小 GET 封装；网络/fixture 均注入 mock。成功返回 (200, json)。"""
    req_headers = dict(headers or {})
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    req = Request(url, method="GET", headers=req_headers)
    with urlopen_fn(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body)


def _budget_endpoint() -> str:
    """预算内部端点。ZHIJUAN_BUDGET_INTERNAL_URL 可能已含或未含路径后缀。

    按 ask 描述（GET {ZHIJUAN_BUDGET_INTERNAL_URL}/internal/budget），若变量
    是 base（host:port）则补 /internal/budget；若已含该路径则不重复拼接。

    fail-closed：变量必须显式配置；未配置时抛 RuntimeError，绝不回退到任何
    硬编码地址（漏配时误连非知卷服务），由调用方归为 BUDGET_UNAVAILABLE。
    """
    url = os.getenv("ZHIJUAN_BUDGET_INTERNAL_URL", "").strip().rstrip("/")
    if not url:
        raise RuntimeError("ZHIJUAN_BUDGET_INTERNAL_URL 未配置（预算不可用）")
    if url.endswith("/internal/budget"):
        return url
    return url + "/internal/budget"


class BudgetInsufficientError(RuntimeError):
    """预算可达但额度不足（sufficient!=true 或 reason_code!=BUDGET_OK）。"""


def budget_query(min_requests: int, *, require_sufficient: bool = True, hooks) -> dict[str, Any]:
    """只读预算查询：GET {ZHIJUAN_BUDGET_INTERNAL_URL}/internal/budget?min_requests=N。

    fail-closed：任何不可达/非 200/缺字段/非法取值都抛 RuntimeError；
    预算可达但额度不足抛 BudgetInsufficientError（preflight 据此区分
    BUDGET_UNAVAILABLE 与 BUDGET_INSUFFICIENT）。

    require_sufficient=False 用于 run 结束后的账本快照：此时额度可能已被
    本次运行消耗（剩 0-n），只读取 calls/reserved_cny 差值，不应把
    "当前不足"当作运行失败。
    """
    token = os.getenv("ZHIJUAN_BUDGET_PROXY_TOKEN", "")
    if not token:
        raise RuntimeError("ZHIJUAN_BUDGET_PROXY_TOKEN 未配置（预算不可用）")
    timeout = hooks.probe_timeout()
    # 未配置 ZHIJUAN_BUDGET_INTERNAL_URL 时直接抛 RuntimeError（fail-closed，
    # 绝不回退硬编码地址）；放在 try 外以保留清晰原因，不误报"不可达"。
    endpoint = _budget_endpoint()
    try:
        status, payload = hooks._http_get(
            f"{endpoint}?min_requests={int(min_requests)}",
            timeout=timeout, token=token,
        )
    except Exception as exc:
        raise RuntimeError(f"/internal/budget 不可达: {type(exc).__name__}") from exc
    if status != 200:
        raise RuntimeError(f"/internal/budget 非 200（HTTP {status}）")
    if not isinstance(payload, dict):
        raise RuntimeError("/internal/budget 响应不是 JSON 对象")
    # 须同时满足 sufficient==true 与 reason_code=='BUDGET_OK'（job_service 受理门禁同款）。
    if (payload.get("sufficient") is not True or payload.get("reason_code") != "BUDGET_OK") \
            and require_sufficient:
        raise BudgetInsufficientError(
            f"预算不足（sufficient={payload.get('sufficient')!r} "
            f"reason_code={payload.get('reason_code')!r}）")
    return payload
