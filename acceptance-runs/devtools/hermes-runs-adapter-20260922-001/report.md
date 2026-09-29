# Hermes Runs adapter offline check

Status: OFFLINE_PASS for the local transport contract only. Real Hermes/DeepSeek execution and physical isolation are pending.

Pinned source: `install/hermes-source.lock.json` records commit `f5d192611032025d2757b07ad838921872126182`. In `vendor/hermes-agent/gateway/platforms/api_server_runs.py`, POST `/v1/runs` accepts `input`, `instructions`, `model`, `provider` and returns HTTP 202 with `run_id`. GET `/v1/runs/{run_id}` returns terminal `status`, `completed`, `partial`, `output`, and possibly `usage`; POST `/stop` requests interruption. The `run_id` is a gateway identifier, not a DeepSeek provider request ID.

Changed behavior: business author/solver calls now use native Hermes Runs. Direct DeepSeek chat and streaming entry points fail closed. A lost admission response maps to UNKNOWN and carries a deterministic Idempotency-Key; it is never blindly retried. A completed response requires `completed: true`, parseable object output, and the candidate schema for authoring. Missing usage stays empty. Solver requires a distinct configured endpoint and key.

Check: `.venv/bin/python -m unittest tests.test_hermes_adapter tests.test_hermes_runs_transport -q` — 19 tests passed. `git diff --check` on owned paths passed. `tools/project_memory.py check` reports `Handoff needs summary and next action` for the current shared workspace; this report does not treat the project ledger as passing.

Pending: Run the pinned Hermes gateway with separately verified author and solver process/container filesystem, tools, and session state. Verify provider routing and real JSON output with authorized paid calls. Integrate remaining direct callers in `services/exam/job_service.py` and `services/exam/template_parser.py`. No paid call, live gateway request, or model quality acceptance was performed.
