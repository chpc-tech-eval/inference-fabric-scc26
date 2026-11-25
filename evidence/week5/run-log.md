# Week 5 run log

Run ID format: `<tool>-c<users>-<cold|warm><n>-<YYYYMMDD>` (UTC). Each run folder under `runs/` holds `results.csv`, `summary.json`, `manifest.yaml`, `quiet-node.txt`.
Quiet = 1-minute load on k8s-worker-01 before the run (under 1.0 counts as quiet).

## Check runs (kept for the record)

| Run | Result | Why it did not count |
|---|---|---|
| cold-001 / warm-001 (first image `8f6ac68b…`) | ran | prompt l06 was a duplicate of l01, so llama.cpp served it from the prompt cache; TTFT too low. Fixed in PR #120. |
| warm-002 | ran | identical prompts across runs hit llama.cpp's cache. Fixed in PR #121 (CACHE_BUST tag). |
| warm-003 | ran | used to confirm the fix. Final image `39592c92…` used for everything below. |

## Measured runs (all completed, no failed runs)

| Run | Tool | Users | Phase | Date | OK | Quiet load | Notes |
|---|---|---|---|---|---|---|---|
| llamacpp-c1-cold1-20261124 | llama.cpp | 1 | cold | 11-24 | 1/1 | 0.16 | server idle about 6 min before the request; no CPU sample |
| llamacpp-c1-warm1-20261124 | llama.cpp | 1 | warm | 11-24 | 20/20 | 0.19 | |
| llamacpp-c1-warm2-20261124 | llama.cpp | 1 | warm | 11-24 | 20/20 | 0.07 | |
| llamacpp-c1-warm3-20261124 | llama.cpp | 1 | warm | 11-24 | 20/20 | 0.83 | borderline |
| llamacpp-c2-warm1-20261124 | llama.cpp | 2 | warm | 11-24 | 20/20 | 0.98 | borderline (previous run's load decaying) |
| llamacpp-c2-warm2-20261124 | llama.cpp | 2 | warm | 11-24 | 20/20 | 0.67 | TTFT p95 6.38 s, the highest of the llama.cpp runs |
| llamacpp-c2-warm3-20261124 | llama.cpp | 2 | warm | 11-24 | 20/20 | 0.71 | |
| llamacpp-c4-warm1-20261124 | llama.cpp | 4 | warm | 11-24 | 20/20 | 0.56 | |
| llamacpp-c4-warm2-20261124 | llama.cpp | 4 | warm | 11-24 | 20/20 | 0.51 | |
| llamacpp-c4-warm3-20261124 | llama.cpp | 4 | warm | 11-24 | 20/20 | 0.57 | |
| ollama-c1-cold1-20261124 | Ollama | 1 | cold | 11-24 | 1/1 | 0.44 | model loaded on first request (18.2 s TTFT); memory sampled before load |
| ollama-c1-warm1-20261125 | Ollama | 1 | warm | 11-25 | 20/20 | 0.21 | |
| ollama-c1-warm2-20261125 | Ollama | 1 | warm | 11-25 | 20/20 | 0.56 | |
| ollama-c1-warm3-20261125 | Ollama | 1 | warm | 11-25 | 20/20 | 0.52 | |
| ollama-c2-warm1-20261125 | Ollama | 2 | warm | 11-25 | 20/20 | 0.97 | borderline |
| ollama-c2-warm2-20261125 | Ollama | 2 | warm | 11-25 | 20/20 | 0.64 | |
| ollama-c2-warm3-20261125 | Ollama | 2 | warm | 11-25 | 20/20 | 0.76 | |
| ollama-c4-warm1-20261125 | Ollama | 4 | warm | 11-25 | 20/20 | 0.45 | |
| ollama-c4-warm2-20261125 | Ollama | 4 | warm | 11-25 | 20/20 | 0.83 | no CPU sample (Prometheus gap) |
| ollama-c4-warm3-20261125 | Ollama | 4 | warm | 11-25 | 20/20 | 0.39 | no CPU sample (Prometheus gap) |

## 0.5B runs (Qwen2.5-0.5B-Instruct Q4_K_M, 2026-11-25, all completed, no failed runs)

Run IDs are `<tool>-05b-c<users>-<phase><n>-20261125`; the folder suffix is the full ID.

| Run | Tool | Users | Phase | OK | Quiet load | Notes |
|---|---|---|---|---|---|---|
| llamacpp-05b-c1-cold1-20261125 | llama.cpp | 1 | cold | 1/1 | 0.25 | server ready only a few minutes; model is loaded at start-up; no CPU sample |
| llamacpp-05b-c1-warm1-20261125 | llama.cpp | 1 | warm | 20/20 | 0.25 |  |
| llamacpp-05b-c1-warm2-20261125 | llama.cpp | 1 | warm | 20/20 | 0.42 |  |
| llamacpp-05b-c1-warm3-20261125 | llama.cpp | 1 | warm | 20/20 | 0.58 |  |
| llamacpp-05b-c4-warm1-20261125 | llama.cpp | 4 | warm | 20/20 | 0.48 |  |
| llamacpp-05b-c4-warm2-20261125 | llama.cpp | 4 | warm | 20/20 | 0.85 | borderline |
| llamacpp-05b-c4-warm3-20261125 | llama.cpp | 4 | warm | 20/20 | 0.85 | borderline |
| ollama-05b-c1-cold1-20261125 | Ollama | 1 | cold | 1/1 | 0.60 | model load on first request (2.1 s); memory sampled after the model download, discard |
| ollama-05b-c1-warm1-20261125 | Ollama | 1 | warm | 20/20 | 0.26 |  |
| ollama-05b-c1-warm2-20261125 | Ollama | 1 | warm | 20/20 | 0.95 | borderline |
| ollama-05b-c1-warm3-20261125 | Ollama | 1 | warm | 20/20 | 0.70 |  |
| ollama-05b-c4-warm1-20261125 | Ollama | 4 | warm | 20/20 | 0.96 | borderline |
| ollama-05b-c4-warm2-20261125 | Ollama | 4 | warm | 20/20 | 0.50 |  |
| ollama-05b-c4-warm3-20261125 | Ollama | 4 | warm | 20/20 | 0.21 |  |

Notes for the 0.5B runs: CPU was recorded for only three runs (ollama-05b-c1-warm3, ollama-05b-c4-warm1, llamacpp-05b-c1-warm1); Ollama ran 09:37 to 10:01 UTC and llama.cpp 13:58 to 14:20 UTC. The Ollama 0.5B model `qwen2.5-0.5b-bench` was built from `qwen2.5:0.5b` with `bench/Modelfile.qwen2.5-0.5b-bench`; llama.cpp used `qwen2.5-0.5b-instruct-q4_k_m.gguf` downloaded from the Qwen GGUF repository.

## Notes

- Servers were swapped through Git (llm-cpu replicas 1 to 0, ollama-cpu 0 to 1) because Argo CD reverts manual scaling. The platform's diagnostic feature (needs llm-cpu) was down while Ollama was running.
- The `ghcr-pull` pull secret uses a read:packages token owned by Faraaz-Parker because the GHCR packages are private. It should be replaced or revoked after the competition.
- Borderline quiet readings right after a run are the previous run's own decaying load.
