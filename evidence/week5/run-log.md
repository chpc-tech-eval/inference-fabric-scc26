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

## Notes

- Servers were swapped through Git (llm-cpu replicas 1 to 0, ollama-cpu 0 to 1) because Argo CD reverts manual scaling. The platform's diagnostic feature (needs llm-cpu) was down while Ollama was running.
- The `ghcr-pull` pull secret uses a read:packages token owned by Faraaz-Parker because the GHCR packages are private. It should be replaced or revoked after the competition.
- Borderline quiet readings right after a run are the previous run's own decaying load.
