# Hermes Runs identity and cancellation offline regression

Pinned vendor evidence: `vendor/hermes-agent/gateway/platforms/api_server_runs.py:161-180` sets `run_id` on every pollable status; `:753-757` returns that status from GET `/v1/runs/{run_id}`.

Before fix, three new MockTransport reproductions failed: a mismatched or absent status `run_id` returned SUCCEEDED; an admission event exception escaped after POST without `/stop`; and cancellation during terminal GET returned SUCCEEDED. A fourth test exposed cancellation becoming true during the completion event. These are fixed in `services/hermes_adapter/http_adapter.py`; cancellation callback failure before admission now returns UNKNOWN without POST, and after admission requests best-effort stop and returns UNKNOWN.

Command: `.venv/bin/python -m unittest tests.test_hermes_runs_transport tests.test_hermes_adapter -q` — 27 tests passed. `git diff --check -- services/hermes_adapter/http_adapter.py tests/test_hermes_runs_transport.py` — passed. No network or paid model call.

Related test outside this ownership: `tests/test_blind_isolation.py` still contains a GET mock status without the pinned vendor `run_id` field, so its positive path fails with `HERMES_STATUS_RUN_ID_MISMATCH` until the owning agent updates that fixture. This is a fixture contract mismatch, not a production exception to identity validation.
