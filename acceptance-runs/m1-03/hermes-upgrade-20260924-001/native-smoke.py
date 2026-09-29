"""Run against the new image without network or provider credentials."""
import json
import importlib.metadata
from unittest.mock import MagicMock
from agent.message_sanitization import _repair_tool_call_arguments
from gateway.config import PlatformConfig
from gateway.platforms.api_server import APIServerAdapter

assert importlib.metadata.version('hermes-agent') == '0.21.5'
assert json.loads(_repair_tool_call_arguments('{"a": [{"b": 1}, {"c": 2}}]}')) == {'a':[{'b':1},{'c':2}]}
assert _repair_tool_call_arguments('{"q":"unterminated') == '{}'
adapter=APIServerAdapter(PlatformConfig(enabled=True))
agent=MagicMock()
adapter._active_run_agents={'run-synthetic':agent}
adapter._run_statuses={'run-synthetic':{'status':'running'}}
assert adapter.interrupt_active_runs('synthetic shutdown') == 1
assert adapter._run_statuses['run-synthetic']['status'] == 'interrupted'
agent.interrupt.assert_called_once()
print('PASS: package version, nested JSON repair, fail-closed string truncation, native interrupted state')
