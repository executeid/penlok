import base64
import asyncio
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import psycopg2

import main


class ASGIClient:
    """Exercise real FastAPI request validation without optional httpx packages."""
    def request(self, method, path, body=None):
        async def run():
            messages = []
            received = False

            async def receive():
                nonlocal received
                if not received:
                    received = True
                    return {"type": "http.request", "body": json.dumps(body).encode() if body else b"", "more_body": False}
                return {"type": "http.disconnect"}

            async def send(message):
                messages.append(message)

            await main.app({"type": "http", "asgi": {"version": "3.0"},
                            "http_version": "1.1", "method": method,
                            "scheme": "http", "path": path,
                            "raw_path": path.encode(), "query_string": b"",
                            "headers": [(b"content-type", b"application/json")],
                            "client": ("127.0.0.1", 1234), "server": ("test", 80)}, receive, send)
            status = next(m["status"] for m in messages if m["type"] == "http.response.start")
            text = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body").decode()
            return type("TestResponse", (), {"status_code": status, "text": text, "json": lambda self: json.loads(self.text)})()
        return asyncio.run(run())

    def post(self, path, json):
        return self.request("POST", path, json)

    def get(self, path):
        return self.request("GET", path)


class CloudApiTests(unittest.TestCase):
    def setUp(self):
        # No lifespan: contract tests must not load GPU models or use live DBs.
        self.client = ASGIClient()
        self.body = {"task_id": "UNIT_cloud_001", "device_id": "test",
                     "image": base64.b64encode(b"image fixture").decode(), "decision": 1}

    def test_success_and_endpoint_aliases(self):
        with patch.object(main, "model_ready", return_value=True), \
             patch.object(main.engine, "verify_face_on_gpu", return_value=("Owner", .9, True)), \
             patch.object(main, "log_task", return_value="postgres") as log:
            for endpoint in ("/migration", "/api/v1/migration", "/api/v1/migrate"):
                response = self.client.post(endpoint, json=self.body)
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data["authorized"])
                self.assertEqual(data["task_id"], self.body["task_id"])
                self.assertEqual(data["audit_backend"], "postgres")
                self.assertGreaterEqual(data["server_total_time_ms"], data["cloud_processing_time_ms"])
            self.assertEqual(log.call_count, 3)

    def test_no_face_is_not_authorized(self):
        with patch.object(main, "model_ready", return_value=True), \
             patch.object(main.engine, "verify_face_on_gpu", return_value=("NO_FACE_DETECTED", 0., False)), \
             patch.object(main, "log_task", return_value="postgres"):
            data = self.client.post("/migration", json=self.body).json()
            self.assertEqual(data["status"], "unauthorized")
            self.assertFalse(data["authorized"])

    def test_native_inference_reuses_one_worker_thread(self):
        threads = set()

        def verify(raw):
            threads.add(threading.get_ident())
            return "Owner", .9, True

        with patch.object(main, "model_ready", return_value=True), \
             patch.object(main.engine, "verify_face_on_gpu", side_effect=verify), \
             patch.object(main, "log_task", return_value="postgres"):
            for _ in range(6):
                self.assertEqual(self.client.post("/migration", json=self.body).status_code, 200)
        self.assertEqual(len(threads), 1)
        self.assertNotIn(threading.get_ident(), threads)

    def test_malformed_image_is_rejected_and_audited(self):
        with patch.object(main, "log_task", return_value="postgres") as log:
            response = self.client.post("/migration", json={**self.body, "image": "not base64!"})
            self.assertEqual(response.status_code, 400)
            self.assertFalse(response.json()["authorized"])
            self.assertEqual(log.call_args.args[3], "error")

    def test_schema_and_routing_validation(self):
        for overrides in ({"decision": 0}, {"task_id": ""}, {"task_id": "bad\nvalue"}, {"device_id": "x" * 33}):
            self.assertEqual(self.client.post("/migration", json={**self.body, **overrides}).status_code, 422)

    def test_no_model_returns_unavailable(self):
        with patch.object(main, "model_ready", return_value=False), \
             patch.object(main, "log_task", return_value="sqlite"):
            self.assertEqual(self.client.post("/migration", json=self.body).status_code, 503)

    def test_audit_failure_does_not_report_success(self):
        with patch.object(main, "model_ready", return_value=True), \
             patch.object(main.engine, "verify_face_on_gpu", return_value=("Owner", .9, True)), \
             patch.object(main, "log_task", return_value="failed"):
            response = self.client.post("/migration", json=self.body)
            self.assertEqual(response.status_code, 503)
            self.assertFalse(response.json()["authorized"])
            self.assertEqual(response.json()["status"], "error")

    def test_sqlite_fallback_persists_real_row(self):
        with tempfile.TemporaryDirectory() as directory:
            target = str(Path(directory) / "audit.db")
            with patch.object(main, "SQLITE_PATH", target), \
                 patch.object(main, "connect_db", side_effect=psycopg2.OperationalError("simulated outage")), \
                 self.assertLogs("cloud_agent", level="ERROR"):
                self.assertEqual(main.log_task("UNIT_fallback", "test", 1.2, "unauthorized", None, 0.), "sqlite")
            with sqlite3.connect(target) as conn:
                self.assertEqual(conn.execute("SELECT task_id,status FROM cloud_task_log").fetchall(),
                                 [("UNIT_fallback", "unauthorized")])

    def test_readiness_reports_database_failure(self):
        with patch.object(main, "model_ready", return_value=True), \
             patch.object(main, "database_available", return_value=False):
            response = self.client.get("/ready")
            self.assertEqual(response.status_code, 503)
            self.assertFalse(response.json()["postgres_available"])

    def test_metrics_are_parseable_and_include_failures(self):
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertIn('cloud_agent_requests_total{status="error"}', response.text)
        self.assertIn('cloud_agent_request_duration_seconds_bucket{le="+Inf"}', response.text)


if __name__ == "__main__":
    unittest.main()
