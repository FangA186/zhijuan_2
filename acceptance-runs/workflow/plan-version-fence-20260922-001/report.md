# Plan-version fence regression

Before fix, two no-network tests failed:

- `test_old_plan_job_and_results_are_not_current_with_same_spec`: job plan revision 2 and current blueprint revision 3 share spec revision 7, yet old q01 was returned.
- `test_replanned_draft_hides_old_candidates_and_checks`: regenerating a plan under the same spec left old draft candidates visible.

Command: `.venv/bin/python -m unittest tests.test_workflow_safety_closeout.CloseoutTests.test_old_plan_job_and_results_are_not_current_with_same_spec tests.test_workflow_safety_closeout.CloseoutTests.test_replanned_draft_hides_old_candidates_and_checks -q`; 2 FAIL before implementation. No model or network call.

After fix:

- `.venv/bin/python -m unittest tests.test_generation_pipeline tests.test_workflow_safety_closeout -q`: 11 tests passed.
- `.venv/bin/python -m unittest tests.test_publish_gate tests.test_generation_pipeline tests.test_workflow_safety_closeout -q`: 27 related tests passed.
- `tests.integration.test_workflow_integration` against the dedicated schema supplied by `/tmp/zhijuan-workflow-20260922/regression-runtime.json`: 4 tests passed. The new PostgreSQL case marks a job RUNNING without starting a worker or model, confirms same-spec replan is rejected, cancels the job, then confirms an old confirmed plan cannot create a new job after the blueprint changes.
- Complete `tests/integration` suite after updating the PostgreSQL fixture to persist an actual confirmed blueprint: 8 tests passed, 0 failed, 0 errors, 0 skipped. See `all-integration-final.log` and `all-integration-final.json`. The original concurrent create, idempotent replay, history, admission and cancellation assertions remain in place.
- `git diff --check` on touched files passed. Database credentials were loaded internally and not printed. No model call.

Implementation: `store._persist` checks active jobs before a same-spec plan hash change under the existing exam advisory lock; `PostgresJobRepository.create` checks the persisted confirmed blueprint under that same lock; current job/results queries now require matching spec and plan revision/hash; new plans hide old local draft candidates and clear old validation/adjudications.
