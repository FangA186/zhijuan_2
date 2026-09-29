"""Unit tests for Custom Vocabulary Image upload and retrieval API."""
from __future__ import annotations
import base64
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from services.api.main import app
from services.api.routes.curriculum import CUSTOM_VOCAB_DIR


class TestVocabUpload(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.created_files: list[Path] = []

    @classmethod
    def tearDownClass(cls):
        for f in cls.created_files:
            if f.is_file():
                try:
                    f.unlink()
                except OSError:
                    pass

    def test_upload_valid_jpeg_and_retrieve(self):
        """Test uploading a valid minimal JPEG image and fetching it back."""
        # Minimal JPEG magic bytes and padding
        fake_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xd9"
        b64_content = base64.b64encode(fake_jpeg).decode("utf-8")

        payload = {
            "filename": "my_school_unit1.jpg",
            "content_base64": f"data:image/jpeg;base64,{b64_content}",
        }

        resp = self.client.post("/v1/curriculum/vocab/upload", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("filename", data)
        self.assertIn("url", data)
        self.assertEqual(data["mime_type"], "image/jpeg")
        self.assertTrue(data["filename"].startswith("custom_"))
        self.assertTrue(data["filename"].endswith(".jpg"))

        created_path = CUSTOM_VOCAB_DIR / data["filename"]
        self.assertTrue(created_path.is_file())
        self.created_files.append(created_path)

        # Fetch image back
        get_resp = self.client.get(data["url"])
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.headers.get("content-type"), "image/jpeg")
        self.assertEqual(get_resp.content, fake_jpeg)

    def test_upload_valid_png(self):
        """Test uploading a valid minimal PNG image."""
        # Minimal PNG magic bytes + IHDR chunk header
        fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        b64_content = base64.b64encode(fake_png).decode("utf-8")

        payload = {
            "filename": "custom_page_2.png",
            "content_base64": b64_content,
        }

        resp = self.client.post("/v1/curriculum/vocab/upload", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["mime_type"], "image/png")
        self.assertTrue(data["filename"].endswith(".png"))

        created_path = CUSTOM_VOCAB_DIR / data["filename"]
        self.assertTrue(created_path.is_file())
        self.created_files.append(created_path)

        get_resp = self.client.get(f"/v1/curriculum/vocab/custom-images/{data['filename']}")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.headers.get("content-type"), "image/png")

    def test_upload_invalid_format_rejected(self):
        """Test that non-image payloads are rejected with 400."""
        text_content = b"Not an image at all, just plain text"
        b64_content = base64.b64encode(text_content).decode("utf-8")

        payload = {
            "filename": "fake.jpg",
            "content_base64": b64_content,
        }

        resp = self.client.post("/v1/curriculum/vocab/upload", json=payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Unsupported or invalid image format", resp.json()["detail"])

    def test_path_traversal_protection(self):
        """Test path traversal attempts on custom image serving are blocked."""
        resp = self.client.get("/v1/curriculum/vocab/custom-images/../../etc/passwd")
        self.assertIn(resp.status_code, [400, 404])

        resp2 = self.client.get("/v1/curriculum/vocab/custom-images/non_existent.jpg")
        self.assertEqual(resp2.status_code, 404)


if __name__ == "__main__":
    unittest.main()
