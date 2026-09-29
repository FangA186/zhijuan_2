"""One bounded retry only for a completed response with malformed strict JSON."""
import json


def needs_format_retry(response):
    try:
        data = json.loads(response)
        return data.get('_json_contract_error') == 'INVALID_ARGUMENT_JSON'
    except (ValueError, TypeError, AttributeError):
        return False


def combine_attempt_usage(previous, current):
    """Return actual summed usage, leaving any incompletely reported field unknown."""
    if previous is None:
        return current
    try:
        first, last = json.loads(previous), json.loads(current)
        a, b = first.get('usage') or {}, last.get('usage') or {}
        usage = dict(b)
        for key in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
            values = (a.get(key), b.get(key))
            if all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in values):
                usage[key] = sum(values)
            else:
                usage.pop(key, None)
        last['usage'] = usage
        return json.dumps(last, ensure_ascii=False).encode()
    except (ValueError, TypeError, AttributeError):
        return current
