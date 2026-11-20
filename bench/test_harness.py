"""Tests for harness.py against a fake OpenAI-style streaming server. Run: python -m unittest -v bench/test_harness.py"""
import csv
import json
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import harness  # noqa: E402

PROMPTS = Path(__file__).with_name("prompts.jsonl")
KEY = "test-key-12345"


class Fake(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, require_key=None, send_usage=True, chunk_delay=0.01, chunks=6):
        super().__init__(("127.0.0.1", 0), Handler)
        self.require_key, self.send_usage = require_key, send_usage
        self.chunk_delay, self.chunks = chunk_delay, chunks
        self.active = self.max_active = 0
        self.lock = threading.Lock()
        self.seen_keys = []

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_address[1]}/v1"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        srv = self.server
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n))
        if self.path != "/v1/chat/completions":
            return self._send(404, '{"error":"not found"}')
        srv.seen_keys.append(self.headers.get("Authorization", ""))
        if srv.require_key and self.headers.get("Authorization") != f"Bearer {srv.require_key}":
            return self._send(401, '{"error":{"message":"Invalid API Key"}}')
        text = req["messages"][0]["content"]
        if text.startswith("Summarise what a load balancer"):   # exactly one prompt in the set fails
            return self._send(500, '{"error":"boom"}')
        assert req["stream"] is True and req["temperature"] == 0 and req["max_tokens"] == 256
        with srv.lock:
            srv.active += 1
            srv.max_active = max(srv.max_active, srv.active)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()

            def piece(s):
                b = s.encode()
                self.wfile.write(f"{len(b):x}\r\n".encode() + b + b"\r\n")
                self.wfile.flush()

            piece("data: " + json.dumps({"choices": [{"delta": {"role": "assistant"}}]}) + "\n\n")
            for i in range(srv.chunks):
                time.sleep(srv.chunk_delay)
                piece("data: " + json.dumps({"choices": [{"delta": {"content": f"w{i} "}}]}) + "\n\n")
            # The request counts as finished before the client can read the end of the stream, so the
            # client's next request can never overlap it in the server's count.
            with srv.lock:
                srv.active -= 1
                finished = True
            if srv.send_usage:
                piece("data: " + json.dumps({"choices": [], "usage": {"prompt_tokens": 40, "completion_tokens": srv.chunks + 1}}) + "\n\n")
            piece("data: [DONE]\n\n")
            self.wfile.write(b"0\r\n\r\n")
        finally:
            if not locals().get("finished"):
                with srv.lock:
                    srv.active -= 1


class HarnessTests(unittest.TestCase):
    def run_harness(self, srv, **extra):
        tmp = tempfile.mkdtemp()
        env = {"TARGET_URL": srv.url, "MODEL": "fake", "RUN_ID": "t1", "PROMPTS_FILE": str(PROMPTS),
               "RESULTS_DIR": tmp, **extra}
        code = harness.main(env)
        out = Path(tmp) / env["RUN_ID"]
        rows = []
        if (out / "results.csv").exists():
            with open(out / "results.csv", newline="") as f:
                rows = list(csv.DictReader(f))
        summary = json.loads((out / "summary.json").read_text()) if (out / "summary.json").exists() else None
        text = "".join(p.read_text() for p in out.glob("*")) if out.exists() else ""
        return code, rows, summary, text

    def serve(self, **kw):
        srv = Fake(**kw)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        return srv

    def test_prompt_set_is_as_agreed(self):
        p = harness.load_prompts(PROMPTS)
        sizes = [x["size"] for x in p]
        self.assertEqual((sizes.count("short"), sizes.count("medium"), sizes.count("long")), (7, 7, 6))
        self.assertEqual(len({x["id"] for x in p}), 20)
        # about 1.5 tokens per word is generous; 4096 context minus 256 answer tokens must fit
        for x in p:
            self.assertLess(len(x["prompt"].split()) * 2.5, 4096 - 256)

    def test_one_request_per_prompt_with_timings(self):
        srv = self.serve()
        code, rows, summary, _ = self.run_harness(srv, KEY_UNUSED="x")
        self.assertEqual(code, 0)
        self.assertEqual(len(rows), 20)
        ok = [r for r in rows if r["status"] == "ok"]
        self.assertEqual(len(ok), 19)                     # the "load balancer" prompt returns 500
        for r in ok:
            self.assertGreater(float(r["ttft_s"]), 0)
            self.assertGreaterEqual(float(r["total_s"]), float(r["ttft_s"]))
            self.assertEqual(r["tokens_source"], "usage")
            self.assertEqual(r["output_tokens"], "7")
            self.assertEqual(r["prompt_tokens"], "40")
            self.assertTrue(r["tokens_per_s"])
        self.assertEqual(summary["ok"], 19)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["by_status"], {"ok": 19, "http_500": 1})
        self.assertIsNotNone(summary["ttft_s"]["median"])
        self.assertLessEqual(summary["ttft_s"]["median"], summary["ttft_s"]["p95"])
        self.assertEqual(len(summary["prompts_sha256"]), 64)

    def test_failure_does_not_stop_the_run(self):
        srv = self.serve()
        code, rows, summary, _ = self.run_harness(srv)
        failed = [r for r in rows if r["status"] != "ok"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["status"], "http_500")
        self.assertIn("boom", failed[0]["error"])
        self.assertEqual(code, 0)

    def test_results_follow_prompt_order(self):
        srv = self.serve()
        _, rows, _, _ = self.run_harness(srv, CONCURRENCY="4")
        ids = [r["prompt_id"] for r in rows]
        self.assertEqual(ids, [p["id"] for p in harness.load_prompts(PROMPTS)])

    def test_concurrency_is_really_concurrent(self):
        srv = self.serve(chunk_delay=0.03, chunks=8)
        _, rows, summary, _ = self.run_harness(srv, CONCURRENCY="4")
        # never more than the setting, and really overlapping (a loaded machine may start the last worker late)
        self.assertLessEqual(srv.max_active, 4)
        self.assertGreaterEqual(srv.max_active, 2)
        self.assertLessEqual({r["worker"] for r in rows}, {"1", "2", "3", "4"})
        srv2 = self.serve(chunk_delay=0.03, chunks=8)
        self.run_harness(srv2, CONCURRENCY="1")
        self.assertEqual(srv2.max_active, 1)

    def test_api_key_is_sent_but_never_saved(self):
        srv = self.serve(require_key=KEY)
        code, rows, summary, text = self.run_harness(srv, API_KEY=KEY)
        self.assertEqual(code, 0)
        self.assertNotIn(KEY, text)
        self.assertTrue(summary["config"]["api_key_used"])
        self.assertIn(f"Bearer {KEY}", srv.seen_keys)

    def test_wrong_key_records_401_and_exit_1(self):
        srv = self.serve(require_key=KEY)
        code, rows, summary, text = self.run_harness(srv, API_KEY="wrong")
        self.assertEqual(code, 1)
        self.assertEqual({r["status"] for r in rows}, {"http_401"})
        self.assertEqual(len(rows), 20)
        self.assertNotIn("wrong", text.replace("wrong_", ""))  # key value itself is not stored

    def test_counts_chunks_when_server_sends_no_usage(self):
        srv = self.serve(send_usage=False, chunks=5)
        _, rows, summary, _ = self.run_harness(srv)
        ok = [r for r in rows if r["status"] == "ok"]
        self.assertEqual({r["tokens_source"] for r in ok}, {"chunks"})
        self.assertEqual({r["output_tokens"] for r in ok}, {"5"})
        self.assertEqual(summary["token_count_sources"], ["chunks"])

    def test_cold_run_one_prompt_labelled(self):
        srv = self.serve()
        # first prompt is the "load balancer" one, so use MAX_PROMPTS=2 and check labelling + limit
        _, rows, summary, _ = self.run_harness(srv, MAX_PROMPTS="2", PHASE="cold")
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["phase"] for r in rows}, {"cold"})
        self.assertEqual(summary["phase"], "cold")

    def test_unreachable_server_is_recorded_not_crashed(self):
        tmp = tempfile.mkdtemp()
        env = {"TARGET_URL": "http://127.0.0.1:9/v1", "MODEL": "fake", "RUN_ID": "dead",
               "PROMPTS_FILE": str(PROMPTS), "RESULTS_DIR": tmp, "MAX_PROMPTS": "3"}
        self.assertEqual(harness.main(env), 1)
        with open(Path(tmp) / "dead" / "results.csv", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual({r["status"] for r in rows}, {"connection_error"})

    def test_bad_settings_exit_2(self):
        for env in ({"MODEL": "m", "RUN_ID": "r"},
                    {"TARGET_URL": "http://x/v1", "MODEL": "m"},
                    {"TARGET_URL": "http://x/v1", "MODEL": "m", "RUN_ID": "../evil"},
                    {"TARGET_URL": "ftp://x/v1", "MODEL": "m", "RUN_ID": "r"},
                    {"TARGET_URL": "http://x/v1", "MODEL": "m", "RUN_ID": "r", "CONCURRENCY": "0"},
                    {"TARGET_URL": "http://x/v1", "MODEL": "m", "RUN_ID": "r", "CONCURRENCY": "abc"},
                    {"TARGET_URL": "http://x/v1", "MODEL": "m", "RUN_ID": "r", "PHASE": "tepid"},
                    {"TARGET_URL": "http://x/v1", "MODEL": "m", "RUN_ID": "r", "PROMPTS_FILE": "/nope.jsonl"}):
            env = {**env, "RESULTS_DIR": tempfile.mkdtemp()}
            env.setdefault("PROMPTS_FILE", str(PROMPTS))
            self.assertEqual(harness.main(env), 2, env)

    def test_bad_prompt_file_exit_2(self):
        bad = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        bad.write('{"id":"a","size":"huge","prompt":"x"}\n')
        bad.close()
        env = {"TARGET_URL": "http://x/v1", "MODEL": "m", "RUN_ID": "r", "PROMPTS_FILE": bad.name,
               "RESULTS_DIR": tempfile.mkdtemp()}
        self.assertEqual(harness.main(env), 2)

    def test_dry_run_needs_no_server_and_writes_nothing(self):
        tmp = tempfile.mkdtemp()
        self.assertEqual(harness.main({"DRY_RUN": "1", "PROMPTS_FILE": str(PROMPTS), "RESULTS_DIR": tmp}), 0)
        self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_percentile_is_nearest_rank(self):
        self.assertEqual(harness.percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95), 10)
        self.assertEqual(harness.percentile([5], 95), 5)
        self.assertEqual(harness.percentile(list(range(1, 101)), 95), 95)


if __name__ == "__main__":
    unittest.main()
