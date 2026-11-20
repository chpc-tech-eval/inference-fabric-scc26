#!/usr/bin/env python3
"""Benchmark harness: sends a fixed prompt set to an OpenAI-style /v1/chat/completions server
(llama.cpp, Ollama, vLLM) with streaming on, and records timings per request.

Standard library only, so the image needs no pip install and no internet.

Settings come from environment variables:
  TARGET_URL       base URL including /v1, e.g. http://llm-cpu.inference.svc.cluster.local:8080/v1   (required)
  MODEL            model name the server expects                                                      (required)
  RUN_ID           unique run name, letters/digits/._-                                                (required)
  CONCURRENCY      requests in flight at the same time (default 1)
  PHASE            "cold" or "warm", written into every row (default warm)
  API_KEY          bearer key, optional (llama.cpp needs one, Ollama has none). Never printed or saved.
  PROMPTS_FILE     JSON Lines file (default: prompts.jsonl next to this script)
  MAX_PROMPTS      use only the first N prompts, 0 = all (a cold run is MAX_PROMPTS=1, CONCURRENCY=1)
  MAX_TOKENS       fixed, default 256
  TEMPERATURE      fixed, default 0
  REQUEST_TIMEOUT  seconds per request, default 300
  RESULTS_DIR      default /results; files go to RESULTS_DIR/RUN_ID/
  DRY_RUN=1        only check the prompt file and print what would run (no network, no files)

Outputs: results.csv (one row per request) and summary.json (median and p95).
One failed request never stops the run: it is recorded and the run carries on.
Exit code: 0 = finished with at least one good request, 1 = finished but every request failed,
2 = bad settings or prompt file.

Measures (as agreed in the Week 5 guide):
  ttft_s        time from sending until the first streamed piece of answer text
  total_s       time from sending until the last piece
  tokens_per_s  output tokens / (total_s - ttft_s)
Output tokens come from the server's usage figures when it sends them (tokens_source=usage);
otherwise the streamed text pieces are counted (tokens_source=chunks, an approximation).
"""
import csv
import hashlib
import http.client
import json
import math
import os
import platform
import queue
import re
import statistics
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

VERSION = "1.0"
FIELDS = ["run_id", "phase", "prompt_id", "size", "worker", "started_at", "ttft_s", "total_s",
          "prompt_tokens", "output_tokens", "tokens_source", "tokens_per_s", "status", "error"]
SIZES = ("short", "medium", "long")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


class ConfigError(Exception):
    pass


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def load_prompts(path):
    prompts, seen = [], set()
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as e:
        raise ConfigError(f"cannot read prompts file {path}: {e.strerror}")
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            p = json.loads(line)
        except ValueError:
            raise ConfigError(f"{path} line {n}: not valid JSON")
        if not isinstance(p, dict) or not isinstance(p.get("id"), str) or not p["id"]:
            raise ConfigError(f"{path} line {n}: needs a string 'id'")
        if p.get("size") not in SIZES:
            raise ConfigError(f"{path} line {n}: 'size' must be one of {SIZES}")
        if not isinstance(p.get("prompt"), str) or not p["prompt"].strip():
            raise ConfigError(f"{path} line {n}: needs a non-empty 'prompt'")
        if p["id"] in seen:
            raise ConfigError(f"{path} line {n}: duplicate id {p['id']}")
        seen.add(p["id"])
        prompts.append(p)
    if not prompts:
        raise ConfigError(f"{path}: no prompts")
    return prompts


def _number(env, name, default, cast, minimum):
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        v = cast(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a number, got '{raw}'")
    if v < minimum:
        raise ConfigError(f"{name} must be at least {minimum}")
    return v


def load_config(env):
    cfg = {}
    default_prompts = str(Path(__file__).with_name("prompts.jsonl"))
    cfg["prompts_file"] = env.get("PROMPTS_FILE", "").strip() or default_prompts
    if env.get("DRY_RUN", "").strip() == "1":
        cfg["dry_run"] = True
        return cfg
    cfg["dry_run"] = False
    for name in ("TARGET_URL", "MODEL", "RUN_ID"):
        if not env.get(name, "").strip():
            raise ConfigError(f"{name} is required")
    cfg["target_url"] = env["TARGET_URL"].strip()
    u = urlparse(cfg["target_url"])
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ConfigError("TARGET_URL must look like http://host:port/v1")
    cfg["model"] = env["MODEL"].strip()
    cfg["run_id"] = env["RUN_ID"].strip()
    if not RUN_ID_RE.match(cfg["run_id"]):
        raise ConfigError("RUN_ID may only contain letters, digits, '.', '_' and '-' (max 100)")
    cfg["concurrency"] = _number(env, "CONCURRENCY", 1, int, 1)
    cfg["max_prompts"] = _number(env, "MAX_PROMPTS", 0, int, 0)
    cfg["max_tokens"] = _number(env, "MAX_TOKENS", 256, int, 1)
    cfg["temperature"] = _number(env, "TEMPERATURE", 0.0, float, 0.0)
    cfg["timeout"] = _number(env, "REQUEST_TIMEOUT", 300.0, float, 1.0)
    cfg["phase"] = env.get("PHASE", "").strip().lower() or "warm"
    if cfg["phase"] not in ("cold", "warm"):
        raise ConfigError("PHASE must be 'cold' or 'warm'")
    cfg["api_key"] = env.get("API_KEY", "").strip()
    cfg["results_dir"] = env.get("RESULTS_DIR", "").strip() or "/results"
    return cfg


def _clean(text, limit=200):
    return re.sub(r"\s+", " ", str(text)).strip()[:limit]


def one_request(cfg, item, worker):
    """Send one prompt and return one result row. Never raises."""
    row = {"run_id": cfg["run_id"], "phase": cfg["phase"], "prompt_id": item["id"],
           "size": item["size"], "worker": worker, "started_at": utc_now(), "ttft_s": "",
           "total_s": "", "prompt_tokens": "", "output_tokens": "", "tokens_source": "",
           "tokens_per_s": "", "status": "error", "error": ""}
    u = urlparse(cfg["target_url"])
    path = u.path.rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": cfg["model"],
        "messages": [{"role": "user", "content": item["prompt"]}],
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
    })
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    if cfg["api_key"]:
        headers["Authorization"] = "Bearer " + cfg["api_key"]
    conn_cls = http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection
    conn = None
    t0 = time.perf_counter()
    ttft = None
    chunks = 0
    usage = None
    try:
        conn = conn_cls(u.hostname, u.port, timeout=cfg["timeout"])
        conn.request("POST", path, body, headers)
        resp = conn.getresponse()
        if resp.status != 200:
            detail = _clean(resp.read(500).decode("utf-8", "replace"))
            row["status"] = f"http_{resp.status}"
            row["error"] = detail
            row["total_s"] = round(time.perf_counter() - t0, 4)
            return row
        while True:
            if time.perf_counter() - t0 > cfg["timeout"]:
                raise TimeoutError("request exceeded REQUEST_TIMEOUT")
            line = resp.readline()
            if not line:
                break
            line = line.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                obj = json.loads(payload)
            except ValueError:
                continue
            if isinstance(obj.get("usage"), dict):
                usage = obj["usage"]
            for ch in obj.get("choices") or []:
                text = (ch.get("delta") or {}).get("content")
                if text:
                    chunks += 1
                    if ttft is None:
                        ttft = time.perf_counter() - t0
        total = time.perf_counter() - t0
        row["total_s"] = round(total, 4)
        if ttft is None:
            row["status"] = "no_content"
            row["error"] = "the server sent no answer text"
            return row
        row["ttft_s"] = round(ttft, 4)
        if usage and isinstance(usage.get("completion_tokens"), int):
            out = usage["completion_tokens"]
            row["tokens_source"] = "usage"
        else:
            out = chunks
            row["tokens_source"] = "chunks"
        if usage and isinstance(usage.get("prompt_tokens"), int):
            row["prompt_tokens"] = usage["prompt_tokens"]
        row["output_tokens"] = out
        decode = total - ttft
        if out > 0 and decode > 0:
            row["tokens_per_s"] = round(out / decode, 3)
        row["status"] = "ok"
        return row
    except TimeoutError as e:
        row["status"], row["error"] = "timeout", _clean(e)
    except OSError as e:  # socket.timeout, connection refused/reset
        timed_out = "timed out" in str(e).lower()
        row["status"] = "timeout" if timed_out else "connection_error"
        row["error"] = _clean(f"{type(e).__name__}: {e}")
    except Exception as e:  # keep going whatever happens
        row["status"], row["error"] = "error", _clean(f"{type(e).__name__}: {e}")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    row["total_s"] = round(time.perf_counter() - t0, 4)
    return row


def percentile(values, p):
    """Nearest-rank percentile: simple, and the same answer for anyone who recomputes it."""
    s = sorted(values)
    return s[max(1, math.ceil(p / 100 * len(s))) - 1]


def stat(values):
    values = [float(v) for v in values if v != ""]
    if not values:
        return None
    return {"n": len(values), "median": round(statistics.median(values), 4),
            "p95": round(percentile(values, 95), 4), "min": round(min(values), 4),
            "max": round(max(values), 4)}


def summarise(cfg, rows, wall_s, started_at, finished_at, prompts_sha):
    ok = [r for r in rows if r["status"] == "ok"]
    by_status = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    out_tokens = sum(r["output_tokens"] for r in ok)
    summary = {
        "harness_version": VERSION,
        "run_id": cfg["run_id"],
        "phase": cfg["phase"],
        "started_at": started_at,
        "finished_at": finished_at,
        "config": {"target_url": cfg["target_url"], "model": cfg["model"],
                   "concurrency": cfg["concurrency"], "max_tokens": cfg["max_tokens"],
                   "temperature": cfg["temperature"], "max_prompts": cfg["max_prompts"],
                   "request_timeout_s": cfg["timeout"], "api_key_used": bool(cfg["api_key"])},
        "prompts_sha256": prompts_sha,
        "requests": len(rows),
        "ok": len(ok),
        "failed": len(rows) - len(ok),
        "by_status": by_status,
        "wall_s": round(wall_s, 3),
        "total_output_tokens": out_tokens,
        "aggregate_tokens_per_s": round(out_tokens / wall_s, 3) if wall_s > 0 and out_tokens else None,
        "ttft_s": stat([r["ttft_s"] for r in ok]),
        "total_s": stat([r["total_s"] for r in ok]),
        "tokens_per_s": stat([r["tokens_per_s"] for r in ok]),
        "token_count_sources": sorted({r["tokens_source"] for r in ok}),
        "by_size": {},
        "python": platform.python_version(),
        "host": platform.node(),
    }
    for size in SIZES:
        sub = [r for r in ok if r["size"] == size]
        if sub:
            summary["by_size"][size] = {"ok": len(sub), "ttft_s": stat([r["ttft_s"] for r in sub]),
                                        "total_s": stat([r["total_s"] for r in sub]),
                                        "tokens_per_s": stat([r["tokens_per_s"] for r in sub])}
    return summary


def write_atomic(path, text):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def run(cfg, prompts):
    work = queue.Queue()
    for item in prompts:
        work.put(item)
    rows, lock = [], threading.Lock()

    def worker(n):
        while True:
            try:
                item = work.get_nowait()
            except queue.Empty:
                return
            row = one_request(cfg, item, n)
            with lock:
                rows.append(row)

    started_at = utc_now()
    t0 = time.perf_counter()
    threads = [threading.Thread(target=worker, args=(i + 1,), daemon=True)
               for i in range(min(cfg["concurrency"], len(prompts)))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.perf_counter() - t0
    order = {p["id"]: i for i, p in enumerate(prompts)}
    rows.sort(key=lambda r: order[r["prompt_id"]])
    return rows, wall, started_at, utc_now()


def main(env=None):
    env = os.environ if env is None else env
    try:
        cfg = load_config(env)
        prompts = load_prompts(cfg["prompts_file"])
    except ConfigError as e:
        print(f"CONFIG ERROR: {e}", file=sys.stderr)
        return 2
    prompts_sha = hashlib.sha256(Path(cfg["prompts_file"]).read_bytes()).hexdigest()
    if cfg["dry_run"]:
        counts = {s: sum(1 for p in prompts if p["size"] == s) for s in SIZES}
        print(f"DRY_RUN_OK {len(prompts)} prompts {counts} sha256={prompts_sha}")
        return 0
    if cfg["max_prompts"]:
        prompts = prompts[:cfg["max_prompts"]]
    out_dir = Path(cfg["results_dir"]) / cfg["run_id"]
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"CONFIG ERROR: cannot create {out_dir}: {e.strerror}", file=sys.stderr)
        return 2
    print(f"run {cfg['run_id']}: {len(prompts)} prompts, concurrency {cfg['concurrency']}, "
          f"phase {cfg['phase']}, model {cfg['model']}", flush=True)
    rows, wall, started_at, finished_at = run(cfg, prompts)
    tmp_csv = out_dir / "results.csv"
    with open(str(tmp_csv) + ".tmp", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    os.replace(str(tmp_csv) + ".tmp", tmp_csv)
    summary = summarise(cfg, rows, wall, started_at, finished_at, prompts_sha)
    write_atomic(out_dir / "summary.json", json.dumps(summary, indent=2) + "\n")
    print(f"done: {summary['ok']}/{summary['requests']} ok in {summary['wall_s']} s; "
          f"failures {summary['by_status']}; results in {out_dir}", flush=True)
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
