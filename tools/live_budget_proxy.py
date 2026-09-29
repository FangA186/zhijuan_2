"""Local DeepSeek gateway with persistent per-request accounting."""
from __future__ import annotations

import argparse
import hmac
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

if __package__:
    from tools.raw_api_capture import RawCapture, apply_diagnostic_thinking
    from tools.json_format_retry import needs_format_retry, combine_attempt_usage
    from tools.deepseek_json_contract import STRICT_UPSTREAM, prepare_strict_request, unwrap_strict_response
    from tools.live_budget_ledger import RUN_NAME, MAX_BODY_BYTES, MAX_OUTPUT_TOKENS, DEFAULT_LEDGER_PATH, ALLOWED_KEYS, RESERVE_CNY, _LedgerMissingError, reserve, record_result
    from tools.live_budget_status import BudgetStatusMixin
else:
    from raw_api_capture import RawCapture, apply_diagnostic_thinking
    from json_format_retry import needs_format_retry, combine_attempt_usage
    from deepseek_json_contract import STRICT_UPSTREAM, prepare_strict_request, unwrap_strict_response
    from live_budget_ledger import RUN_NAME, MAX_BODY_BYTES, MAX_OUTPUT_TOKENS, DEFAULT_LEDGER_PATH, ALLOWED_KEYS, RESERVE_CNY, _LedgerMissingError, reserve, record_result
    from live_budget_status import BudgetStatusMixin

def forward_upstream(body: bytes, upstream_key: str) -> tuple[int, bytes]:
    request_body = prepare_strict_request(json.loads(body))
    capture = RawCapture(request_body)
    prepared = json.dumps(request_body, ensure_ascii=False).encode()
    req = urllib.request.Request(STRICT_UPSTREAM, data=prepared, method="POST", headers={
        "Authorization": f"Bearer {upstream_key}", "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            capture.write('response', status=response.status, content_type=getattr(response, 'headers', {}).get('Content-Type'))
            return response.status, unwrap_strict_response(capture.body(response.read()))
    except urllib.error.HTTPError as exc:
        capture.write('response', status=exc.code)
        capture.body(exc.read())
        return exc.code, b'{"error":"upstream_rejected"}'


class BudgetProxy(BudgetStatusMixin):
    def __init__(self, ledger: Path, internal_token: str, upstream_key: str,
                 forward: Callable[[bytes, str], tuple[int, bytes]] = forward_upstream):
        if not upstream_key:
            raise ValueError("Upstream credential is required")
        self.ledger = ledger
        self.internal_token = internal_token
        self.upstream_key = upstream_key
        self.forward = forward

    def prepare(self, path: str, authorization: str, raw: bytes) -> tuple[int, bytes]:
        if not hmac.compare_digest(authorization, f"Bearer {self.internal_token}"):
            return 401, b'{"error":"unauthorized"}'
        if path not in {"/chat/completions", "/v1/chat/completions"}:
            return 404, b'{"error":"not_found"}'
        if len(raw) > MAX_BODY_BYTES:
            return 413, b'{"error":"body_too_large"}'
        try:
            body = json.loads(raw)
            if not isinstance(body, dict) or set(body) - (ALLOWED_KEYS | {"stream_options"}):
                raise ValueError()
            if body.get("model") != "deepseek-flash" or type(body.get("stream")) not in (type(None), bool):
                raise ValueError()
            messages = body.get("messages")
            if not isinstance(messages, list) or not messages:
                raise ValueError()
            if any(not isinstance(m, dict) or set(m) != {"role", "content"}
                   or m["role"] not in {"system", "user", "assistant"}
                   or not isinstance(m["content"], str) for m in messages):
                raise ValueError()
            cap = body.get("max_tokens", MAX_OUTPUT_TOKENS)
            if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
                raise ValueError()
            if "response_format" in body and body["response_format"] not in (
                {"type": "json_object"}, {"type": "text"}):
                raise ValueError()
        except (ValueError, TypeError, KeyError):
            return 400, b'{"error":"unsupported_request"}'
        body["max_tokens"] = min(cap, MAX_OUTPUT_TOKENS)
        apply_diagnostic_thinking(body)
        body.pop("stream_options", None)
        body["stream"] = bool(body.get("stream"))
        # Canonical internal format; forward_upstream applies the native strict schema.
        body["response_format"] = {"type": "json_object"}
        prepared = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
        if len(prepared) > MAX_BODY_BYTES:
            return 413, b'{"error":"body_too_large"}'
        return 200, prepared

    def process(self, path: str, authorization: str, raw: bytes) -> tuple[int, bytes]:
        status, prepared = self.prepare(path, authorization, raw)
        if status != 200:
            return status, prepared
        body = json.loads(prepared)
        if body['stream']:
            return 400, b'{"error":"stream_requires_stream_handler"}'
        previous = None
        for attempt in range(2):
            try:
                reservation_id = reserve(self.ledger)
            except _LedgerMissingError:
                return 503, json.dumps({
                    "error": "budget_proxy_ledger_missing",
                    "reason": "预算账本不存在：旧账必须延续，不能新建空账本清零额度",
                }, ensure_ascii=False).encode()
            try:
                status, response = self.forward(prepared, self.upstream_key)
                record_result(self.ledger, reservation_id, "SUCCEEDED" if status == 200 else "UPSTREAM_ERROR",
                              status, response if status == 200 else b"")
                if status == 200 and attempt == 0 and needs_format_retry(response):
                    previous = response
                    body['messages'] = [*body['messages'], {'role': 'user', 'content':
                        'The completed response contained malformed JSON arguments. Return the same requested result using the strict function schema with valid JSON syntax.'}]
                    prepared = json.dumps(body, ensure_ascii=False).encode()
                    if len(prepared) > MAX_BODY_BYTES:
                        return status, response
                    continue
                return status, combine_attempt_usage(previous, response) if status == 200 else b'{"error":"upstream_rejected"}'
            except Exception as exc:
                print(json.dumps({"event": "proxy_request_error", "error_type": type(exc).__name__, "reservation": reservation_id}), flush=True)
                # Ambiguous upstream result keeps its reservation. No secret or body in the error.
                try:
                    record_result(self.ledger, reservation_id, "UNKNOWN")
                except Exception:
                    pass  # RESERVED is itself an unresolved charged attempt.
                return 502, b'{"error":"upstream_result_unknown"}'



def handler_for(proxy: BudgetProxy):
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, status: int, payload: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            auth = self.headers.get("Authorization", "")
            if parsed.path == "/internal/budget":
                params = urllib.parse.parse_qs(parsed.query)
                # Each value in parse_qs is a list; flatten to single str.
                flat = {k: v[0] for k, v in params.items()}
                self._send_json(*proxy.budget_status(auth, flat))
            else:
                self._send_json(*proxy.models(self.path, auth))

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                length = -1
            if length < 0 or length > MAX_BODY_BYTES:
                status, payload = 413, b'{"error":"body_too_large"}'
            else:
                raw = self.rfile.read(length)
                try:
                    streaming = json.loads(raw).get('stream') is True
                except (ValueError, AttributeError):
                    streaming = False
                if streaming:
                    if __package__:
                        from tools.live_budget_stream import serve_stream
                    else:
                        from live_budget_stream import serve_stream
                    serve_stream(self, proxy, raw)
                    return
                status, payload = proxy.process(self.path, self.headers.get("Authorization", ""), raw)
            self._send_json(status, payload)

        def log_message(self, format, *args):
            pass  # Access logs can contain request paths or credentials.

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Local DeepSeek gateway with request accounting")
    env_ledger = os.getenv("ZHIJUAN_BUDGET_LEDGER_PATH")
    parser.add_argument("--ledger", type=Path, default=env_ledger or DEFAULT_LEDGER_PATH,
                        help="Persistent SQLite path; defaults to ZHIJUAN_BUDGET_LEDGER_PATH env or built-in /tmp path")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8650)
    args = parser.parse_args()
    proxy = BudgetProxy(args.ledger, os.getenv("ZHIJUAN_BUDGET_PROXY_TOKEN", ""),
                        os.getenv("DEEPSEEK_UPSTREAM_API_KEY", ""))
    server = ThreadingHTTPServer((args.bind, args.port), handler_for(proxy))
    print(f"{RUN_NAME} budget proxy listening on {args.bind}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
