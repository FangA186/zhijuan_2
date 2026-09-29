"""Keep the local image viewer inside its configured textbook directory."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import vocab_viewer_operations as operations
from tools import vocab_viewer_paths as paths


class ViewerPathTests(unittest.TestCase):
    def test_read_delete_and_restore_reject_sibling_prefix_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "教材单词图片"
            trash = base / ".trash"
            sibling = root / "教材单词图片2"
            base.mkdir()
            trash.mkdir()
            sibling.mkdir()
            external = sibling / "example.jpg"
            external.write_bytes(b"fixture")
            (base / "outside-link.jpg").symlink_to(external)
            with patch.object(paths, "BASE_DIR", str(base)), patch.object(paths, "TRASH_DIR", str(trash)), \
                 patch.object(operations, "BASE_DIR", str(base)), patch.object(operations, "TRASH_DIR", str(trash)):
                for name in ("../教材单词图片2/example.jpg", "outside-link.jpg"):
                    with self.subTest(name=name), self.assertRaises(PermissionError):
                        paths.get_safe_path(name)
                with self.assertRaises(PermissionError):
                    paths.get_safe_trash_path("../../教材单词图片2/example.jpg")
                self.assertEqual(paths.list_book_images(""), [])
                deleted = operations.delete_files(["../教材单词图片2/example.jpg"], use_trash=False)
                restored = operations.restore_trash_files(["../../教材单词图片2/example.jpg"])
                self.assertFalse(deleted["deleted"])
                self.assertTrue(deleted["failed"])
                self.assertEqual(restored["restored"], 0)
                self.assertTrue(restored["failed"])
                (trash / "kept.jpg").write_bytes(b"kept")
                self.assertEqual(operations.restore_trash_files([])["restored"], 0)
                self.assertTrue((trash / "kept.jpg").exists())
                self.assertEqual(external.read_bytes(), b"fixture")


if __name__ == "__main__":
    unittest.main()
