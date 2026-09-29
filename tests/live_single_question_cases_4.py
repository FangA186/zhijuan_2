"""Live single-question offline safety checks, part 4."""
from tests.live_single_question_shared import *

class SeedSpecTests(unittest.TestCase):
    """run 的种子规格构造正确性（纯函数）。"""

    def test_seed_spec_is_single_choice_1_q_100(self):
        spec = lsq.build_seed_spec()
        self.assertEqual(spec["stage"], "primary")
        self.assertEqual(len(spec["sections"]), 1)
        section = spec["sections"][0]
        self.assertEqual(section["question_type"], "single_choice")
        self.assertEqual(section["count"], 1)
        self.assertEqual(section["score_each_x100"], 100)
        self.assertEqual(spec["total_score_x100"], 100)
        self.assertTrue(spec["taught_scope"]["scope_confirmed"])

    def test_seed_spec_passes_domain_validation(self):
        # validate_spec + BlueprintGenerator.generate 都是纯函数，可离线验证。
        from services.exam.spec_validation import validate_spec
        from services.blueprint.generator import BlueprintGenerator
        spec = lsq.build_seed_spec()
        validate_spec(spec, require_scope_confirmation=True)  # 不抛即通过
        blueprint = BlueprintGenerator.generate(spec, spec_revision=1, revision=1)
        self.assertEqual(len(blueprint["slots"]), 1)
        self.assertEqual(blueprint["slots"][0]["kind"], "single_choice")
        self.assertEqual(blueprint["slots"][0]["score_x100"], 100)
        self.assertEqual(blueprint["total_score_x100"], 100)
        # 分值配平约束（generator.py 抛出即失败）
        self.assertEqual(sum(s["score_x100"] for s in blueprint["slots"]), spec["total_score_x100"])

class EvidenceReportTests(unittest.TestCase):
    def test_job_evidence_structure(self):
        job = {
            "job_id": "abc-123", "status": "COMPLETED", "total_slots": 1,
            "completed_slots": 1, "usage_status": "TOKENS_REPORTED",
            "tokens_used": 345, "tokens_used_known": 345,
            "slots": [{"slot_id": "slot_001", "status": "REVIEW_REQUIRED",
                       "kind": "single_choice", "score_x100": 100, "target_topic": "整数四则运算"}],
            "run_refs": {
                "slot_001": {
                    "author": {"task_ref": "job:slot:author", "run_id": "run_author_1",
                               "state": "completed",
                               "usage": {"total_tokens": 200, "input_tokens": 150, "output_tokens": 50}},
                    "solver": {"task_ref": "job:slot:solver", "run_id": "run_solver_1",
                               "state": "completed",
                               "usage": {"total_tokens": 145, "input_tokens": 100, "output_tokens": 45}},
                },
            },
        }
        results = [{"slot_id": "slot_001",
                    "candidate": {"public": {"local_id": "q01"}},
                    "validation": {"overall_status": "REVIEW"}}]
        evidence = lsq.job_evidence(job, results)
        self.assertEqual(evidence["job_id"], "abc-123")
        self.assertEqual(evidence["status"], "COMPLETED")
        self.assertEqual(evidence["validation_overall"], ["REVIEW"])
        self.assertEqual(evidence["slots"][0]["score_x100"], 100)
        self.assertEqual(evidence["author_runs"][0]["run_id"], "run_author_1")
        self.assertEqual(evidence["solver_runs"][0]["run_id"], "run_solver_1")
        # 缺 run_id 时如实记 None（证据层面"未知"），不猜测。
        missing = lsq.job_evidence({"job_id": "x", "status": "RECONCILING", "run_refs": {}}, [])
        self.assertEqual(missing["author_runs"], [])

    def test_job_evidence_filters_phantom_phase_records(self):
        # run_refs 里只有 author、没有 solver 阶段时，solver 不得出现幻影行。
        job = {
            "job_id": "abc", "status": "FAILED", "total_slots": 1, "completed_slots": 0,
            "run_refs": {"slot_001": {"author": {"task_ref": "t", "run_id": "run_a",
                                                  "state": "hermes_run_admitted"}}},
        }
        evidence = lsq.job_evidence(job, [])
        self.assertEqual(len(evidence["author_runs"]), 1)
        self.assertEqual(evidence["author_runs"][0]["run_id"], "run_a")
        self.assertEqual(evidence["solver_runs"], [])  # 未开始 = 无记录，不猜"未知"
        self.assertEqual(evidence["phase_count"], 1)

    def test_write_report_has_required_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            result = {
                "preflight": {"ready": True},
                "budget_before": {"calls": 16, "reserved_cny": 16},
                "budget_after": {"calls": 18, "reserved_cny": 18},
                "budget_delta": {"calls": 2, "reserved_cny": 2},
                "job_id": "job-1",
                "final_status": "COMPLETED",
                "accept_status": "QUEUED",
                "evidence": {"slots": [], "validation_overall": ["REVIEW"],
                             "author_runs": [], "solver_runs": []},
                "results_count": 1,
                "ok": True,
                "reason": None,
            }
            lsq.write_report(path, result)
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["report_kind"], "l01-live-single-question-v1")
        self.assertEqual(payload["budget_delta_calls"], 2)
        self.assertEqual(payload["budget_delta_reserved_cny"], 2)
        self.assertEqual(payload["job"]["status"], "COMPLETED")
        self.assertEqual(payload["job"]["validation_overall"], ["REVIEW"])
        # limitations 必须明示"不构成教学质量验收"。
        self.assertTrue(any("不构成教学质量验收" in line for line in payload["limitations"]))
        self.assertTrue(any("REVIEW" in line for line in payload["limitations"]))

    def test_write_report_honest_on_reconciling(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            result = {"ok": False, "reason": "作业终态 RECONCILING：如实记录并停止，绝不重新受理",
                      "final_status": "RECONCILING", "job_id": "job-2",
                      "evidence": None, "preflight": {"ready": True}}
            lsq.write_report(path, result)
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["job"]["status"], "RECONCILING")
        self.assertFalse(payload["ok"])
        self.assertIn("RECONCILING", payload["reason"])

class TeardownOrderTests(unittest.TestCase):
    """子进程收尾顺序：worker -> scheduler -> api，且只终止归属校验通过的进程。"""

    def _fake_proc(self, pid: int):
        proc = mock.MagicMock(spec=subprocess.Popen)
        proc.pid = pid
        proc.poll.return_value = None  # 仍在运行
        return proc

    def test_terminate_order_worker_then_scheduler_then_api(self):
        procs = {
            "worker": self._fake_proc(1111),
            "scheduler": self._fake_proc(2222),
            "api": self._fake_proc(3333),
        }
        calls = []

        def fake_terminate_owned(pid, grace_seconds=10.0):
            kind = {1111: "worker", 2222: "scheduler", 3333: "api"}[pid]
            calls.append(kind)
            return f"PID {pid} 已终止"

        with mock.patch.object(lsq, "verify_pid_ownership",
                               return_value=(True, "属本项目")), \
                mock.patch.object(lsq, "terminate_owned", side_effect=fake_terminate_owned), \
                mock.patch("builtins.print"):
            lsq._terminate_all(procs)
        self.assertEqual(calls, ["worker", "scheduler", "api"])

    def test_terminate_skips_not_owned(self):
        procs = {"worker": self._fake_proc(1111)}

        def fake_ownership(pid, markers=lsq.WORKER_MARKERS):
            return False, "命令行不含标记，拒绝 kill"

        with mock.patch.object(lsq, "verify_pid_ownership", side_effect=fake_ownership) as verify, \
                mock.patch.object(lsq, "terminate_owned") as term, \
                mock.patch("builtins.print"):
            lsq._terminate_all(procs)
        verify.assert_called_once()
        term.assert_not_called()  # 归属不通过 → 不杀

    def test_terminate_skips_already_exited(self):
        proc = self._fake_proc(1111)
        proc.poll.return_value = 0  # 已退出
        with mock.patch.object(lsq, "verify_pid_ownership") as verify, \
                mock.patch.object(lsq, "terminate_owned") as term, \
                mock.patch("builtins.print"):
            lsq._terminate_all({"worker": proc})
        verify.assert_not_called()
        term.assert_not_called()

    def test_run_refuses_when_preflight_not_ready_without_spawn(self):
        with mock.patch.object(lsq, "preflight",
                               return_value={"ready": False, "components": {}}), \
                mock.patch.object(lsq, "spawn_process") as spawn, \
                mock.patch("builtins.print"), \
                mock.patch.object(lsq, "write_report"), \
                mock.patch.dict(os.environ, {"ZHIJUAN_TEST_DATABASE_URL": "postgresql://u@h/x"}, clear=True):
            result = lsq.run(out_path=Path("/tmp/lsq-test-report.json"))
        self.assertFalse(result["ok"])
        self.assertIn("preflight", result["reason"])
        spawn.assert_not_called()  # 预检不过绝不启动任何进程

