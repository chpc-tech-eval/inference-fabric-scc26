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
