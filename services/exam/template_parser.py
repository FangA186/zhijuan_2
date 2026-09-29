"""Exam Template Document Parser.

Supports:
1. Pure Python standard library Docx text extraction (zipfile + xml.etree.ElementTree).
2. Rule-based Fast Template Parser (regex for section titles, question counts, scores).
"""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Literal

from .template_parser_headers import _empty_result, _finalize, _parse_header
from .template_parser_sections import _collect_sections, _score_sections

QuestionKind = Literal[
    "single_choice",
    "multiple_choice",
    "true_false",
    "fill_blank",
    "solution",
    "short_answer",
    "essay",
    "material_group",
]


class DocxTextExtractor:
    """Extracts text paragraphs from docx binary streams using standard library."""

    @staticmethod
    def extract_paragraphs(docx_bytes: bytes) -> list[str]:
        if not docx_bytes:
            return []
        try:
            with io.BytesIO(docx_bytes) as bio:
                with zipfile.ZipFile(bio) as zf:
                    if "word/document.xml" not in zf.namelist():
                        return []
                    xml_content = zf.read("word/document.xml")
            
            tree = ET.fromstring(xml_content)
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs: list[str] = []

            for p in tree.iterfind(".//w:p", ns):
                text_parts = [node.text for node in p.iterfind(".//w:t", ns) if node.text]
                if text_parts:
                    line = "".join(text_parts).strip()
                    if line:
                        paragraphs.append(line)

            return paragraphs
        except Exception as e:
            return []



class RuleTemplateParser:
    SECTION_HEADER_REGEX = re.compile(
        r"^\s*(第[一二三四五六七八九十]+(?:大题|部分)*|[一二三四五六七八九十]+|[(（][一二三四五六七八九十]+[)）])[、.．\s]+(.+)"
    )
    ALT_SECTION_HEADER_REGEX = re.compile(
        r"^\s*[【\[]?(单项选择题|多项选择题|单选题|多选题|选择题|填空题|判断题|解答题|综合题|计算题|证明题|书面表达|作文)[】\]]?[:：\s]*(.*)"
    )
    ANSWER_HEADER_REGEX = re.compile(
        r"^\s*[【\[]?(?:参考答案|答案及解析|答案与解析|试题解析|参考答案及评分标准|参考答案与评分标准|答案|解析|答题卡)[】\]]?[:：\s]*$"
    )
    QUESTION_NUM_REGEX = re.compile(r"^\s*(\d+)[.、．\s]")
    KIND_KEYWORDS = [
        ("multiple_choice", ["多项选择", "多选题", "双项选择"]),
        ("single_choice", ["单项选择", "单选题", "选择题"]),
        ("fill_blank", ["填空题", "填空"]),
        ("true_false", ["判断题", "正误判断"]),
        ("essay", ["书面表达", "写作", "作文", "写作题"]),
        ("short_answer", ["简答题", "简答"]),
        ("solution", ["解答题", "综合题", "计算题", "证明题", "解答大题", "探究题"]),
    ]

    @classmethod
    def parse(cls, paragraphs: list[str], filename: str = "") -> dict[str, Any]:
        if not paragraphs:
            return _empty_result(filename)
        exam_paragraphs = []
        for paragraph in paragraphs:
            if cls.ANSWER_HEADER_REGEX.match(paragraph.strip()):
                break
            exam_paragraphs.append(paragraph)
        title, duration, total_score = _parse_header(exam_paragraphs, filename)
        raw_sections = _collect_sections(exam_paragraphs, cls)
        parsed, calculated_total, warnings = _score_sections(raw_sections)
        return _finalize(title, duration, total_score, parsed, calculated_total, warnings)

    @classmethod
    def _detect_kind(cls, text: str) -> QuestionKind | None:
        for kind, kws in cls.KIND_KEYWORDS:
            for kw in kws:
                if kw in text:
                    return kind
        return None



class ExamTemplateService:
    """Extract a reviewable template structure without calling a model."""

    def parse_template(
        self,
        filename: str,
        content_bytes: bytes,
    ) -> dict[str, Any]:
        """Extract paragraphs and parse exam structure."""
        if not content_bytes:
            raise ValueError("模板文件为空")

        paragraphs: list[str] = []
        lower_name = filename.lower()

        if lower_name.endswith(".docx"):
            paragraphs = DocxTextExtractor.extract_paragraphs(content_bytes)
        elif lower_name.endswith((".txt", ".json", ".md")):
            for enc in ("utf-8", "gb18030", "gbk", "latin1"):
                try:
                    text = content_bytes.decode(enc)
                    paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
                    break
                except Exception:
                    continue
        else:
            raise ValueError("当前只支持 .docx、.txt、.json 或 .md 模板")

        if not paragraphs:
            raise ValueError("无法读取模板文字，请检查文件格式")

        return RuleTemplateParser.parse(paragraphs, filename)


template_service = ExamTemplateService()
