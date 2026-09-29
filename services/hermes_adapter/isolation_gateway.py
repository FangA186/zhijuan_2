"""Narrow solver-only HTTP admission boundary in front of isolated Hermes Runs."""
from __future__ import annotations
if __package__:
    from .solver_output import SOLVER_OUTPUT_INSTRUCTIONS
else:
    from solver_output import SOLVER_OUTPUT_INSTRUCTIONS

import hmac
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

RUN_PATH = re.compile(r"^/v1/runs/(run_[A-Za-z0-9_-]+)(/stop|/events)?$")
FORBIDDEN = frozenset({"private", "answers", "solution", "rubric", "accepted_answers",
                       "correct_option_ids", "answer_text", "explanation", "scoring_rubric", "scoring_mode", "partial_score_x100"})
QUESTION_KEYS = {"local_id", "kind", "prompt", "options", "score_x100", "material_ids", "children", "answer_space_lines"}
BLOCK_KEYS = {"text": {"type", "text"}, "math": {"type", "latex"},
              "asset": {"type", "asset_id", "alt"}, "table": {"type", "headers", "rows"}}


def validate_public_question(question: object) -> None:
    if not isinstance(question, dict) or set(question) != QUESTION_KEYS:
        raise ValueError("unexpected question field")
    def blocks(items: object) -> None:
        if not isinstance(items, list):
            raise ValueError("invalid blocks")
        for block in items:
            if not isinstance(block, dict) or set(block) != BLOCK_KEYS.get(block.get("type")):
                raise ValueError("unexpected block field")
    blocks(question.get("prompt"))
    if not isinstance(question.get("options"), list) or not isinstance(question.get("children"), list):
        raise ValueError("invalid options or children")
    for option in question["options"]:
        if not isinstance(option, dict) or set(option) != {"id", "content"}:
            raise ValueError("unexpected option field")
        blocks(option["content"])
    for child in question["children"]:
        validate_public_question(child)


def validate_solver_run(body: object) -> dict:
    if not isinstance(body, dict) or set(body) != {"provider", "model", "instructions", "input"}:
        raise ValueError("unexpected run fields")
    expected_model = os.getenv("HERMES_SOLVER_MODEL_ID")
    if body["provider"] != "deepseek" or not expected_model or body["model"] != expected_model:
        raise ValueError("invalid model route")
    if not isinstance(body["instructions"], str) or "Role: solver." not in body["instructions"]:
        raise ValueError("solver role required")
    if not isinstance(body["input"], str):
        raise ValueError("invalid input")
    content = json.loads(body["input"])
    if not isinstance(content, dict) or set(content) != {"public_question"}:
        raise ValueError("unexpected solver input")
    def reject(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in FORBIDDEN:
                    raise ValueError("private field rejected")
                reject(item)
        elif isinstance(value, list):
            for item in value:
                reject(item)
    reject(content)
    validate_public_question(content["public_question"])
    return content["public_question"]


class Handler(BaseHTTPRequestHandler):
    _CONFIG_VERSION = 2

    def _internal_readiness(self) -> bool:
        if not hmac.compare_digest(self.headers.get("Authorization", ""),
                                   f"Bearer {os.getenv('HERMES_SOLVER_API_KEY', '')}"):
            self.send_error(401)
            return False
        payload = json.dumps({
            "status": "OK",
            "service": "zhijuan-solver-gateway",
            "config_version": self._CONFIG_VERSION,
            # Non-secret routing identity only: role boundaries, model whitelist
            # and upstream endpoint presence. Nothing here forwards any request.
            "role": "solver",
            "model": os.getenv("HERMES_SOLVER_MODEL_ID", ""),
            "upstream_configured": bool(os.environ.get("HERMES_SOLVER_UPSTREAM_URL")),
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        return True

    def _forward(self, method: str) -> None:
        if self.path == "/internal/readiness" and method == "GET":
            self._internal_readiness()
            return
        key = os.environ["HERMES_SOLVER_API_KEY"]
        if not hmac.compare_digest(self.headers.get("Authorization", ""), f"Bearer {key}"):
            self.send_error(401)
            return
        path = self.path
        if method == "POST" and path == "/v1/runs":
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 100000:
                    raise ValueError("invalid size")
                data = self.rfile.read(size)
                public_question = validate_solver_run(json.loads(data))
                skill = open("/app/blind-solver/SKILL.md", encoding="utf-8").read()
                data = json.dumps({"provider": "deepseek", "model": json.loads(data)["model"],
                                   "instructions": skill + SOLVER_OUTPUT_INSTRUCTIONS + "\n题型：" + public_question["kind"] + "。multiple_choice是多项选择，必须列出全部正确选项，不得按单选题作答。",
                                   "input": json.dumps({"public_question": public_question}, ensure_ascii=False)},
                                  ensure_ascii=False).encode()
            except (ValueError, TypeError, json.JSONDecodeError):
                self.send_error(400)
                return
        elif RUN_PATH.fullmatch(path) and (method == "GET" and not path.endswith("/stop") or method == "POST" and path.endswith("/stop")):
            data = None
        else:
            self.send_error(404)
            return
        headers = {"Authorization": f"Bearer {os.environ['HERMES_SOLVER_UPSTREAM_KEY']}"}
        if data is not None:
            headers["Content-Type"] = "application/json"
            if idem := self.headers.get("Idempotency-Key"):
                headers["Idempotency-Key"] = idem
        request = Request(os.environ["HERMES_SOLVER_UPSTREAM_URL"] + path,
                          data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=30) as response:
                if path.endswith('/events'):
                    self.send_response(response.status)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    for line in response:
                        self.wfile.write(line)
                        self.wfile.flush()
                    return
                status, result = response.status, response.read(1000000)
        except HTTPError as exc:
            status, result = exc.code, exc.read(1000000)
        except URLError:
            self.send_error(502)
            return
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(result)))
        self.end_headers()
        self.wfile.write(result)

    def do_POST(self) -> None:
        self._forward("POST")

    def do_GET(self) -> None:
        self._forward("GET")


if __name__ == "__main__":
    if not os.environ.get("HERMES_SOLVER_API_KEY") or not os.environ.get("HERMES_SOLVER_UPSTREAM_KEY"):
        raise SystemExit("solver keys required")
    ThreadingHTTPServer(("0.0.0.0", 8643), Handler).serve_forever()
