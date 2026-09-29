"""Template parser cases, part 2."""
from tests.template_parser_fixture import *

class TemplateParserCases2(TemplateParserFixture, unittest.TestCase):
    def test_unreadable_docx_is_not_reported_as_success(self):
        payload = {"filename": "broken.docx", "content_base64": base64.b64encode(b"broken").decode()}
        response = self.client.post("/v1/exams/templates/parse", json=payload)
        self.assertEqual(response.status_code, 422)


    def test_api_parse_template_empty_rejected(self):
        """Empty filename or empty content returns 400."""
        resp1 = self.client.post("/v1/exams/templates/parse", json={"filename": "", "content_base64": "abc"})
        self.assertEqual(resp1.status_code, 400)

        resp2 = self.client.post("/v1/exams/templates/parse", json={"filename": "test.txt", "content_base64": ""})
        self.assertEqual(resp2.status_code, 400)


    def check_local_user_real_math_docx(self):
        """Manual check only: requires authorization to read the uploaded exam."""
        from pathlib import Path
        file_path = Path(__file__).resolve().parents[1] / "uploads/source-docx/2023-2024学年人教A版（2019）高中数学必修第一册期末综合测试卷.docx"
        if not file_path.exists():
            self.fail("本地上传试卷不存在；不能把实际模板检查计为通过")

        with open(file_path, "rb") as f:
            b64_content = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "filename": file_path.name,
            "content_base64": b64_content,
        }
        resp = self.client.post("/v1/exams/templates/parse", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["total_score"], 150)
        self.assertEqual(data["duration_minutes"], 120)
        self.assertEqual(len(data["sections"]), 4)
        self.assertTrue(any("52" in item and "40" in item for item in data["warnings"]))
        total_q = sum(s["count"] for s in data["sections"])
        self.assertEqual(total_q, 23)

        type_map = {s["question_type"]: s["count"] for s in data["sections"]}
        self.assertEqual(type_map["single_choice"], 10)
        self.assertEqual(type_map["multiple_choice"], 3)
        self.assertEqual(type_map["fill_blank"], 4)
        self.assertEqual(type_map["solution"], 6)

