from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

"""Heartbeat storage and worker checks."""
from tests.runtime_heartbeats_shared import *

class RuntimeHeartbeatStorageTests(unittest.TestCase):
    def test_upsert_writes_db_now_and_cannot_set_timestamp(self):
        conn = _SqliteHeartbeatStub()
        upsert_heartbeat(conn, "zhijuan-local", "worker", "inst-1", {"model_id": "deepseek-chat"})
        rows = conn.conn.execute(
            "SELECT runtime_id, component, instance_id, last_seen_at_epoch FROM runtime_heartbeats"
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][:3], ("zhijuan-local", "worker", "inst-1"))
        # Timestamp is the DB-side clock (>=1.0), not an app-supplied value.
        self.assertGreaterEqual(rows[0][3], 1.0)

    def test_fresh_components_marks_expired_heartbeat_not_ok(self):
        conn = _SqliteHeartbeatStub()
        upsert_heartbeat(conn, "zhijuan-local", "worker", "inst-1", {"model_id": "m"})
        conn._clock = 10.0  # pretend 9+ seconds passed since the write
        state = fresh_components(conn, "zhijuan-local", ttl_seconds=2.0)
        self.assertIn("worker", state)
        self.assertFalse(state["worker"]["ok"])
        self.assertIsInstance(state["worker"]["age_seconds"], float)
        self.assertEqual(state["worker"]["metadata"]["model_id"], "m")

    def test_fresh_component_ok_within_ttl(self):
        conn = _SqliteHeartbeatStub()
        upsert_heartbeat(conn, "zhijuan-local", "worker", "inst-1", {})
        conn._clock = 2.0
        state = fresh_components(conn, "zhijuan-local", ttl_seconds=10.0)
        self.assertTrue(state["worker"]["ok"])

    def test_cross_runtime_id_is_excluded(self):
        conn = _SqliteHeartbeatStub()
        upsert_heartbeat(conn, "zhijuan-local", "worker", "inst-1", {})
        self.assertEqual(fresh_components(conn, "other-runtime", ttl_seconds=100.0), {})

    def test_same_component_deduplicates_to_most_recent_instance(self):
        conn = _SqliteHeartbeatStub()
        upsert_heartbeat(conn, "zhijuan-local", "worker", "inst-old", {"boot": 1})
        conn._clock = 10.0
        upsert_heartbeat(conn, "zhijuan-local", "worker", "inst-new", {"boot": 2})
        state = fresh_components(conn, "zhijuan-local", ttl_seconds=100.0)
        self.assertEqual(state["worker"]["metadata"]["boot"], 2)
        self.assertEqual(len(state), 1)  # one component row despite two instances

    def test_future_timestamp_is_not_fresh(self):
        conn = _SqliteHeartbeatStub()
        # Write a heartbeat with a timestamp in the future relative to the read.
        conn.conn.execute(
            "INSERT INTO runtime_heartbeats VALUES (?, ?, ?, ?, ?)",
            ("zhijuan-local", "worker", "clock-skewed", 1000.0, "{}"),
        )
        state = fresh_components(conn, "zhijuan-local", ttl_seconds=1000.0)
        self.assertNotIn("worker", state)


class HeartbeatThreadTests(unittest.TestCase):
    def test_instance_id_changes_between_process_starts(self):
        # Two freshly-created threads simulate two process starts.
        first = HeartbeatThread("worker", inst_id=instance_id())
        second = HeartbeatThread("worker", inst_id=instance_id())
        self.assertNotEqual(first.inst_id, second.inst_id)
        self.assertEqual(len(first.inst_id), 32)  # uuid4().hex

    def test_runtime_id_defaults_and_env(self):
        self.assertEqual(runtime_id(), "zhijuan-local")
        with patch.dict(os.environ, {"ZHIJUAN_RUNTIME_ID": "acceptance-b"}, clear=True):
            self.assertEqual(runtime_id(), "acceptance-b")

    def test_gateway_fingerprint_is_non_secret(self):
        with patch.dict(os.environ, {
            "HERMES_API_BASE_URL": "http://127.0.0.1:8644",
            "HERMES_SOLVER_API_BASE_URL": "http://127.0.0.1:8643",
        }, clear=True):
            fp = gateway_role_fingerprint()
            self.assertEqual(fp["author_host_port"], "127.0.0.1:8644")
            self.assertEqual(fp["solver_host_port"], "127.0.0.1:8643")
            self.assertEqual(fp["gateway_config_version"], GATEWAY_ROLE_CONFIG_VERSION)

    def test_start_stop_and_interval(self):
        writes = []
        thread = HeartbeatThread("worker", interval=0.02,
                                 poll=lambda meta: writes.append(dict(meta)),
                                 metadata={"model_id": "test-model"})
        thread.start()
        try:
            deadline = time.monotonic() + 0.5
            while time.monotonic() < deadline and len(writes) < 2:
                time.sleep(0.01)
            self.assertGreaterEqual(len(writes), 2)  # immediate write + interval ticks
        finally:
            thread.stop()
        self.assertIsNone(thread._thread)
        before = len(writes)
        time.sleep(0.06)
        self.assertEqual(len(writes), before)  # no ticks after stop

    def test_metadata_contains_model_id_with_env_override(self):
        with patch.dict(os.environ, {"ZHIJUAN_DEEPSEEK_MODEL_ID": "deepseek-flash"}, clear=True):
            thread = HeartbeatThread("worker", inst_id="i1")
            self.assertEqual(thread.metadata["model_id"], "deepseek-flash")
        self.assertIn("gateway_config_version", thread.metadata)
        self.assertIn("author_host_port", thread.metadata)


class OutboxSchedulerTests(unittest.TestCase):
    def test_scheduler_registers_dispatcher_heartbeat_after_successful_round(self):
        from services.worker.scheduler import OutboxScheduler

        sent = []
        heartbeat = HeartbeatThread("dispatcher", poll=lambda m: sent.append(dict(m)), metadata={"model_id": "m"})
        scheduler = OutboxScheduler(tick_seconds=0.02, heartbeat=heartbeat,
                                    dispatch=lambda: 1, reconcile=lambda: 0)
        thread = threading.Thread(target=scheduler.run, daemon=True)
        thread.start()
        time.sleep(0.15)
        scheduler.stop()
        thread.join(timeout=2.0)
        self.assertFalse(thread.is_alive())
        # Every successful round writes a dispatcher heartbeat.
        self.assertGreaterEqual(len(sent), 1)

    def test_scheduler_stops_cleanly_and_stops_heartbeat(self):
        from services.worker.scheduler import OutboxScheduler

        heartbeat_calls = []
        heartbeat = HeartbeatThread("dispatcher", poll=lambda m: heartbeat_calls.append(1), metadata={})
        scheduler = OutboxScheduler(tick_seconds=0.02, heartbeat=heartbeat,
                                    dispatch=lambda: 0, reconcile=lambda: 0)
        thread = threading.Thread(target=scheduler.run, daemon=True)
        thread.start()
        time.sleep(0.1)
        scheduler.stop()
        thread.join(timeout=2.0)
        self.assertFalse(thread.is_alive())
        self.assertIsNone(heartbeat._thread)  # heartbeat thread joined as well

    def test_scheduler_tick_overrides_env(self):
        from services.worker.scheduler import OutboxScheduler
        with patch.dict(os.environ, {"ZHIJUAN_SCHEDULER_TICK_SECONDS": "0.5"}):
            scheduler = OutboxScheduler()
        self.assertEqual(scheduler.tick_seconds, 0.5)

    def test_scheduler_round_with_mocked_dispatch_outbox_registers_heartbeat(self):
        from services.worker.scheduler import OutboxScheduler

        sent = []
        heartbeat = HeartbeatThread("dispatcher", poll=lambda m: sent.append(dict(m)), metadata={"model_id": "m"})
        scheduler = OutboxScheduler(tick_seconds=0.02, heartbeat=heartbeat)
        with patch("services.worker.jobs.dispatch_outbox", return_value=1) as dispatch, \
             patch("services.worker.jobs.reconcile_stale", return_value=0):
            thread = threading.Thread(target=scheduler.run, daemon=True)
            thread.start()
            time.sleep(0.15)
            scheduler.stop()
            thread.join(timeout=2.0)
            self.assertFalse(thread.is_alive())
            # A successful round must have called dispatch_outbox exactly as a tick.
            dispatch.assert_called()
        self.assertGreaterEqual(len(sent), 1)  # proof-of-life heartbeat written



if __name__ == "__main__":
    unittest.main()
