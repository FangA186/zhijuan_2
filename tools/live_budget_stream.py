"""Native provider stream, strict function arguments → assistant output; no reasoning."""
import json
import urllib.request
import urllib.error

if __package__:
    from tools.raw_api_capture import RawCapture
    from tools.deepseek_json_contract import STRICT_UPSTREAM, FUNCTION_NAME, prepare_strict_request
    from tools.live_budget_ledger import reserve, record_result, _LedgerMissingError
else:
    from raw_api_capture import RawCapture
    from deepseek_json_contract import STRICT_UPSTREAM, FUNCTION_NAME, prepare_strict_request
    from live_budget_ledger import reserve, record_result, _LedgerMissingError


def output_chunks(lines, diagnostics=None):
    diagnostics = diagnostics if diagnostics is not None else {}
    arguments, name, finished, has_content = '', '', False, False
    usage, model, request_id = {}, None, None
    for line in lines:
        line = line.decode() if isinstance(line, bytes) else line
        if not line.startswith('data:'):
            continue
        raw = line[5:].strip()
        if raw == '[DONE]':
            break
        event = json.loads(raw)
        diagnostics['frames'] = diagnostics.get('frames', 0) + 1
        if event.get('error'):
            raise ValueError('provider_stream_error')
        request_id, model = event.get('id', request_id), event.get('model', model)
        if isinstance(event.get('usage'), dict):
            usage = event['usage']
        for choice in event.get('choices', []):
            if choice.get('index', 0) != 0:
                raise ValueError('multiple_choices')
            delta = choice.get('delta') or {}
            diagnostics['delta_fields'] = sorted(set(diagnostics.get('delta_fields', [])) | set(delta))
            if delta.get('content'):
                has_content = True
                yield {'id': request_id, 'model': model, 'object': 'chat.completion.chunk',
                       'choices': [{'index': 0, 'delta': {'content': delta['content']}, 'finish_reason': None}]}
            # Raw reasoning is captured separately; normal exam output retains its public contract.
            for call in delta.get('tool_calls') or []:
                if call.get('index', 0) != 0:
                    raise ValueError('multiple_functions')
                function = call.get('function') or {}
                name += function.get('name') or ''
                text = function.get('arguments') or ''
                if text:
                    if name != FUNCTION_NAME:
                        raise ValueError('unexpected_function')
                    arguments += text
                    diagnostics['argument_characters'] = len(arguments)
                    yield {'id': request_id, 'model': model, 'object': 'chat.completion.chunk',
                           'choices': [{'index': 0, 'delta': {'content': text}, 'finish_reason': None}]}
            if choice.get('finish_reason'):
                diagnostics['finish_reason'] = choice['finish_reason']
                if choice['finish_reason'] not in {'stop', 'tool_calls'}:
                    raise ValueError('incomplete_output')
                finished = True
    if not finished or (name != FUNCTION_NAME and not (not name and has_content)):
        raise ValueError('invalid_output')
    yield {'id': request_id, 'model': model, 'object': 'chat.completion.chunk', 'usage': usage,
           'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]}


def serve_stream(handler, proxy, raw):
    status, prepared = proxy.prepare(handler.path, handler.headers.get('Authorization', ''), raw)
    if status != 200:
        handler._send_json(status, prepared)
        return
    try:
        reservation = reserve(proxy.ledger)
    except _LedgerMissingError:
        handler._send_json(503, b'{"error":"budget_proxy_ledger_missing"}')
        return
    started, usage, model, request_id = False, {}, None, None
    diagnostics = {}
    capture = None
    try:
        body = prepare_strict_request(json.loads(prepared))
        body['stream_options'] = {'include_usage': True}
        capture = RawCapture(body)
        request = urllib.request.Request(STRICT_UPSTREAM, data=json.dumps(body).encode(), method='POST',
            headers={'Authorization': f'Bearer {proxy.upstream_key}', 'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=120) as response:
            capture.write('response', status=response.status, content_type=response.headers.get('Content-Type'))
            handler.send_response(200)
            handler.send_header('Content-Type', 'text/event-stream')
            handler.send_header('Cache-Control', 'no-cache')
            handler.end_headers()
            started = True
            for chunk in output_chunks(capture.lines(response), diagnostics):
                usage = chunk.get('usage', usage)
                model, request_id = chunk.get('model'), chunk.get('id')
                handler.wfile.write(b'data: ' + json.dumps(chunk, ensure_ascii=False).encode() + b'\n\n')
                handler.wfile.flush()
        record_result(proxy.ledger, reservation, 'SUCCEEDED', 200,
                      json.dumps({'usage': usage, 'model': model, 'id': request_id}).encode())
        handler.wfile.write(b'data: [DONE]\n\n')
        handler.wfile.flush()
    except Exception as exc:
        if capture and isinstance(exc, urllib.error.HTTPError):
            capture.write('response', status=exc.code)
            capture.body(exc.read())
        known = {'provider_stream_error', 'multiple_choices', 'multiple_functions', 'unexpected_function', 'incomplete_output', 'invalid_output'}
        diagnostics.update(event='stream_contract_error', reservation=reservation, error_type=type(exc).__name__,
                           code=str(exc) if isinstance(exc, ValueError) and str(exc) in known else 'stream_transport_error')
        print(json.dumps(diagnostics), flush=True)
        record_result(proxy.ledger, reservation, 'UNKNOWN')
        # No replay after output has begun: the provider may already have billed this run.
        if started:
            handler.wfile.write(b'data: {"error":{"message":"provider_stream_incomplete"}}\n\n')
            handler.wfile.flush()
        else:
            handler._send_json(502, b'{"error":"upstream_result_unknown"}')
