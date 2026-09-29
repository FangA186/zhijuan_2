"""Guard the split publication mixin's local serialization path."""
import unittest
from types import SimpleNamespace

from services.api.store_publication import ExamStorePublicationMixin


class PublicationMixinTests(unittest.TestCase):
    def test_approved_candidate_serializes_and_records_snapshot(self):
        state = SimpleNamespace(
            candidates=[{"public": {"local_id": "q1"}}],
            validation={"q1": {"overall_status": "PASS"}},
            adjudications={}, blueprint={"revision": 1},
            publications={}, published_exams=[], spec={"title": "Fixture"},
        )
        publication = ExamStorePublicationMixin.publish_exam(state, "fixture", {})
        self.assertEqual(publication["status"], "PUBLISHED")
        self.assertEqual(state.published_exams[0]["exam_id"], "fixture")


if __name__ == "__main__":
    unittest.main()
