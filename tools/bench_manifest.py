#!/usr/bin/env python3
"""Write the provenance manifest for ONE benchmark run (Week 5).

Run it from the repo root on your workstation, with the VPN on, after the run's
result files have been copied into evidence/week5/runs/<run_id>/.

Cluster facts (image digests, server settings, model fingerprint, CPU and memory
over the run window) are read with read-only commands over SSH from the control
plane, because kubectl only works there. No secret is ever read: Secret objects
are not queried and environment variables that come from secrets are skipped.

Example:
  python3 tools/bench_manifest.py --run-id 20261122T101500Z-llamacpp-c4 \\
      --tool llama.cpp --concurrency 4 --job bench-abcde --cp-host valencia@10.151.0.11

A failed run gets a manifest too:  --status failed --reason "OOMKilled"
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import urllib.parse
from pathlib import Path

SCHEMA_VERSION = "1.0"
PROJECT = "inference-fabric-scc26"
REPOSITORY = "https://github.com/chpc-tech-eval/inference-fabric-scc26"
TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
SERVERS = {
    "llama.cpp": {"app": "llm-cpu", "deploy": "llm-cpu"},
    "ollama": {"app": "ollama-cpu", "deploy": "ollama-cpu"},
}
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
WARNINGS = []


def warn(message):
    WARNINGS.append(message)
    print("WARNING: " + message, file=sys.stderr)


def cluster(host, command):
    """Run one read-only command on the control plane over SSH."""
    result = subprocess.run(["ssh", "-o", "BatchMode=yes", host, command],
                            capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip()[:200] or "exit status %d" % result.returncode)
    return result.stdout


def kjson(host, args):
    return json.loads(cluster(host, "kubectl " + args + " -o json"))


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_info():
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    changed = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                             capture_output=True, text=True).stdout.strip()
    return commit or None, bool(changed)


def parse_time(value):
    return datetime.datetime.strptime(value, TS_FORMAT).replace(tzinfo=datetime.timezone.utc)


def plain_env(container):
    """Environment variables with a literal value (anything from a Secret is skipped)."""
    return {e["name"]: e["value"] for e in container.get("env", []) if "value" in e}


def parse_flags(args):
    flags = {}
    i = 0
    while i < len(args):
        item = args[i]
        if item.startswith("-"):
            name = item.lstrip("-")
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                value = args[i + 1]
                i += 2
            else:
                value = True
                i += 1
            if "key" not in name:
                flags[name] = value
        else:
            i += 1
    return flags


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def job_info(host, job):
    info = {}
    data = kjson(host, "-n bench get job " + shlex.quote(job))
    info["started_at"] = data.get("status", {}).get("startTime")
    info["finished_at"] = data.get("status", {}).get("completionTime")
    container = data["spec"]["template"]["spec"]["containers"][0]
    info["image"] = container.get("image")
    info["env"] = plain_env(container)
    pods = kjson(host, "-n bench get pods -l job-name=" + shlex.quote(job))
    if pods.get("items"):
        pod = pods["items"][0]
        info["node"] = pod["spec"].get("nodeName")
        statuses = pod.get("status", {}).get("containerStatuses") or [{}]
        info["running_digest"] = statuses[0].get("imageID")
    return info


def server_info(host, tool):
    spec = SERVERS[tool]
    deploy = kjson(host, "-n inference get deploy " + spec["deploy"])
    container = deploy["spec"]["template"]["spec"]["containers"][0]
    info = {
        "container": container["name"],
        "image": container.get("image"),
        "args": container.get("args", []),
        "env": plain_env(container),
        "limits": container.get("resources", {}).get("limits", {}),
        "requests": container.get("resources", {}).get("requests", {}),
        "replicas": deploy["spec"].get("replicas"),
    }
    pods = kjson(host, "-n inference get pods -l app=" + spec["app"])
    if pods.get("items"):
        pod = pods["items"][0]
        info["node"] = pod["spec"].get("nodeName")
        statuses = pod.get("status", {}).get("containerStatuses") or [{}]
        info["running_digest"] = statuses[0].get("imageID")
    else:
        warn("no running pod found for %s (is the server switched on?)" % spec["app"])
    return info


def server_settings(tool, info):
    settings = {"cpu_limit": info["limits"].get("cpu"), "memory_limit": info["limits"].get("memory")}
    if tool == "llama.cpp":
        flags = parse_flags(info["args"])
        threads = to_int(flags.get("threads"))
        parallel = to_int(flags.get("parallel"))
        ctx_total = to_int(flags.get("ctx-size"))
        settings.update({"threads": threads, "parallel": parallel, "ctx_total": ctx_total})
        if ctx_total and parallel:
            settings["ctx_per_request"] = ctx_total // parallel
    else:
        settings["env"] = info["env"]
        settings["note"] = "num_thread and num_ctx are set in the Modelfile (see modelfile_sha256)"
    return settings


def model_info(host, tool, info, model_name):
    out = {"name": model_name}
    spec = SERVERS[tool]
    if tool == "llama.cpp":
        flags = parse_flags(info["args"])
        path = flags.get("m") or flags.get("model")
        out["alias"] = flags.get("alias")
        out["file"] = path
        if path:
            command = ("kubectl -n inference exec deploy/%s -c %s -- sha256sum %s"
                       % (spec["deploy"], info["container"], shlex.quote(path)))
            out["file_sha256"] = cluster(host, command).split()[0]
    else:
        listing = cluster(host, "kubectl -n inference exec deploy/%s -- ollama list" % spec["deploy"])
        for line in listing.splitlines()[1:]:
            columns = line.split()
            if columns and model_name and (columns[0] == model_name or columns[0].startswith(model_name + ":")):
                out["ollama_id"] = columns[1]
                out["ollama_name"] = columns[0]
        if "ollama_id" not in out:
            warn("model %r not found in `ollama list`" % model_name)
    return out


def prom_value(host, query, at_epoch):
    url = "http://127.0.0.1:9090/api/v1/query?query=%s&time=%d" % (urllib.parse.quote(query, safe=""), at_epoch)
    command = ("kubectl -n monitoring exec deploy/prometheus-server -c prometheus-server -- wget -qO- "
               + shlex.quote(url))
    data = json.loads(cluster(host, command))
    result = data.get("data", {}).get("result", [])
    return float(result[0]["value"][1]) if result else None


def resource_use(host, container, started, finished):
    window = int((finished - started).total_seconds())
    if window < 1:
        warn("run window is under a second, resource use skipped")
        return None
    at = int(finished.timestamp())
    cpu_q = ('sum(increase(container_cpu_usage_seconds_total{namespace="inference",container="%s"}[%ds]))'
             % (container, window))
    mem_q = ('max_over_time(sum(container_memory_working_set_bytes{namespace="inference",container="%s"})[%ds:15s])'
             % (container, window))
    cpu = prom_value(host, cpu_q, at)
    mem = prom_value(host, mem_q, at)
    if cpu is None or mem is None:
        warn("Prometheus returned no CPU/memory data for container %s in the run window" % container)
    return {
        "source": "Prometheus (cAdvisor), server container only",
        "window_seconds": window,
        "cpu_cores_avg": round(cpu / window, 3) if cpu is not None else None,
        "memory_gib_max": round(mem / 2 ** 30, 3) if mem is not None else None,
        "note": "cAdvisor is scraped about once a minute, so very short windows are approximate",
    }


def cpu_model_from_record(node):
    record = Path("evidence/week5/hardware-workers.txt")
    if not node or not record.exists():
        return None
    text = record.read_text(errors="replace")
    index = text.find(node.split(".")[0])
    if index < 0:
        return None
    match = re.search(r"Model name:\s*(.+)", text[index:])
    return match.group(1).strip() if match else None


def scalar(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, dict):
        return "{}"
    if isinstance(value, list):
        return "[]"
    return json.dumps(str(value), ensure_ascii=False)


def emit(value, indent=0):
    pad = "  " * indent
    lines = []
    if isinstance(value, dict):
        for key, item in value.items():
            key = re.sub(r"[^A-Za-z0-9_.-]", "_", str(key))
            if isinstance(item, (dict, list)) and item:
                lines.append("%s%s:" % (pad, key))
                lines.extend(emit(item, indent + 1))
            else:
                lines.append("%s%s: %s" % (pad, key, scalar(item)))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and item:
                sub = emit(item, indent + 1)
                sub[0] = pad + "- " + sub[0].lstrip()
                lines.extend(sub)
            else:
                lines.append("%s- %s" % (pad, scalar(item)))
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--tool", required=True, choices=sorted(SERVERS))
    parser.add_argument("--concurrency", type=int, required=True)
    parser.add_argument("--phase", choices=["warm", "cold"], default="warm")
    parser.add_argument("--repeat", type=int, help="repeat number for warm runs (1-3)")
    parser.add_argument("--job", help="name of the Kubernetes Job in namespace bench")
    parser.add_argument("--started", help="UTC start, e.g. 2026-11-22T10:15:00Z (default: from the Job)")
    parser.add_argument("--finished", help="UTC end (default: from the Job)")
    parser.add_argument("--modelfile", default="bench/Modelfile.qwen2.5-1.5b-bench", help="Ollama Modelfile to hash")
    parser.add_argument("--model", help="model name as served (Ollama: the name shown by `ollama list`)")
    parser.add_argument("--status", choices=["completed", "failed"], default="completed")
    parser.add_argument("--reason", help="why the run failed")
    parser.add_argument("--cp-host", help="user@control-plane for SSH (or set CP_HOST)")
    parser.add_argument("--flavor", default="C8.medium", help="OpenStack flavor (from Infrastructure's record)")
    parser.add_argument("--cpu-model", help="CPU model (default: looked up in evidence/week5/hardware-workers.txt)")
    parser.add_argument("--results-dir", help="default: evidence/week5/runs/<run-id>")
    parser.add_argument("--notes")
    parser.add_argument("--no-cluster", action="store_true", help="skip every cluster lookup (offline/test)")
    args = parser.parse_args()

    if not NAME_RE.match(args.run_id):
        sys.exit("run id may only contain letters, digits, dot, dash and underscore")
    if args.job and not NAME_RE.match(args.job):
        sys.exit("job name looks wrong")
    if args.status == "failed" and not args.reason:
        sys.exit("a failed run needs --reason")

    host = args.cp_host or os.environ.get("CP_HOST")
    use_cluster = not args.no_cluster
    if use_cluster and not host:
        sys.exit("give --cp-host user@10.151.0.11 (or set CP_HOST), or use --no-cluster")

    results_dir = Path(args.results_dir or "evidence/week5/runs/%s" % args.run_id)
    results_dir.mkdir(parents=True, exist_ok=True)

    commit, dirty = git_info()
    if dirty:
        warn("tracked files have uncommitted changes (dirty: true)")

    job = {}
    server = {}
    model = {"name": args.model}
    if use_cluster:
        if args.job:
            try:
                job = job_info(host, args.job)
            except Exception as error:
                warn("could not read the Job: %s" % error)
        try:
            server = server_info(host, args.tool)
        except Exception as error:
            warn("could not read the server: %s" % error)
        if server:
            try:
                model = model_info(host, args.tool, server, args.model)
            except Exception as error:
                warn("could not read the model details: %s" % error)

    started_s = args.started or job.get("started_at")
    finished_s = args.finished or job.get("finished_at")
    started = parse_time(started_s) if started_s else None
    finished = parse_time(finished_s) if finished_s else None
    if not (started and finished):
        warn("start/finish time missing: give --started and --finished")

    usage = None
    if use_cluster and server and started and finished:
        try:
            usage = resource_use(host, server["container"], started, finished)
        except Exception as error:
            warn("could not read resource use: %s" % error)

    files = []
    for path in sorted(results_dir.iterdir()):
        if path.is_file() and path.name != "manifest.yaml":
            files.append({"name": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    if not files and args.status == "completed":
        warn("no result files found in %s" % results_dir)

    modelfile = Path(args.modelfile)
    prompts = Path("bench/prompts.jsonl")
    server_node = server.get("node")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": args.run_id,
        "project": PROJECT,
        "status": args.status,
        "started_at": started_s,
        "finished_at": finished_s,
        "run": {"tool": args.tool, "concurrency": args.concurrency, "phase": args.phase, "repeat": args.repeat},
        "source": {"repository": REPOSITORY, "commit": commit, "dirty": dirty},
        "software": {
            "harness_image": job.get("image"),
            "harness_running_digest": job.get("running_digest"),
            "server_image": server.get("running_digest") or server.get("image"),
            "server_settings": server_settings(args.tool, server) if server else None,
        },
        "model": model,
        "inputs": {
            "prompts_sha256": sha256_file(prompts) if prompts.exists() else None,
            "modelfile_sha256": sha256_file(modelfile) if (modelfile.exists() and args.tool == "ollama") else None,
            "harness_env": job.get("env"),
        },
        "hardware": {
            "server_node": server_node,
            "harness_node": job.get("node"),
            "flavor": args.flavor,
            "cpu_model": args.cpu_model or cpu_model_from_record(server_node),
        },
        "results": {"files": files},
        "resource_use": usage,
    }
    if args.status == "failed":
        manifest["failure_reason"] = args.reason
    if args.notes:
        manifest["notes"] = args.notes
    manifest["collection_warnings"] = list(WARNINGS)

    out = results_dir / "manifest.yaml"
    out.write_text("\n".join(emit(manifest)) + "\n")
    print("wrote %s (%d result files, %d warnings)" % (out, len(files), len(WARNINGS)))


if __name__ == "__main__":
    main()
