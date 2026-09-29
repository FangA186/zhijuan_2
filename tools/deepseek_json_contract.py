"""Native strict function output used only as a serialization envelope.

The function is never executed and grants no tool capability. Hermes still owns
all runs; the proxy serializes the returned fields as ordinary assistant content.
Business validation remains authoritative after provider shape enforcement.
"""
import copy
import json
from functools import lru_cache
from pathlib import Path

STRICT_UPSTREAM = 'https://api.deepseek.com/beta/chat/completions'
FUNCTION_NAME = 'return_exam_json'


def strict_schema(node):
    if not isinstance(node, dict):
        return node
    allowed = {'type', 'properties', 'items', 'enum', 'anyOf', '$ref', '$defs',
               'description', 'minimum', 'maximum'}
    result = {}
    for key, value in node.items():
        if key in {'properties', '$defs'}:
            result[key] = {name: strict_schema(child) for name, child in value.items()}
        elif key in {'anyOf', 'oneOf'}:
            result['anyOf'] = [strict_schema(child) for child in value]
        elif key == 'const':
            result['enum'] = [value]
        elif key in allowed:
            result[key] = strict_schema(value) if isinstance(value, dict) else value
    if result.get('type') == 'object':
        result['required'] = list(result.get('properties', {}))
        result['additionalProperties'] = False
    return result


@lru_cache(maxsize=4)
def output_schema(role):
    root = Path(__file__).resolve().parents[1]
    path = root / 'contracts/candidate.schema.json'
    if not path.exists():
        path = Path('/app/contracts/candidate.schema.json')
    if role == 'planner':
        return strict_schema(json.loads((path.parent / 'blueprint-design.schema.json').read_text()))
    if role == 'reviewer':
        return strict_schema(json.loads((path.parent / 'question-review.schema.json').read_text()))
    candidate = strict_schema(json.loads(path.read_text()))
    definitions = candidate.pop('$defs')
    solver = strict_schema({'type': 'object', 'properties': {
        'derived_answer': {'type': 'string'},
        'selected_option_ids': {'type': 'array', 'items': {'type': 'string'}},
        'steps': {'type': 'array', 'items': {'type': 'object', 'properties': {'text': {'type': 'string'}}}},
        'status': {'type': 'string', 'enum': ['PASS', 'REVIEW']},
    }})
    if role == 'author':
        return {**candidate, '$defs': definitions}
    return solver


def prepare_strict_request(body):
    prepared = copy.deepcopy(body)
    prepared.pop('response_format', None)
    prepared.pop('stop', None)
    role = next((role for role in ('planner', 'author', 'reviewer') if any(
        f'Role: {role}.' in m.get('content', '') for m in body.get('messages', []))), 'solver')
    prepared['tools'] = [{'type': 'function', 'function': {
        'name': FUNCTION_NAME, 'description': 'Return the final requested JSON fields directly. Do not execute any action.',
        'strict': True, 'parameters': output_schema(role),
    }}]
    prepared['tool_choice'] = 'auto' if prepared.get('thinking', {}).get('type') == 'enabled' else {
        'type': 'function', 'function': {'name': FUNCTION_NAME}}
    return prepared


def unwrap_strict_response(raw):
    envelope = json.loads(raw)
    choices = envelope.get('choices') or []
    if not choices:
        return raw
    choice = choices[0]
    message = choice.get('message') or {}
    calls = message.get('tool_calls') or []
    if not calls and choice.get('finish_reason') == 'stop' and isinstance(message.get('content'), str):
        choice['message'] = {'role': 'assistant', 'content': message['content']}
        return json.dumps(envelope, ensure_ascii=False).encode()
    # Do not synthesize success for truncated, missing, or unexpected calls.
    content = ''
    diagnostic = {'call_count': len(calls), 'finish_reason': choice.get('finish_reason')}
    if choice.get('finish_reason') in {'stop', 'tool_calls'} and len(calls) == 1:
        function = calls[0].get('function') or {}
        diagnostic['expected_function'] = function.get('name') == FUNCTION_NAME
        diagnostic['argument_type'] = type(function.get('arguments')).__name__
        if function.get('name') == FUNCTION_NAME:
            try:
                value = json.loads(function['arguments'])
                diagnostic['arguments_valid_json'] = True
                diagnostic['result_is_object'] = isinstance(value, dict)
                if isinstance(value, dict):
                    content = json.dumps(value, ensure_ascii=False)
            except (ValueError, KeyError, TypeError) as exc:
                diagnostic['error_type'] = type(exc).__name__
                if isinstance(exc, json.JSONDecodeError):
                    diagnostic['error_position'] = exc.pos
                    diagnostic['argument_length'] = len(exc.doc)
                diagnostic['arguments_valid_json'] = False
    if not content:
        print(json.dumps({'strict_output_rejected': diagnostic}), flush=True)
        if diagnostic.get('error_type') == 'JSONDecodeError':
            envelope['_json_contract_error'] = 'INVALID_ARGUMENT_JSON'
    message = {'role': 'assistant', 'content': content}
    choice['message'] = message
    if content:
        choice['finish_reason'] = 'stop'
    return json.dumps(envelope, ensure_ascii=False).encode()
