"""One frozen slot's bounded role calls; no implicit retries or budget expansion."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from reference_code.adapter_contract import RunRequest
from services.api.settings import settings

ROOT = Path(__file__).resolve().parents[2]


class GenerationFailure(RuntimeError):
    def __init__(self, status, code, *, phase=None, payload=None):
        self.status, self.phase, self.payload = status, phase, payload
        super().__init__(code)


class GenerationContext:
    def __init__(self, adapter, spec, slot, local_id, exam_id, refs, emit, cancelled):
        self.adapter, self.spec, self.slot, self.local_id = adapter, spec, slot, local_id
        self.refs = refs or {r: f'{exam_id}:{local_id}:{r}:{uuid4().hex}' for r in ('author', 'solver')}
        self.refs.setdefault('reviewer', self.refs['author'].rsplit(':author', 1)[0] + ':reviewer')
        self.emit, self.cancelled = emit, cancelled
        self.attempt, self.calls, self.usage = 0, 0, {}
        self.deadline = datetime.now(timezone.utc) + timedelta(seconds=1200)
        self.policy_hash = hashlib.sha256((ROOT / 'configs/business-policy.example.yaml').read_bytes()).hexdigest()

    def ref(self, role):
        return self.refs[role] + (f':repair:{self.attempt}' if self.attempt else '')

    def event(self, role, event, **fields):
        self.emit(dict(event=event, phase=role, attempt=self.attempt, task_ref=self.ref(role), **fields))

    def run(self, role, payload, schema):
        if self.cancelled():
            raise GenerationFailure('CANCELLED', 'Cancelled before generation', phase=role)
        if self.calls >= 9 or datetime.now(timezone.utc) >= self.deadline:
            raise GenerationFailure('BUDGET_EXCEEDED', 'REPAIR_LIMIT_EXCEEDED', phase=role)
        self.event(role, 'phase_started')
        skill = {'author': 'question-author', 'solver': 'blind-solver', 'reviewer': 'question-reviewer'}[role]
        def emit(event):
            event = dict(event)
            kind = event.pop('event')
            event.pop('task_ref', None)
            self.event(role, 'completed' if kind == 'hermes_run_completed' else kind, **event)
        self.calls += 1
        result = self.adapter.run_stage(RunRequest(
            task_ref=self.ref(role), provider='deepseek', model_id=settings.deepseek_model_id,
            role=role, input_payload=payload, schema_name=schema,
            skill_bundle_hash=hashlib.sha256((ROOT / 'skills' / skill / 'SKILL.md').read_bytes()).hexdigest(),
            policy_hash=self.policy_hash, max_iterations=1,
            deadline_utc=min(self.deadline, datetime.now(timezone.utc) + timedelta(seconds=120)).isoformat(),
            capability_grant_ref='isolated-local-generation'), emit, self.cancelled)
        self.usage[self.ref(role)] = dict(result.usage)
        if result.status != 'SUCCEEDED' or result.payload is None:
            raise GenerationFailure(result.status, result.error_code or 'Generation did not complete',
                                    phase=role, payload=result.payload)
        return dict(result.payload)

    def reserve_repair(self):
        self.attempt += 1
        self.event('author', 'repair_reserved')  # Must commit atomically before another paid call.

    def checkpoint(self, candidate, validation, review=None):
        self.event('author', 'candidate_checkpoint', checkpoint={
            'candidate': candidate, 'validation': validation, 'review': review,
            'question_revision_id': self.slot['question_revision_id']})


def author_input(spec, slot, local_id):
    selection = slot['kind'] in {'single_choice', 'multiple_choice', 'true_false'}
    skeleton = {
        'public': {'local_id': local_id, 'kind': slot['kind'], 'prompt': [{'type': 'text', 'text': '题干'}],
            'options': [{'id': v, 'content': [{'type': 'text', 'text': '选项'}]} for v in
                        (['opt_a', 'opt_b'] if slot['kind'] == 'true_false' else ['opt_a', 'opt_b', 'opt_c', 'opt_d'])] if selection else [],
            'score_x100': slot['score_x100'], 'material_ids': [], 'children': [],
            'answer_space_lines': slot.get('answer_space_lines', 2)},
        'private': {'answers': [{'local_question_id': local_id, 'answer_kind': 'selection' if selection else 'free_text',
            'correct_option_ids': [], 'accepted_answers': [], 'solution': [{'type': 'text', 'text': '简洁可核验解析'}],
            'scoring_mode': 'exclusive' if selection else 'additive',
            'partial_score_x100': spec.get('multiple_choice_partial_score_x100', 0) if slot['kind'] == 'multiple_choice' else 0,
            'rubric': [] if selection else [{'id': 'r1', 'description': '采分点', 'score_x100': slot['score_x100'], 'acceptable_variants': []}]}]}}
    return {'stage': spec['stage'], 'subject': spec['subject_label'], 'spec': spec, 'slot': slot,
            'local_id': local_id, 'output_skeleton': skeleton,
            'output_schema': json.loads((ROOT / 'contracts/candidate.schema.json').read_text()),
            'public_question_schema': json.loads((ROOT / 'contracts/public-question.schema.json').read_text())}
