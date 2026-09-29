"""Stable import surface for the curriculum data repository."""
from .repository_loading import CurriculumRepositoryLoadingMixin
from .repository_reading import CurriculumRepositoryReadingMixin


class CurriculumRepository(CurriculumRepositoryLoadingMixin, CurriculumRepositoryReadingMixin):
    pass
