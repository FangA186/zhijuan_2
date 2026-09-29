"""Shared contract for brief, auditable solver summaries, not private reasoning."""
MAX_STEP_CHARACTERS = 500
MAX_SUMMARY_CHARACTERS = 6000
SOLVER_OUTPUT_INSTRUCTIONS = (
    '\nReturn exactly one JSON object: {"derived_answer": "short answer", '
    '"selected_option_ids": [], "steps": [{"text": "brief verifiable justification"}], '
    '"status": "PASS or REVIEW"}. Use stable option IDs for selection questions. '
    f'Use as many concise verification steps as needed, at most {MAX_STEP_CHARACTERS} '
    f'characters per step and {MAX_SUMMARY_CHARACTERS} characters in total. '
    'Do not output private reasoning.'
)


def valid_solver_steps(steps):
    if not isinstance(steps, list):
        return False
    total = 0
    for step in steps:
        if not isinstance(step, dict) or set(step) != {'text'}:
            return False
        text = step['text']
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_STEP_CHARACTERS:
            return False
        total += len(text)
        if total > MAX_SUMMARY_CHARACTERS:
            return False
    return True
