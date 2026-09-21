# Open LLM Inference Fabric — Ollama, llama.cpp & vLLM on CPU/GPU

**Repository:** `inference-fabric-scc26`  
**Recommended long name:** **Open LLM Inference Fabric: Ollama, llama.cpp & vLLM on CPU/GPU**  
**Duration:** 10-week core, 12 weeks with stretch/handover

## Project summary

This project goes underneath Hermes and studies the model-serving substrate itself. Students deploy and benchmark **Ollama**, **llama.cpp** and **vLLM** across the available execution classes—CPU nodes and, where allocated, A100/H200 GPU resources—then build an evidence-based routing catalogue that `agent-control-plane` can consume later.

The goal is not to declare one runtime universally “best”. Each runtime solves a different operational problem. Students must discover and document the boundaries empirically:

- ease of deployment and model management;
- supported model formats and quantisation paths;
- CPU/GPU portability;
- throughput and latency under concurrency;
- VRAM/RAM behaviour and context-length pressure;
- multi-GPU and distributed-serving capabilities;
- observability and failure recovery;
- suitability for interactive Hermes agents versus high-throughput shared services.

## Core question

> Given a model, hardware class and service objective, what measurable evidence should the platform use to choose an inference runtime and resource placement?

## Primary integrations

- `infra-hpc-qc-k8s` — Kubernetes/GPU deployment, scheduling, storage and telemetry;
- `agent-control-plane` — model catalogue, execution classes and future routing decisions;
- Hermes — representative interactive agent workload;
- `quantum-platform` — optional administrative view of model endpoints and health.

## Learning outcomes

Students should be able to:

- explain model serving separately from agent orchestration;
- deploy the same logical model behind multiple inference APIs;
- reason about quantisation, VRAM, KV cache and context length;
- benchmark TTFT, inter-token latency, throughput and concurrency;
- use Kubernetes resource requests/limits, node labels and affinity for placement;
- compare CPU and GPU execution honestly;
- collect GPU/CPU telemetry alongside application metrics;
- design a runtime-neutral model endpoint catalogue;
- identify when a runtime feature matters operationally rather than only theoretically.

## Scope

### Must deliver

1. Reproducible deployment of Ollama.
2. Reproducible deployment of `llama.cpp` server.
3. Reproducible deployment of vLLM.
4. At least one common model/workload that can be compared fairly across all compatible runtimes.
5. CPU baseline for at least Ollama and `llama.cpp` where practical.
6. GPU baseline on at least one allocated NVIDIA GPU class.
7. Benchmark harness producing machine-readable results.
8. Prometheus-compatible metrics or an exporter/collector path for request and resource telemetry.
9. Kubernetes scheduling manifests showing explicit resource placement.
10. A runtime/model/execution-class catalogue suitable for later `agent-control-plane` dry-run routing.

### Should deliver

- A100 vs H200 comparison where resource allocations permit;
- multiple quantisation/precision variants;
- concurrent interactive-agent load versus batch throughput load;
- graceful model-server health/readiness handling;
- a Hermes profile that can switch between approved inference endpoints without changing agent identity/state;
- cost/resource-efficiency metric such as tokens/s per GPU or tokens/s per GB VRAM.

### Stretch

- multi-GPU vLLM deployment;
- `llama.cpp` multi-GPU experiments;
- AMD ROCm experiment on available hardware;
- Kubernetes LeaderWorkerSet/Ray or another reviewed distributed-serving mechanism;
- control-plane routing policy that recommends an execution class in dry-run mode based on benchmark evidence.

## Non-goals

- training foundation models;
- fine-tuning as a core deliverable;
- declaring a universal winner;
- letting the control plane schedule expensive jobs autonomously before evidence/policy is reviewed;
- benchmarking different models and then attributing differences to serving runtimes.

## Architecture

```text
                          Hermes / test clients
                                  │
                       OpenAI-compatible requests
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
              Ollama          llama.cpp            vLLM
                │                 │                 │
          model/runtime      model/runtime      model/runtime
                │                 │                 │
                └────────────── Kubernetes ─────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                   CPU           A100          H200
                    │             │             │
                    └──── resource telemetry ───┘
                                  │
                         benchmark/result store
                                  │
                         agent-control-plane
                         catalogue / dry-run
```

## Benchmark methodology

A valid comparison keeps the following as constant as possible:

- model family and model content;
- prompt corpus;
- output token targets;
- context length;
- concurrency level;
- warm/cold-start definition;
- hardware allocation;
- precision/quantisation category when supported;
- request API semantics.

Record at least:

- time to first token (TTFT), p50/p95;
- inter-token latency or tokens/second;
- end-to-end request latency, p50/p95;
- aggregate throughput under concurrency;
- CPU utilisation;
- RAM usage;
- GPU utilisation;
- VRAM usage;
- model load/start time;
- error/OOM/retry count;
- model, runtime and image versions.

## Runtime hypotheses to test

These are hypotheses, not predetermined conclusions:

### Ollama
Likely strong for simple model lifecycle and developer ergonomics. Students should test how well those conveniences translate into multi-user/Kubernetes operations.

### llama.cpp
Designed for broad hardware portability, quantised inference and CPU/GPU flexibility. Students should test how its deployment simplicity, GGUF ecosystem and CPU/GPU offload compare with the other runtimes.

### vLLM
Designed for high-throughput model serving and sophisticated GPU scheduling/batching. Students should test whether its throughput advantages matter for shared Hermes services and what operational complexity accompanies them.

## Runtime-neutral catalogue

A project outcome should resemble:

```yaml
models:
  - id: example-model
    logical_name: example-model
    endpoints:
      - runtime: llama.cpp
        execution_class: cpu-large
        endpoint_ref: llama-example-cpu
        measured:
          ttft_p50_ms: 0
          tokens_per_second: 0
      - runtime: vllm
        execution_class: h200-single
        endpoint_ref: vllm-example-h200
        measured:
          ttft_p50_ms: 0
          tokens_per_second: 0
```

The control plane should refer to logical endpoint IDs, not embed cluster credentials or raw secrets.

## Repository layout

```text
inference-fabric-scc26/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BENCHMARK-METHODOLOGY.md
│   ├── MODEL-CATALOGUE.md
│   └── OPERATIONS.md
├── deploy/
│   ├── ollama/
│   ├── llama-cpp/
│   └── vllm/
├── benchmarks/
│   ├── prompts/
│   ├── harness/
│   └── schemas/
├── catalog/
├── dashboards/
├── tests/
└── .github/workflows/
```

## Ten-week roadmap

### Week 1 — Baseline and methodology

- choose one fair comparison model/workload;
- define benchmark schema;
- establish CPU and GPU execution classes;
- create simple client load generator.

### Week 2 — Ollama

Deploy, instrument and benchmark one baseline. Document model lifecycle, storage and health behaviour.

### Week 3 — llama.cpp

Deploy equivalent model/quantisation where possible. Benchmark and document CPU/GPU device behaviour.

### Week 4 — vLLM

Deploy GPU baseline. Validate batching/concurrency and readiness behaviour.

### Week 5 — Fair comparison suite

Run controlled benchmarks across compatible configurations. Produce first comparative report; identify invalid comparisons and rerun them rather than hiding them.

### Week 6 — Kubernetes scheduling

- node labels/affinity;
- GPU requests;
- resource limits;
- placement failures;
- model storage lifecycle;
- safe rolling restart/update.

### Week 7 — Hermes integration

One persistent Hermes profile uses a runtime-neutral endpoint configuration. Demonstrate inference backend changes without losing the agent's platform identity or control-plane audit semantics.

### Week 8 — Concurrency and failure

- multiple simultaneous sessions;
- context pressure;
- OOM behaviour;
- runtime restart;
- unavailable GPU node;
- metrics and alerts.

### Week 9 — Staging catalogue

Freeze `stag`, generate the model/runtime/execution-class catalogue from accepted benchmark evidence and test a dry-run routing query.

### Week 10 — Final demo

Serve the same representative workload through the three runtimes, show benchmark evidence and telemetry, explain appropriate use cases and limitations, and demonstrate that routing recommendations are evidence-driven rather than hard-coded preference.

### Weeks 11–12 — Stretch

Multi-GPU/distributed serving, ROCm portability, richer routing policy and upstream integration.

## Acceptance criteria

The team must provide a repeatable benchmark run for each core runtime, machine-readable evidence, exact image/runtime/model versions, resource telemetry and a technically defensible explanation of when each runtime is appropriate. The conclusion must be workload- and hardware-specific rather than a universal ranking.

## Upstream contribution targets

- `infra-hpc-qc-k8s`: reusable inference deployment patterns, GPU scheduling and dashboards;
- `agent-control-plane`: model endpoint/execution-class catalogue and dry-run routing contract;
- `quantum-platform`: optional endpoint health/admin visibility.
