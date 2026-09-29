"""Template parser cases, part 1."""
from tests.template_parser_fixture import *

class TemplateParserCases1(TemplateParserFixture, unittest.TestCase):
    def test_docx_text_extractor(self):
        """Test extracting paragraphs from synthetic docx binary bytes."""
        expected = [
            "2023-2024学年期末教学质量检测卷",
            "一、选择题：共10题",
            "1. 第一题",
            "2. 第二题",
        ]
        docx_bytes = self._create_synthetic_docx(expected)
        extracted = DocxTextExtractor.extract_paragraphs(docx_bytes)
        self.assertEqual(extracted, expected)


    def test_docx_text_extractor_corrupt_handled(self):
        """Corrupt or non-docx bytes should safely return empty list without crashing."""
        self.assertEqual(DocxTextExtractor.extract_paragraphs(b"corrupted binary"), [])
        self.assertEqual(DocxTextExtractor.extract_paragraphs(b""), [])


    def test_rule_parser_user_math_exam(self):
        """Test rule parser on high school math exam with Single Choice, Multi Choice, Fill Blank, Solution."""
        sample_paragraphs = [
            "2023-2024学年人教A版（2019）高中数学必修第一册期末综合测试卷",
            "考试时间：120分钟  满分：150分",
            "一、单项选择题：本题共10小题，每小题4分，共40分，在每小题给出的四个选项中，只有一项是符合题目要求的.",
            "1. 设集合 A={x|x-1>0}，集合 B={x|x<=3}，则 A∩B=（  ）",
            "2. 设函数 f(x)=2/x",
            "3. 函数 y 的定义域是",
            "4. 下列四个命题",
            "5. 已知集合 A",
            "6. 已知函数单调递增",
            "7. 函数图像对称",
            "8. 向量垂直",
            "9. 三角函数化简",
            "10. 抽象函数性质",
            "二、多项选择题（本大题共3小题，每小题4分，共12分.在每小题给出的四个选项中，有多项符合题目要求.全部选对的得4分，选对但不全的得2分，有选错的得0分）",
            "11. 下列四个命题中假命题是（  ）",
            "12. 函数 y=3sin(x)",
            "13. 定义域为 R 的函数",
            "三、填空题：本题共4小题，每小题4分，共16分.",
            "14. 设 A, B 是 R 的两个子集",
            "15. 已知方程的实数解",
            "16. 函数零点个数",
            "17. 已知角为第三象限角",
            "四、解答题：本大题共6小题，共82分.解答应写出文字说明、证明过程或演算步骤.",
            "18. (本小题满分12分) 设矩形 ABCD",
            "19. (本小题满分14分) 阅读下列材料，解答问题",
            "20. (本小题满分14分) 已知不等式",
            "21. (本小题满分14分) 已知 A, B, C 是三角形内角",
            "22. (本小题满分14分) 设二次函数",
            "23. (本小题满分14分) 综合探究题",
        ]

        result = RuleTemplateParser.parse(sample_paragraphs, "高中数学期末卷.docx")
        self.assertEqual(result["duration_minutes"], 120)
        self.assertEqual(result["total_score"], 150)
        self.assertEqual(len(result["sections"]), 4)

        sec_map = {s["question_type"]: s for s in result["sections"]}
        self.assertIn("single_choice", sec_map)
        self.assertIn("multiple_choice", sec_map)
        self.assertIn("fill_blank", sec_map)
        self.assertIn("solution", sec_map)

        self.assertEqual(sec_map["single_choice"]["count"], 10)
        self.assertEqual(sec_map["multiple_choice"]["count"], 3)
        self.assertEqual(sec_map["fill_blank"]["count"], 4)
        self.assertEqual(sec_map["solution"]["count"], 6)

        total_questions = sum(s["count"] for s in result["sections"])
        self.assertEqual(total_questions, 23)

        # Verify solution section total score and item scores
        self.assertEqual(sec_map["solution"]["total_score_x100"], 8200)
        self.assertEqual(sec_map["solution"]["item_scores_x100"], [1200, 1400, 1400, 1400, 1400, 1400])

        # A parsed template has no approved curriculum/scope and must not bypass that gate.
        from services.blueprint import BlueprintGenerator
        with self.assertRaises(ValueError):
            BlueprintGenerator.generate(result)
        # Explicitly attach a full confirmed specification and preserve each parsed item score.
        from pathlib import Path
        import json
        spec = json.loads((Path(__file__).resolve().parents[1] / "examples/exam-spec-senior.json").read_text())
        spec["sections"] = [
            {"id":f"{section['id']}-{i}", "title":section["title"], "question_type":section["question_type"],
             "count":1, "score_each_x100":score, "topics":spec["taught_scope"]["topics"][:1]}
            for section in result["sections"] for i,score in enumerate(section["item_scores_x100"])
        ]
        spec["total_score_x100"] = result["total_score_x100"]
        spec["taught_scope"]["scope_confirmed"] = True
        bp = BlueprintGenerator.generate(spec)
        self.assertEqual(bp["total_score_x100"], 15000)
        self.assertEqual(len(bp["slots"]), 23)
        self.assertEqual([s["score_x100"] for s in bp["slots"][-6:]], [1200,1400,1400,1400,1400,1400])


    def test_conflicting_section_score_is_exposed_for_teacher_review(self):
        result = RuleTemplateParser.parse([
            "高中数学期末试卷", "考试时间：120分钟 满分：150分",
            "一、单项选择题：本题共10小题，每小题4分，共52分。",
            "二、多项选择题：本题共3小题，每小题4分，共12分。",
        ], "math.docx")
        self.assertEqual(result["sections"][0]["total_score_x100"], 4000)
        self.assertTrue(any("52" in item and "40" in item for item in result["warnings"]))


    def test_api_parse_template_docx(self):
        """Test POST /v1/exams/templates/parse endpoint with a docx payload."""
        paragraphs = [
            "期末质量监测（英语）",
            "一、单项选择题（共15题，每题2分，共30分）",
            "二、完形填空（共10题，每题1.5分，共15分）",
            "三、阅读理解（共10题，每题2分，共20分）",
            "四、书面表达（共1题，共25分）",
        ]
        docx_bytes = self._create_synthetic_docx(paragraphs)
        b64_content = base64.b64encode(docx_bytes).decode("utf-8")

        payload = {
            "filename": "english_final_exam.docx",
            "content_base64": f"data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,{b64_content}",
        }

        resp = self.client.post("/v1/exams/templates/parse", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["title"], "期末质量监测（英语）")
        self.assertGreaterEqual(len(data["sections"]), 3)
        types = [s["question_type"] for s in data["sections"]]
        self.assertIn("single_choice", types)


    def test_api_parse_template_txt(self):
        """Test POST /v1/exams/templates/parse endpoint with plain text."""
        txt_content = (
            "八年级数学期中测试卷\n"
            "考试时间：90分钟 满分：100分\n"
            "一、选择题（共8小题，每小题3分，共24分）\n"
            "二、填空题（共6小题，每小题3分，共18分）\n"
            "三、解答题（共5小题，共58分）\n"
        ).encode("utf-8")
        b64_content = base64.b64encode(txt_content).decode("utf-8")

        payload = {
            "filename": "math_midterm.txt",
            "content_base64": b64_content,
        }

        with patch("services.hermes_adapter.adapter.HermesDeepSeekAdapter._call_deepseek_chat",
                   side_effect=AssertionError("direct provider call must not run")):
            resp = self.client.post("/v1/exams/templates/parse", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_score"], 100)
        self.assertEqual(len(data["sections"]), 3)
        self.assertEqual(sum(s["count"] for s in data["sections"]), 19)


    def test_forced_ai_template_parse_is_explicitly_unavailable(self):
        payload = {"filename": "exam.txt", "content_base64": base64.b64encode(
            "一、选择题：共2题，每题5分，共10分".encode()).decode(), "force_llm": True}
        with patch("services.hermes_adapter.adapter.HermesDeepSeekAdapter._call_deepseek_chat",
                   side_effect=AssertionError("direct provider call must not run")):
            response = self.client.post("/v1/exams/templates/parse", json=payload)
        self.assertEqual(response.status_code, 501)
        self.assertIn("尚未接入 Hermes", response.json()["detail"])


