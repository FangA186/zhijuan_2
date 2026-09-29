"""Publication and historical exam listing operations for ExamStore."""
from __future__ import annotations
import json


class ExamStorePublicationMixin:
    def publish_exam(self, exam_id: str, publish_data: dict[str, Any]) -> dict[str, Any]:
        """Publish the current exam, verifying publication gates and generating snapshot fingerprints."""
        import hashlib
        import time
        from datetime import datetime

        # Gate Check: no unresolved FAIL or REVIEW
        for c in self.candidates:
            local_id = c.get("public", {}).get("local_id")
            val = self.validation.get(local_id, {})
            status = val.get("overall_status", "REVIEW")
            is_adjudicated = local_id in self.adjudications
            if status == "FAIL":
                raise ValueError(f"题目 #{local_id} 存在严重阻断错误 (FAIL)，严禁发布！")
            if status == "REVIEW" and not is_adjudicated:
                raise ValueError(f"题目 #{local_id} 存在待复核问题 (REVIEW)，需人工裁决后方可发布！")

        # Deterministic content hash
        serialized = json.dumps(self.candidates, sort_keys=True, ensure_ascii=False)
        content_hash = f"sha256:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"
        render_hash = f"render_sha256:{hashlib.sha256((content_hash + '_playwright_layout').encode('utf-8')).hexdigest()}"

        rev = self.blueprint.get("revision", 1)
        snapshot_id = f"snap_pub_{int(time.time())}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        publication = {
            "snapshot_id": snapshot_id,
            "exam_id": exam_id,
            "revision": rev,
            "content_hash": content_hash,
            "render_hash": render_hash,
            "status": "PUBLISHED",
            "reviewer_name": publish_data.get("reviewer_name", "学科审核人"),
            "published_at": now_str,
            "exports": [
                {"export_id": f"exp_student_{snapshot_id}", "render_hash": render_hash, "format": "PDF", "view": "student"},
                {"export_id": f"exp_teacher_{snapshot_id}", "render_hash": render_hash, "format": "PDF", "view": "teacher"},
                {"export_id": f"exp_json_{snapshot_id}", "render_hash": render_hash, "format": "JSON", "view": "standard"},
            ],
        }

        self.publications[snapshot_id] = publication
        self.spec["status"] = "PUBLISHED"

        published_entry = {
            "id": snapshot_id,
            "exam_id": exam_id,
            "title": self.spec.get("title", "原创试卷项目"),
            "stage_label": f"{self.spec.get('grade_label', '初中')} · {self.spec.get('subject_label', '数学')}",
            "status": "PUBLISHED",
            "total_score_x100": self.spec.get("total_score_x100", 10000),
            "question_count": len(self.candidates),
            "revision": rev,
            "content_hash": content_hash,
            "render_hash": render_hash,
            "created_at": now_str,
            "isCurrent": True,
        }

        # Prepend to published list
        self.published_exams.insert(0, published_entry)

        return publication


    def list_exams(self) -> list[dict[str, Any]]:
        """List all exams for the organization (published records + default historical)."""
        defaults = [
            {
                "id": "exam_hist_02",
                "title": "五年级语文第一单元古诗文阅读专项调研卷",
                "stage_label": "五年级 · 小学语文",
                "status": "PUBLISHED",
                "total_score_x100": 10000,
                "question_count": 8,
                "revision": 2,
                "content_hash": "sha256:b590e8a1c841e0...",
                "render_hash": "render_sha256:88fa2b10...",
                "created_at": "2026-09-16 10:20",
                "isCurrent": False,
            },
            {
                "id": "exam_hist_03",
                "title": "高一物理必修第一册牛顿第二定律综合测试卷",
                "stage_label": "高一 · 高中物理",
                "status": "REVIEWED",
                "total_score_x100": 10000,
                "question_count": 12,
                "revision": 1,
                "content_hash": "sha256:c1840ea89b...",
                "render_hash": "render_sha256:49c01827...",
                "created_at": "2026-09-15 16:35",
                "isCurrent": False,
            },
        ]

        if not self.published_exams:
            # Provide current active exam as draft/ready
            curr = {
                "id": "exam_demo_01",
                "exam_id": "current",
                "title": self.spec.get("title", "原创试卷项目"),
                "stage_label": f"{self.spec.get('grade_label', '九年级')} · {self.spec.get('subject_label', '初中数学')}",
                "status": self.spec.get("status", "READY"),
                "total_score_x100": self.spec.get("total_score_x100", 10000),
                "question_count": len(self.candidates),
                "revision": self.blueprint.get("revision", 1),
                "created_at": "2026-09-17 14:40",
                "isCurrent": True,
            }
            return [curr] + defaults

        return self.published_exams + defaults
