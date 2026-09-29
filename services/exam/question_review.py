"""Advisory review contract and version-bound evidence; never grants approval."""
import hashlib
import json
import jsonschema

from services.api.settings import settings
from services.hermes_adapter.blind_runtime import BlindSolverRuntime
from services.hermes_adapter.comparator import compare_answers
from services.hermes_adapter.solver_output import valid_solver_steps
from .generation_context import GenerationFailure

from services.hermes_adapter.schema_validator import load_schema

REVIEW_SCHEMA = load_schema('question-review.schema.json')


def review_candidate(ctx, candidate, validation, format_error):
    review = ctx.run('reviewer', {'candidate': candidate, 'validation': validation,
        'format_error': format_error, 'spec': ctx.spec, 'slot': ctx.slot,
        'same_paper_questions': getattr(ctx, 'same_paper', []),
        'question_revision_id': ctx.slot['question_revision_id'], 'output_schema': REVIEW_SCHEMA}, 'question_review')
    try:
        jsonschema.validate(review, REVIEW_SCHEMA)
        if review['question_revision_id'] != ctx.slot['question_revision_id']:
            raise ValueError('Stale reviewer revision')
    except (jsonschema.ValidationError, ValueError) as exc:
        raise GenerationFailure('FAILED', 'REVIEW_OUTPUT_INVALID', phase='reviewer') from exc
    return review


def blind_check(ctx, candidate):
    public = BlindSolverRuntime(ctx.adapter).prepare_blind_input(candidate['public'])
    def has_material(node):
        return bool(node.get('material_ids')) or any(has_material(c) for c in node.get('children', []))
    if has_material(public):
        raise GenerationFailure('FAILED', 'Shared-material generation is not enabled')
    solved = ctx.run('solver', {'public_question': public}, 'blind_solver')
    if not isinstance(solved.get('derived_answer'), str) or not isinstance(solved.get('selected_option_ids'), list):
        raise GenerationFailure('FAILED', 'Blind output has no structured answer', phase='solver')
    if any(not isinstance(option, str) for option in solved['selected_option_ids']):
        raise GenerationFailure('FAILED', 'Blind option IDs must be strings', phase='solver')
    if not valid_solver_steps(solved.get('steps', [])):
        raise GenerationFailure('FAILED', 'Blind output must contain only short verifiable steps', phase='solver')
    reference = next((a for a in candidate['private']['answers'] if a['local_question_id'] == ctx.local_id), {})
    accepted = reference.get('accepted_answers', [])
    return compare_answers(reference.get('answer_text') or (accepted[0].get('value', '') if accepted else ''),
        reference.get('correct_option_ids'), solved['derived_answer'], solved['selected_option_ids'],
        settings.deepseek_model_id, steps=solved.get('steps', [])).to_dict()


def bind_review(validation, review):
    validation['reviewer_report'] = review
    validation['rule_checks'].append({
        'rule_id': 'AGENT_REVIEW', 'check_code': 'AGENT_REVIEW', 'category': 'model_comparison',
        'name': 'AGENT_REVIEW', 'status': 'REVIEW', 'severity': 'info', 'manual_allowed': True,
        'evidence_type': 'model', 'content_hash': validation['content_hash'],
        'evidence_summary': review['summary'], 'checker_id': 'question-reviewer', 'checker_version': '1'})
    validation['evidence_hash'] = hashlib.sha256(json.dumps(
        {k: v for k, v in validation.items() if k != 'evidence_hash'},
        ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return validation
