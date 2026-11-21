# Benchmark harness

Sends a fixed prompt set to an OpenAI-style server (llama.cpp, Ollama, vLLM) with streaming on and records
time to first token, total time and tokens per second for every request. Standard library only.

## Settings (environment variables)

| Variable | Meaning | Default |
| --- | --- | --- |
| `TARGET_URL` | base URL including `/v1` | **required** |
| `MODEL` | model name the server expects | **required** |
| `RUN_ID` | unique run name (letters, digits, `.`, `_`, `-`) | **required** |
| `CONCURRENCY` | requests in flight at once | `1` |
| `PHASE` | `cold` or `warm`, written into every row | `warm` |
| `API_KEY` | bearer key (llama.cpp needs one, Ollama has none). Never printed or saved | none |
| `MAX_PROMPTS` | use only the first N prompts (a cold run is `MAX_PROMPTS=1`, `CONCURRENCY=1`) | `0` (all) |
| `MAX_TOKENS` / `TEMPERATURE` | fixed for every tool | `256` / `0` |
| `REQUEST_TIMEOUT` | seconds per request | `300` |
| `PROMPTS_FILE` | JSON Lines prompt file | `prompts.jsonl` next to the script (`/app/prompts.jsonl` in the image) |
| `RESULTS_DIR` | where results go: `RESULTS_DIR/RUN_ID/` | `/results` |
| `CACHE_BUST` | `1` puts a short tag (`[ref 1a2b3c4d] `, different for every run and every prompt) in front of each prompt, so the server cannot skip the prefill of a prompt it processed in an earlier run. `0` sends the prompt exactly as written | `1` |
| `PARALLEL` / `CTX` | the server's slot count and context size. Only written into `summary.json`, so each result says which server setup it came from | not recorded |
| `DRY_RUN=1` | check the prompt file only: no network, no files | off |

## Outputs

`results.csv` (one row per request) and `summary.json` (median and 95th percentile of each measure, counts by status,
the prompt file's sha256, the settings used with `api_key_used` true/false, never the key).

- `ttft_s`: sending until the first streamed answer text.
- `total_s`: sending until the last piece.
- `tokens_per_s` = output tokens / (`total_s` - `ttft_s`), as in the Week 5 guide.
- Output tokens come from the server's usage figures (`tokens_source=usage`); if the server sends none, streamed
  pieces are counted (`tokens_source=chunks`, an approximation). Check this column before comparing tools.
- Percentiles use the nearest-rank method.
- One failed request never stops the run: it is recorded (`status`, `error`) and the run carries on.

Exit codes: `0` finished with at least one good request, `1` finished but every request failed, `2` bad settings.

## For the Job template (Cloud automation)

- The image runs as user/group `10001`. The results volume must be writable by that user, for example
  `securityContext: { runAsUser: 10001, runAsGroup: 10001, fsGroup: 10001 }`.
- Use the model names and addresses from `docs/week5-servers.md`. They may differ from the guide's examples
  (for example Ollama's derived model `qwen2.5-1.5b-bench`).
- Pass the llama.cpp key from the sealed secret as `API_KEY` (`secretKeyRef`). Ollama needs no `API_KEY`.
- Give every run a new `RUN_ID`, for example `<tool>-c<concurrency>-<cold|warm><n>-<YYYYMMDD>`.

## For CI (CI/CD & security)

```bash
python -m pyflakes bench/harness.py
python -m unittest bench/test_harness.py                       # fake server, about 15 s, no network
DRY_RUN=1 PROMPTS_FILE=bench/prompts.jsonl python bench/harness.py
```

`bench/prompts.jsonl` is fixed: 7 short, 7 medium, 6 long. Never edit it after the first run; make `prompts.v2.jsonl` instead.

Repeated runs against the same server: llama.cpp keeps processed prompts and skips their prefill when the same text
comes again (a second warm run showed first-token times near 0.06 s instead of 1.4 to 3.3 s for every medium and long
prompt). `CACHE_BUST=1` (the default) prevents this by tagging each request, which adds about 5 to 8 prompt tokens.
The tag is recorded as `cache_bust` in `summary.json`; compare only runs with the same setting.

Every prompt must be different from the start: llama.cpp keeps the processed start of earlier prompts and skips that work
when it sees the same text again, which makes a repeated prompt look about 40 times faster to first token (seen once in a
check run, before the prompt set was fixed). `test_prompts_are_unique_…` guards this.
