"""Pure snapshot updates, executed under the repository's transaction/version fence."""
import copy
import json
from datetime import datetime, timezone

from services.hermes_adapter.run_stream import safe_text

MAX_REPAIRS = 2
MAX_ACTIVITY_CHARS = 1_000_000


def append_activity(job, slot_id, phase, attempt, data, run_id=None):
    activity = job.setdefault('activity', [])
    kind = data.get('event', 'status')
    # Explicit wire fields only. Never persist private reasoning or arbitrary envelope data.
    fields = {k: safe_text(v) if isinstance(v, str) else v for k, v in data.items()
              if k in {'event', 'delta', 'text', 'output', 'error', 'status', 'tool', 'duration'}
              and isinstance(v, (str, int, float, bool))}
    message = fields.get('delta') or fields.get('output') or fields.get('text') or fields.get('error') or fields.get('status') or kind
    tail = activity[-1] if activity else {}
    if kind == 'message.delta' and all(tail.get(k) == v for k, v in
            [('kind', kind), ('slot_id', slot_id), ('role', phase), ('attempt', attempt)]):
        tail['message'] += message
        tail['data']['delta'] += message
    else:
        job['activity_seq'] = job.get('activity_seq', 0) + 1
        activity.append({'id': job['activity_seq'], 'timestamp': datetime.now(timezone.utc).isoformat(),
                         'role': phase, 'slot_id': slot_id, 'attempt': attempt, 'run_id': run_id,
                         'kind': kind, 'level': 'error' if fields.get('error') else 'info',
                         'message': message, 'data': fields})
    # ponytail: snapshot tail capped at 1M chars; move to an event table for longer runs.
    while activity and (sum(len(x['message']) for x in activity) > MAX_ACTIVITY_CHARS or len(activity) > 2000):
        activity.pop(0)
        job['activity_dropped'] = job.get('activity_dropped', 0) + 1


def apply_run_event(job, slot, event):
    phase, kind = event.get('phase'), event.get('event')
    attempt = event.get('attempt', 0)
    if phase not in {'author', 'solver', 'reviewer'} or type(attempt) is not int or not 0 <= attempt <= MAX_REPAIRS:
        raise ValueError('Unsupported run phase or repair attempt')
    allowed = {'phase_started', 'hermes_run_admitted', 'completed', 'activity', 'repair_reserved', 'candidate_checkpoint'}
    if kind not in allowed:
        raise ValueError('Unsupported run event')
    ref = f"{job['job_id']}:{slot['slot_id']}:{phase}" + (f':repair:{attempt}' if attempt else '')
    if event.get('task_ref') != ref:
        raise ValueError('Unexpected task reference')
    reserved = slot.get('repair_attempt', 0)
    if kind == 'repair_reserved':
        if phase != 'author' or attempt != reserved + 1:
            raise ValueError('Repair quota or sequence violated')
        slot['repair_attempt'] = attempt
    elif attempt != reserved:
        raise ValueError('Unreserved or stale repair attempt')
    key = phase + (f':repair:{attempt}' if attempt else '')
    record = job.setdefault('run_refs', {}).setdefault(slot['slot_id'], {}).setdefault(key, {})
    if kind == 'phase_started' and record.get('state') not in {None, 'repair_reserved'}:
        raise ValueError('Run already started; reconcile instead of readmitting')
    record.update(task_ref=ref, state=kind)
    if kind == 'hermes_run_admitted':
        run_id = event.get('run_id')
        if not run_id or record.get('run_id') not in (None, run_id):
            raise ValueError('Missing or conflicting Hermes run id')
        record['run_id'] = run_id
    if kind == 'completed':
        record['usage'] = {k: v for k, v in event.get('usage', {}).items()
                           if k in {'input_tokens', 'output_tokens', 'total_tokens'} and type(v) is int and v >= 0}
        records = [r for phases in job['run_refs'].values() for r in phases.values()]
        job['tokens_used_known'] = sum(r.get('usage', {}).get('total_tokens', 0) for r in records)
        job['tokens_used'] = None  # Future repairs/calls remain unknown until the job settles.
        job['usage_status'] = 'PARTIAL_UNKNOWN'
    if kind == 'candidate_checkpoint':
        record['checkpoint'] = copy.deepcopy(event['checkpoint'])
    if kind == 'activity':
        append_activity(job, slot['slot_id'], phase, attempt, event.get('data', {}), record.get('run_id'))
    elif kind != 'candidate_checkpoint':
        append_activity(job, slot['slot_id'], phase, attempt, {'event': kind}, record.get('run_id'))
