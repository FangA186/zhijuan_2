#!/bin/sh
set -eu
ZHIJUAN_SKIP_DOTENV=1 ZHIJUAN_RAW_API_DIR='' .venv/bin/python -m unittest tests.test_topic_diversity tests.test_blueprint_engine tests.test_generation_pipeline tests.test_review_workflow tests.test_validators tests.test_hermes_adapter tests.test_template_parser tests.test_bug_memory tests.test_scoring_modes tests.test_workflow_safety_closeout tests.test_slot_failure_diagnostics
node --experimental-strip-types --test tests/frontend_topic_planning.test.mjs tests/frontend_section_scope.test.mjs tests/frontend_scoring.test.mjs
npm run build --prefix apps/web
.venv/bin/python tools/check_code_lines.py
