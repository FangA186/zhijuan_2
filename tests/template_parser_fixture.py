"""Unit tests for Exam Template Document Parser and API Route."""
from __future__ import annotations

import base64
import io
import unittest
import zipfile
from unittest.mock import patch
from fastapi.testclient import TestClient

from services.api.main import app
from services.exam.template_parser import (
    DocxTextExtractor,
    RuleTemplateParser,
    ExamTemplateService,
)



class TemplateParserFixture:
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)


    def _create_synthetic_docx(self, paragraphs: list[str]) -> bytes:
        """Create a minimal in-memory valid docx zip archive with word/document.xml."""
        body_xml = "".join(f"<w:p><w:t>{p}</w:t></w:p>" for p in paragraphs)
        xml_content = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body>{body_xml}</w:body>"
            "</w:document>"
        ).encode("utf-8")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("word/document.xml", xml_content)
        return buf.getvalue()



__all__ = [name for name in globals() if not name.startswith("__")]
