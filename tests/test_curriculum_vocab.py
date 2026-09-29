"""Unit tests for Curriculum Vocabulary data mapping, repository, and API routes."""
from __future__ import annotations
import json
import unittest
import tempfile
from unittest.mock import patch
from tests.curriculum_fixture import material, write
from pathlib import Path
from fastapi.testclient import TestClient

from services.curriculum import (
    CurriculumService,
    CurriculumRepository,
)
from services.api.main import app


class TestCurriculumVocab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        root = Path(cls.directory.name).resolve()
        cls.repo = CurriculumRepository(root / "data")
        cls.repo.vocab_images_base = root / "images"
        cls.service = CurriculumService(cls.repo)
        cls.client = TestClient(app)

        # Load catalog directly to know sample IDs
        catalog_path = Path(__file__).resolve().parents[1] / "services/curriculum/vocab_catalog.json"
        with open(catalog_path, "r", encoding="utf-8") as f:
            cls.catalog = json.load(f)
        sample_id, record = next(iter(cls.catalog['materials'].items()))
        write(cls.repo.mats_file, [material(sample_id, record['edition'], '英语', record['stage'])])
        write(cls.repo.tags_file, {'hierarchies': []})
        image = cls.repo.vocab_images_base / record['folder_path'] / record['images'][0]['filename']
        image.parent.mkdir(parents=True, exist_ok=True)
        # Byte-serving fixture, not a copied textbook page or a visual-rendering test.
        image.write_bytes(b'\xff\xd8\xff' + b'fixture' * 200 + b'\xff\xd9')
        for module in ['services.api.routes.curriculum', 'services.api.routes.vocab_image_routes']:
            scoped = patch(module + '.curriculum_service', cls.service)
            scoped.start(); cls.addClassCleanup(scoped.stop)


    def test_vocab_catalog_total_counts(self):
        """Verify the catalog contains all 367 textbooks and 2,005 clean images."""
        self.assertEqual(self.catalog["total_materials"], 367)
        self.assertEqual(self.catalog["total_images"], 2005)
        self.assertEqual(len(self.catalog["materials"]), 367)

    def test_repository_loads_vocab_catalog(self):
        """Verify repository loads vocabulary entries on demand."""
        self.repo.ensure_loaded()
        self.assertGreaterEqual(len(self.repo._vocab_by_material_id), 367)
        self.assertGreaterEqual(len(self.repo._vocab_by_key), 200)

    def test_material_has_vocab_flag(self):
        """Verify that English materials that have clean vocab images have has_vocab=True."""
        self.repo.ensure_loaded()
        materials_with_vocab = [m for m in self.repo.get_all_materials() if m.has_vocab]
        self.assertGreater(len(materials_with_vocab), 0)
        # Check serialization in to_dict
        sample = materials_with_vocab[0]
        d = sample.to_dict()
        self.assertTrue(d.get("hasVocab"))
        self.assertGreater(d.get("vocabCount", 0), 0)

    def test_get_material_vocab_by_id(self):
        """Verify get_material_vocab returns full package for a known textbook."""
        sample_id = list(self.catalog["materials"].keys())[0]
        expected = self.catalog["materials"][sample_id]

        vocab = self.service.get_material_vocab(sample_id)
        self.assertIsNotNone(vocab)
        self.assertEqual(vocab["material_id"], sample_id)
        self.assertEqual(vocab["title"], expected["title"])
        self.assertEqual(vocab["image_count"], expected["image_count"])
        self.assertEqual(len(vocab["images"]), expected["image_count"])
        self.assertTrue(vocab["images"][0]["url"].startswith(f"/v1/curriculum/materials/{sample_id}/vocab/images/"))

    def test_vocab_image_path_resolution_and_security(self):
        """Verify secure image path resolution and path traversal rejection."""
        sample_id = list(self.catalog["materials"].keys())[0]
        vocab = self.catalog["materials"][sample_id]
        valid_filename = vocab["images"][0]["filename"]

        # Valid image path
        path = self.service.get_vocab_image_file(sample_id, valid_filename)
        self.assertIsNotNone(path)
        self.assertTrue(path.is_file())
        self.assertGreater(path.stat().st_size, 1024)

        # Unlisted / malicious filename
        bad_path = self.service.get_vocab_image_file(sample_id, "../../../etc/passwd")
        self.assertIsNone(bad_path)

        unlisted_file = self.service.get_vocab_image_file(sample_id, "non_existent.jpg")
        self.assertIsNone(unlisted_file)

    def test_api_get_vocab_endpoint(self):
        """Test GET /v1/curriculum/materials/{material_id}/vocab endpoint."""
        sample_id = list(self.catalog["materials"].keys())[0]
        resp = self.client.get(f"/v1/curriculum/materials/{sample_id}/vocab")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["material_id"], sample_id)
        self.assertIn("images", data)
        self.assertGreater(len(data["images"]), 0)

    def test_api_get_vocab_image_endpoint(self):
        """Test GET /v1/curriculum/materials/{material_id}/vocab/images/{filename}."""
        sample_id = list(self.catalog["materials"].keys())[0]
        vocab = self.catalog["materials"][sample_id]
        filename = vocab["images"][0]["filename"]

        resp = self.client.get(f"/v1/curriculum/materials/{sample_id}/vocab/images/{filename}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("content-type"), "image/jpeg")
        self.assertIn("max-age=86400", resp.headers.get("cache-control", ""))
        self.assertGreater(len(resp.content), 1024)

    def test_api_vocab_not_found(self):
        """Test 404 behavior for unknown material or missing image."""
        resp = self.client.get("/v1/curriculum/materials/unknown-9999/vocab")
        self.assertEqual(resp.status_code, 404)

        sample_id = list(self.catalog["materials"].keys())[0]
        resp2 = self.client.get(f"/v1/curriculum/materials/{sample_id}/vocab/images/not_found.jpg")
        self.assertEqual(resp2.status_code, 404)


if __name__ == "__main__":
    unittest.main()
