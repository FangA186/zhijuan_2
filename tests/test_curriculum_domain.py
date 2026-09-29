"""Unit tests for Curriculum domain models, repository, and service."""
from __future__ import annotations
import unittest
from services.curriculum import (
    CurriculumService,
    CurriculumRepository,
    CurriculumFilter,
    TextbookMaterial,
    ChapterNode,
)


class TestCurriculumDomain(unittest.TestCase):
    def setUp(self):
        self.service = CurriculumService()

    def test_get_tags(self):
        tags = self.service.get_tags()
        self.assertIsInstance(tags, dict)
        self.assertIn("hierarchies", tags)

    def test_search_materials_high_school_math_editions(self):
        """Verify that high school math can return all editions (at least 7 versions)."""
        res = self.service.search_materials(CurriculumFilter(
            stage="高中",
            subject="数学",
            mode="visible",
        ))
        self.assertGreater(res.total, 0)
        editions = {item.get("dims", {}).get("zxxbb", {}).get("name") for item in res.items if item.get("dims", {}).get("zxxbb")}
        self.assertGreaterEqual(len(editions), 7)
        self.assertIn("人教A版", editions)
        self.assertTrue(any("B版" in ed for ed in editions))
        self.assertIn("北师大版", editions)

    def test_search_mode_all_vs_visible(self):
        """Check that 'all' includes hidden or unlisted materials."""
        vis_res = self.service.search_materials(CurriculumFilter(mode="visible"))
        all_res = self.service.search_materials(CurriculumFilter(mode="all"))
        self.assertGreaterEqual(all_res.total, vis_res.total)
        self.assertEqual(all_res.total, 3209)

    def test_chapter_tree_and_topic_extraction(self):
        """Test getting chapter tree and extracting candidate topic strings."""
        # Query any material that has chapters
        res = self.service.search_materials(CurriculumFilter(
            stage="高中",
            subject="数学",
            edition="人教A版",
            limit=5,
        ))
        self.assertGreater(len(res.items), 0)
        mat_id = res.items[0]["id"]
        
        tree = self.service.get_chapter_tree(mat_id)
        if tree:
            self.assertIsInstance(tree, list)
            topics = self.service.extract_key_topics(mat_id)
            self.assertIsInstance(topics, list)
            self.assertGreater(len(topics), 0)
            # Ensure ignored titles are filtered
            for ignored in ["目录", "正文", "本书说明"]:
                self.assertFalse(any(ignored == t for t in topics))

    def test_nonexistent_material(self):
        mat = self.service.get_material("non_existent_id_999999")
        self.assertIsNone(mat)
        tree = self.service.get_chapter_tree("non_existent_id_999999")
        self.assertIsNone(tree)


if __name__ == "__main__":
    unittest.main()
