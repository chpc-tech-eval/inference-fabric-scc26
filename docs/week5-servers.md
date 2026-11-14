# Week 5 server settings

| Setting | llama.cpp (`llm-cpu`) | Ollama (`ollama-cpu`) |
|---|---|---|
| Node | k8s-worker-01 | k8s-worker-01 |
| CPU / memory | 6 / 6Gi (requests = limits) | 6 / 6Gi (requests = limits) |
| Threads | `--threads 6` | `num_thread 6` (via derived model `qwen2.5-1.5b-bench`, ID `66c5fa2ffb97`) |
| Parallel requests | `--parallel 4` | `OLLAMA_NUM_PARALLEL=4` |
| Context | `--ctx-size 16384` (4 slots x 4096) | `num_ctx 4096` per slot (`OLLAMA_CONTEXT_LENGTH=4096`) |
| Model | `qwen2.5-1.5b-instruct-q4_k_m.gguf` | `qwen2.5:1.5b` (1.5B, Q4_K_M) |
| Model fingerprint | sha256 `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e` | ID `65ec06548149` |
| Image | `ghcr.io/ggml-org/llama.cpp@sha256:e3032ea0712da96dec820c770626385de4322dd06619fb5829256a504bbc9375` | `ollama/ollama:0.40.16@sha256:910d0d8107b538fb0894e63163eb195de0cc7aefcbc666dc62d3b18f71124592` |
| Keep-alive | n/a (model always loaded) | `OLLAMA_KEEP_ALIVE=-1` |
| Harness URL | `http://llm-cpu.inference.svc.cluster.local:8080/v1` | `http://ollama-cpu.inference.svc.cluster.local:11434/v1` |
| Harness model name | `qwen2.5-1.5b-instruct` | `qwen2.5-1.5b-bench` |
| Auth | API key (SealedSecret) | none, protected by network policy only |

## Differences that can't be avoided

- Ollama has no API key of its own, so only the network policy protects it (flag for security).
- The Ollama model was pulled with `kubectl exec ollama pull`, a one-off data download rather than a configuration change.
- Ollama's thread count is set through a derived model (Modelfile), not a flag, so the model name the harness uses differs.
- The two tools use different GGUF packaging: the model IDs are not comparable hashes, so both fingerprints are recorded to show each ran Qwen2.5-1.5B-Instruct Q4_K_M.
- Derived model created once after the pull, recipe in `docs/bench/Modelfile.qwen2.5-1.5b-bench`:
  `ollama create qwen2.5-1.5b-bench -f docs/bench/Modelfile.qwen2.5-1.5b-bench`
  (base model ID `65ec06548149` stays the fingerprint for the manifests).
