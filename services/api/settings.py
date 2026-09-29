"""API Configuration and environment loading.

Adheres to AGENTS.md rules:
- Does not log or leak raw secrets.
- Loads DEEPSEEK_API_KEY from environment or .env.
"""
from __future__ import annotations
import os
from pathlib import Path
from pydantic import BaseModel, Field

def _load_env_file() -> None:
    if os.getenv("ZHIJUAN_SKIP_DOTENV") == "1":
        return
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

_load_env_file()

class Settings(BaseModel):
    app_title: str = "知卷 AI 原创命题服务"
    app_version: str = "1.4.0"
    host: str = "127.0.0.1"
    port: int = 8000
    deepseek_api_key: str = Field(default_factory=lambda: os.environ.get("DEEPSEEK_API_KEY", "").strip())
    deepseek_base_url: str = Field(default_factory=lambda: os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"))
    deepseek_model_id: str = Field(default_factory=lambda: os.environ.get("ZHIJUAN_DEEPSEEK_MODEL_ID", "deepseek-chat").strip())
    # Local generation runtime (contract C4). Same env keys are read elsewhere
    # via os.getenv; these defaults are the single source for the API layer.
    runtime_id: str = Field(default_factory=lambda: os.environ.get("ZHIJUAN_RUNTIME_ID", "zhijuan-local").strip())
    budget_internal_url: str = Field(default_factory=lambda: os.environ.get("ZHIJUAN_BUDGET_INTERNAL_URL", "http://127.0.0.1:8650/internal/budget").rstrip("/"))
    budget_proxy_token: str = Field(default_factory=lambda: os.environ.get("ZHIJUAN_BUDGET_PROXY_TOKEN", "").strip())
    budget_ledger_path: str = Field(default_factory=lambda: os.environ.get("ZHIJUAN_BUDGET_LEDGER_PATH", "/tmp/zhijuan-workflow-20260922/budget/acceptance.sqlite").strip())
    heartbeat_ttl_seconds: float = Field(default_factory=lambda: float(os.environ.get("ZHIJUAN_HEARTBEAT_TTL_SECONDS", "20")))
    readiness_probe_timeout: float = Field(default_factory=lambda: float(os.environ.get("ZHIJUAN_READINESS_PROBE_TIMEOUT", "2.0")))
    readiness_cache_ttl: float = Field(default_factory=lambda: float(os.environ.get("ZHIJUAN_READINESS_CACHE_TTL", "3.0")))
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ]

settings = Settings()
