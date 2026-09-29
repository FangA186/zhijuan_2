"""Real-PostgreSQL tests for the runtime heartbeat table (database/005).

Run only with ZHIJUAN_TEST_DATABASE_URL pointed at an isolated disposable
PostgreSQL database — never at zhijuan_local or any other project database.

Covers the behaviours the readiness probe depends on: DB-assigned timestamps,
idempotent upsert per instance, TTL staleness, cross-runtime isolation,
freshest-instance deduplication, future-timestamp (clock skew) rejection.
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path

import psycopg

from services.api import runtime_heartbeats as hb

SQL = Path(__file__).resolve().parents[2] / "database/005_local_runtime_heartbeats.sql"


@unittest.skipUnless(os.getenv("ZHIJUAN_TEST_DATABASE_URL"), "isolated PostgreSQL DSN required")
class HeartbeatPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn = os.environ["ZHIJUAN_TEST_DATABASE_URL"]
        with psycopg.connect(cls.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database()")
                assert cur.fetchone()[0] == "zhijuan_accept_w6", (
                    "heartbeat integration tests must run on the dedicated test database")
            conn.execute(SQL.read_text())
            conn.commit()

    def setUp(self):
        with psycopg.connect(self.dsn) as conn:
            conn.execute("TRUNCATE runtime_heartbeats")
            conn.commit()

    def _upsert(self, runtime_id="zhijuan-test", component="worker", instance="i1",
                metadata=None):
        with psycopg.connect(self.dsn) as conn:
            hb.upsert_heartbeat(conn, runtime_id, component, instance,
                                metadata if metadata is not None
                                else {"model_id": "deepseek-flash", "gateway": "127.0.0.1:8644"})
            conn.commit()

    def _fresh(self, runtime_id="zhijuan-test", ttl=20.0):
        with psycopg.connect(self.dsn) as conn:
            return hb.fresh_components(conn, runtime_id, ttl)

    def test_migration_is_idempotent(self):
        with psycopg.connect(self.dsn) as conn:
            conn.execute(SQL.read_text())
            conn.commit()
        self._upsert()
        fresh = self._fresh()
        self.assertTrue(fresh["worker"]["ok"])

    def test_upsert_then_fresh_roundtrip(self):
        self._upsert(metadata={"model_id": "deepseek-flash", "gateway": "127.0.0.1:8644"})
        fresh = self._fresh()
        self.assertIn("worker", fresh)
        self.assertTrue(fresh["worker"]["ok"])
        self.assertLessEqual(fresh["worker"]["age_seconds"], 2.0)
        self.assertEqual(fresh["worker"]["metadata"].get("model_id"), "deepseek-flash")

    def test_upsert_is_idempotent_per_instance(self):
        self._upsert()
        self._upsert()
        with psycopg.connect(self.dsn) as conn:
            count = conn.execute("SELECT count(*) FROM runtime_heartbeats").fetchone()[0]
        self.assertEqual(count, 1)

    def test_ttl_expiry_marks_stale(self):
        self._upsert()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE runtime_heartbeats SET last_seen_at = now() - interval '25 seconds'")
            conn.commit()
        fresh = self._fresh(ttl=20.0)
        self.assertIn("worker", fresh)
        self.assertFalse(fresh["worker"]["ok"])
        self.assertGreaterEqual(fresh["worker"]["age_seconds"], 24.0)

    def test_cross_runtime_heartbeat_is_invisible(self):
        self._upsert(runtime_id="some-other-deployment")
        self.assertEqual(self._fresh(runtime_id="zhijuan-test"), {})

    def test_freshest_instance_wins_per_component(self):
        self._upsert(instance="old")
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE runtime_heartbeats SET last_seen_at = now() - interval '30 seconds' "
                         "WHERE instance_id = 'old'")
            conn.commit()
        self._upsert(instance="new")
        fresh = self._fresh(ttl=20.0)
        self.assertEqual(list(fresh.keys()), ["worker"])
        self.assertTrue(fresh["worker"]["ok"])
        self.assertLessEqual(fresh["worker"]["age_seconds"], 2.0)

    def test_future_timestamp_is_treated_stale(self):
        self._upsert()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE runtime_heartbeats SET last_seen_at = now() + interval '30 seconds'")
            conn.commit()
        # A skewed process must not prove liveness with a future timestamp.
        self.assertEqual(self._fresh(), {})

    def test_dispatcher_component_separate_from_worker(self):
        self._upsert(component="dispatcher", instance="d1")
        fresh = self._fresh()
        self.assertIn("dispatcher", fresh)
        self.assertNotIn("worker", fresh)


if __name__ == "__main__":
    unittest.main()
