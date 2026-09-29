# Blind solver gateway

The solver runs in its own container with a private Hermes state volume and no author mounts. The only published endpoint is the narrow proxy on `127.0.0.1:8643`; it admits a public-question-only Runs request and status/stop calls. The solver has an explicit empty `api_server` toolset. Never point `HERMES_SOLVER_API_BASE_URL` at the author gateway.

Use separate random values for `HERMES_SOLVER_API_KEY` (application to proxy) and `HERMES_SOLVER_UPSTREAM_KEY` (proxy to Hermes). Set `HERMES_SOLVER_MODEL_ID` to the separately verified DeepSeek model ID; missing or mismatched values are rejected. Set `DEEPSEEK_API_KEY` only for an authorized live run.

```sh
docker compose -p zhijuan-workflow-20260922 -f infra/hermes-solver/compose.yaml build
docker compose -p zhijuan-workflow-20260922 -f infra/hermes-solver/compose.yaml up -d
```

Set `HERMES_SOLVER_API_BASE_URL=http://127.0.0.1:8643` and `HERMES_SOLVER_API_KEY` in the business process. Use `docker compose ... exec solver-hermes` to verify `/state` and `/work` contain no author files and `hermes tools list` (or the fixed vendor tool resolver) returns no tools. A GET `/v1/skills` through the proxy must return 404; a Runs request containing `session_id`, `previous_response_id`, or nested `answers` must return 400 without admission. An offline provider canary is sufficient for those negative checks; no model call is needed.
