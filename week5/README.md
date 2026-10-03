# Week 5 — CPU/GPU Inference Runtime Benchmarking

This week studies the model-serving substrate itself. Compare **Ollama, llama.cpp and vLLM** using controlled workloads and explicit placement across CPU, A100 and H200 where authorised.

The question is not “which runtime is best?” The question is:

> Under the same model/workload constraints, what measurable evidence makes each runtime appropriate for a particular execution class?

## Control plane vs compute plane

Keep the Week-4 ACP/Hermes control-side service small. Serving experiments run on the separately assigned CPU/GPU systems:

```text
Student Platform / Hermes clients
          ↓ OpenAI-compatible requests
benchmark endpoint(s)
          ↓
CPU / A100 / H200 serving runtime
```

Do not grant the GPU servers your Kubernetes cluster-admin credentials.

## Experiment order

```text
1. Freeze prompt corpus/model identity/measurement code
2. CPU baseline: Ollama + llama.cpp where practical
3. Validate benchmark harness on a tiny deterministic workload
4. A100 baseline per approved runtime
5. H200 baseline per approved runtime
6. Warm/cold start tests
7. Concurrency sweep
8. Capture CPU/RAM/GPU/VRAM telemetry
9. Failure/OOM/timeout observations
10. Publish runtime/model/execution-class catalogue
11. Optional ACP dry-run routing experiment based on measured evidence
```

## Keep comparisons fair

Hold constant where technically possible:

- exact model/revision/content;
- prompt corpus;
- context and output-token targets;
- concurrency levels;
- warm/cold definition;
- precision/quantisation category;
- hardware allocation;
- API semantics.

If a runtime cannot support one of these equivalently, document the mismatch rather than pretending the comparison is identical.

## Metrics

Capture at least:

```text
TTFT p50/p95
end-to-end latency p50/p95
inter-token latency or output tokens/s
aggregate throughput at concurrency N
load/start time
CPU utilisation + RAM
GPU utilisation + VRAM
errors / OOM / retry count
model/runtime/image versions
```

## Provenance/result structure

Borrow the `quantum-workflows` result philosophy:

```text
project/results/<experiment>/<timestamp>-<run-id>/
├── manifest.json
├── summary.json
└── data/
    ├── requests.csv
    └── telemetry.csv
```

The manifest records Git SHA, immutable runner/server image, runtime/model ID, hardware class, parameters and timings. It never contains API keys.

## CI

The benchmark code itself must have credential-free unit/smoke tests in GitHub Actions. Hardware runs are opt-in/manual and must not consume GPU resources on every PR.

## Runtime catalogue deliverable

Produce a machine-readable table such as:

```yaml
models:
  - logical_name: <model>
    endpoints:
      - runtime: vllm
        execution_class: h200
        evidence_run: <run-id>
        constraints:
          max_tested_context: <value>
        observed:
          ttft_p50_ms: <value>
          throughput_tok_s: <value>
```

This catalogue is evidence, not an automatic scheduler yet.

## Exit gate

At least one common workload has comparable CPU and GPU evidence, each claimed result traces to an immutable run manifest, and the team can explain where the comparison is and is not scientifically fair.
