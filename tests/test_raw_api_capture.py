import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.raw_api_capture import RawCapture, apply_diagnostic_thinking
from tools.raw_api_server import read_records
from tools.deepseek_json_contract import prepare_strict_request, unwrap_strict_response
from tools.live_budget_stream import output_chunks


class RawApiTests(unittest.TestCase):
    def test_exact_provider_lines_include_reasoning_and_tools_before_conversion(self):
        wire = [b': heartbeat\r\n', b'\r\n',
            b'data: {"choices":[{"delta":{"reasoning_content":"sample-reasoning"}}]}\r\n',
            b'\r\n', b'data: [DONE]\n', b'\n']
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ', {'ZHIJUAN_RAW_API_DIR': directory}), \
             contextlib.redirect_stdout(io.StringIO()) as printed:
            capture = RawCapture({'model': 'test', 'thinking': {'type': 'enabled'}, 'api_key': 'never-log-this'})
            self.assertEqual(list(capture.lines(wire)), wire)
            path = Path(directory) / 'responses.ndjson'
            records = list(read_records(path))
            self.assertEqual(''.join(r['raw'] for _,r in records if 'raw' in r).encode(), b''.join(wire))
            self.assertEqual(list(read_records(path, records[-1][0])), [])
            self.assertIn('sample-reasoning', printed.getvalue())
            self.assertNotIn('never-log-this', path.read_text())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_no_capture_without_opt_in(self):
        with patch.dict('os.environ', {'ZHIJUAN_RAW_API_DIR': ''}), contextlib.redirect_stdout(io.StringIO()) as out:
            capture = RawCapture({})
            capture.body(b'data: test\n')
            self.assertEqual(out.getvalue(), '')

    def test_partial_disk_record_waits_until_newline(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'responses.ndjson'
            path.write_bytes(b'{"raw":"x"}')
            self.assertEqual(list(read_records(path)), [])
            with path.open('ab') as stream: stream.write(b'\n')
            self.assertEqual(list(read_records(path))[0][1]['raw'], 'x')

    def test_thinking_mode_uses_auto_and_remains_explicit(self):
        body = {'messages': [], 'model': 'test'}
        with patch.dict('os.environ', {'ZHIJUAN_DIAGNOSTIC_THINKING': 'enabled'}):
            apply_diagnostic_thinking(body)
        self.assertEqual(body['thinking'], {'type': 'enabled'})
        self.assertEqual(prepare_strict_request(body)['tool_choice'], 'auto')
        with patch.dict('os.environ', {'ZHIJUAN_DIAGNOSTIC_THINKING': 'disabled'}):
            apply_diagnostic_thinking(body)
        self.assertIsInstance(prepare_strict_request(body)['tool_choice'], dict)

    def test_auto_tool_choice_can_return_content_without_a_tool(self):
        frames = ['data: '+json.dumps({'choices':[{'delta':{'content':'{"x":1}'},'finish_reason':None}]}),
                  'data: '+json.dumps({'choices':[{'delta':{},'finish_reason':'stop'}]}), 'data: [DONE]']
        chunks = list(output_chunks(frames))
        self.assertEqual(chunks[0]['choices'][0]['delta']['content'], '{"x":1}')
        raw = json.dumps({'choices':[{'message':{'content':'{"x":1}'},'finish_reason':'stop'}]}).encode()
        self.assertEqual(json.loads(unwrap_strict_response(raw))['choices'][0]['message']['content'], '{"x":1}')

    def test_capture_cap_is_visible_not_silent(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ', {'ZHIJUAN_RAW_API_DIR':directory}), \
             patch('tools.raw_api_capture.MAX_BYTES', 1), contextlib.redirect_stdout(io.StringIO()):
            capture = RawCapture({})
            capture.body(b'data: should-not-fit')
            records = list(read_records(Path(directory)/'responses.ndjson'))
            self.assertEqual(records[-1][1]['kind'], 'capture_stopped')

    def test_adapter_capture_has_its_own_source(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ', {'ZHIJUAN_RAW_API_DIR':directory}), \
             contextlib.redirect_stdout(io.StringIO()):
            capture=RawCapture({'model':'test','role':'author'},source='hermes-adapter')
            record=list(read_records(Path(directory)/'responses.ndjson'))[0][1]
            self.assertEqual(record['source'],'hermes-adapter')
            self.assertEqual(record['role'],'author')
