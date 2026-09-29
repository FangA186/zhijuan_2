"""Bounded author → check → blind solve → reviewer → revision workflow."""
import copy

from services.api.store import store
from services.diagram_assets import materialize_candidate
from services.hermes_adapter.schema_validator import validate_candidate as validate_shape
from services.validators import validate_candidate
from .generation_context import GenerationContext, GenerationFailure, author_input
from .question_review import blind_check, review_candidate, bind_review
from .spec_validation import validate_spec
from services.blueprint.topic_scope import GENERIC_TOPICS


def generate(service, local_id, exam_id='current', *, spec=None, slot=None, task_refs=None,
             run_event=lambda _: None, cancellation_requested=lambda: False, previous_questions=()):
    if cancellation_requested():
        raise GenerationFailure('CANCELLED', 'Cancelled before generation')
    spec = copy.deepcopy(spec if spec is not None else store.get_canonical_spec())
    validate_spec(spec, require_scope_confirmation=True)
    if slot is None:
        raise ValueError('A frozen blueprint slot is required')
    if spec.get('provided_materials') or slot.get('kind') == 'material_group' or slot.get('material_id'):
        raise GenerationFailure('FAILED', 'Shared-material generation is not enabled')
    if slot.get('target_topic') in GENERIC_TOPICS:
        raise GenerationFailure('FAILED', 'PLAN_TOPIC_UNRESOLVED', phase='author')
    slot = copy.deepcopy(slot)
    base_revision = slot.setdefault('question_revision_id', f'{exam_id}:{local_id}')
    ctx = GenerationContext(service.get_adapter(), spec, slot, local_id, exam_id,
                            task_refs, run_event, cancellation_requested)
    from services.validators.diversity import public_summaries
    ctx.same_paper = public_summaries(previous_questions)
    feedback = None
    for attempt in range(3):
        if attempt:
            ctx.reserve_repair()
            slot['question_revision_id'] = f'{base_revision}:repair:{attempt}'
        payload = author_input(spec, slot, local_id)
        payload['same_paper_questions'] = ctx.same_paper
        if feedback:
            payload['revision_request'] = feedback
        format_error = None
        try:
            candidate = ctx.run('author', payload, 'candidate')
        except GenerationFailure as exc:
            # Only a known completed run's rejected output is repairable. Never retry unknown execution.
            if exc.status != 'FAILED' or not str(exc).startswith('HERMES_OUTPUT_INVALID') or exc.payload is None:
                raise
            candidate, format_error = dict(exc.payload), str(exc)
        try:
            validate_shape(candidate)
        except ValueError as exc:
            format_error = format_error or str(getattr(exc, 'diagnostic_code', 'STRUCTURE_INVALID'))
        if not format_error:
            if candidate['public']['local_id'] != local_id:
                format_error = 'CANDIDATE_ID_MISMATCH'
            else:
                try:
                    candidate = materialize_candidate(candidate)
                except ValueError:
                    format_error = 'DIAGRAM_INVALID'
        validation = validate_candidate(candidate, slot, spec, materials=spec.get('provided_materials', []), previous_questions=previous_questions)
        ctx.checkpoint(candidate, validation)
        if not format_error and validation['overall_status'] != 'FAIL':
            report = blind_check(ctx, candidate)
            validation = validate_candidate(candidate, slot, spec, report, materials=spec.get('provided_materials', []), previous_questions=previous_questions)
        review = review_candidate(ctx, candidate, validation, format_error)
        ctx.checkpoint(candidate, validation, review)
        needs_repair = bool(format_error) or validation['overall_status'] == 'FAIL' or review['action'] == 'repair'
        if needs_repair and attempt < 2:
            feedback = {'previous_candidate': candidate, 'review': review, 'checks': validation,
                        'format_error': format_error, 'instruction': '修正定位的问题；保持题型、总分和课程范围，返回完整候选。'}
            continue
        if format_error:
            raise GenerationFailure('FAILED', 'HERMES_OUTPUT_INVALID:REPAIR_EXHAUSTED', phase='author')
        validation = bind_review(validation, review)
        validation['item_id'] = local_id
        ctx.checkpoint(candidate, validation, review)
        return {'candidate': candidate, 'validation': validation, 'usage': ctx.usage}
