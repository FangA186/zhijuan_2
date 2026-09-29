"""Generate frozen slots through Hermes, then collect independent, version-bound checks."""
from __future__ import annotations

from typing import Any
from ..api.store import store
from ..api.settings import settings
from ..hermes_adapter.adapter import HermesDeepSeekAdapter
from .generation_context import GenerationFailure


class QuestionService:
    @staticmethod
    def get_adapter() -> HermesDeepSeekAdapter:
        return HermesDeepSeekAdapter(default_model=settings.deepseek_model_id, timeout=120)

    @staticmethod
    def _current_results(exam_id: str):
        from .job_service import GenerationJobService
        if not __import__('os').getenv('DATABASE_URL'):
            return None
        repo = GenerationJobService.repository()
        job = GenerationJobService.get_current_job(exam_id)
        if job:
            return repo.results(job['job_id'])
        return []

    @classmethod
    def list_candidates(cls, exam_id: str = 'current') -> list[dict[str, Any]]:
        results = cls._current_results(exam_id)
        return [r['candidate'] for r in results] if results is not None else store.get_candidates()

    @classmethod
    def get_validation(cls, exam_id: str = 'current') -> dict:
        results = cls._current_results(exam_id)
        return {r['candidate']['public']['local_id']:r['validation'] for r in results} if results is not None else store.get_validation()

    @classmethod
    def get_candidate(cls, local_id: str, exam_id: str = 'current') -> dict | None:
        return next((c for c in cls.list_candidates(exam_id) if c.get('public', {}).get('local_id') == local_id), None)

    @classmethod
    def update_candidate(cls, candidate: dict, exam_id: str = 'current') -> dict:
        # Editing a persisted generation result needs its own revision transaction (M2-05).
        if cls._current_results(exam_id) is not None:
            raise ValueError('Persisted result editing requires the versioned revision workflow')
        from ..hermes_adapter.schema_validator import validate_candidate as validate_structure
        validate_structure(candidate)
        return store.update_candidate(candidate)

    @classmethod
    def generate_slot_result(cls, local_id: str, exam_id: str = 'current', **kwargs) -> dict:
        from .question_generation import generate
        return generate(cls, local_id, exam_id, **kwargs)

    @classmethod
    def regenerate_question_slot(cls, local_id: str, exam_id: str = 'current') -> dict:
        # Until per-question revision jobs are integrated, never make synchronous untracked calls.
        raise ValueError('Single-question regeneration requires a versioned queued job; use a confirmed full blueprint')
