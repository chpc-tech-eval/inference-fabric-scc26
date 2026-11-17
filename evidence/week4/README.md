# Week 4 evidence: Agent Control Plane (CPU-first)

One small, fenced AI assistant: browser -> Student Platform -> ACP API -> ACP PostgreSQL -> Hermes worker -> CPU model (`llm-cpu`).

Result: a staff user requested the fixed pod-readiness diagnostic from the browser. It ran **queued -> started -> diagnostic_completed -> succeeded in 14 s**, the evidence matches Prometheus exactly, and a CPU-model explanation was shown. Earlier runs failed and are kept, because the page shows failures as failures.

## Index

| Evidence | File | Owner | Status |
| --- | --- | --- | --- |
| Run manifest (provenance of the end-to-end run) | `run-manifest.yaml` | Frontend | present |
| Image digests, schema version, model | `images.md`, `images-capture.txt` | CI/CD & security | present |
| Security checklist | `security-checklist.md`, `security-checklist-capture.txt` | CI/CD & security | present |
| Verification | `verification.txt` | CI/CD & security | present |
| Hermes team-image fix | `hermes-team-image.txt` | CI/CD & security | present |
| Controlled failure test | `failure-test.md` | CI/CD & security | **pending, not in the repo yet** |
| Restart and persistence test | `restart-persistence.md` | Cloud automation | **pending, not in the repo yet** |
| Clock sync on every node | `clock-sync.txt` | Infrastructure | present |
| Nothing-exposed checks | `exposure-checks.txt` | Infrastructure | present |
| Security observations during the run | `security-observations.md` | Infrastructure | **pending, not in the repo yet** |
| Capacity, CPU features, model download path | `capacity.md`, `capacity.txt`, `cpu-features.txt`, `download-path.txt` | Infrastructure | present |
| `llm-cpu` dashboard screenshots | `llm_cpu_dashboard_1.png`, `llm_cpu_dashboard_2.png` | CI/CD & security | present |
| Browser screenshots (below) | `screenshots/` | Frontend | present |

## End-to-end test (from the browser)

The staff page is `/admin/diagnostics`. Screenshots are in `screenshots/`.

| # | File | What it shows | Task |
| --- | --- | --- | --- |
| 1 | `01-login-staff.png` | logged in as a staff user | n/a |
| 2 | `02-request.png` | the request button | n/a |
| 3 | `03-queued-running.png` | **Queued**: waiting for the worker | `e16061f4…` (failure run) |
| 4 | `04-explaining.png` | **"Explaining…"** with the evidence already shown | `37b7991c…` (this run later failed, see Problems) |
| 5a | `05-no-metrics.png` | **"No metrics found"**, shown as a failure, never as healthy | `e16061f4…` |
| 5b | `05-explanation-failed.png` | failed after evidence was collected (`hermes_timeout`) | `37b7991c…` |
| 5c | `05-succeeded.png` | **Succeeded**: evidence, explanation, events, total time | `5ceee7e7…` |
| 6 | `06-nonstaff-blocked.png` | a non-staff user gets 403 | n/a |
| 7 | `07-after-logout.png` | access ends after logout | n/a |
| 8 | `08-acp-unreachable.png` | the page's clear message when the ACP cannot be reached (an honest failure, not a blank or healthy page) | n/a |
| 9 | `09-raw-response.png` | the ACP's raw response for the successful task | `5ceee7e7…` |

### The successful run

- Task `5ceee7e7-b2ba-4383-b9e8-270c8f468423`, 2026-11-17.
- Events: `queued` 19:00:04, `started` 19:00:04, `diagnostic_completed` 19:00:04, `succeeded` 19:00:18 (UTC).
- **Explanation time: 14 s** end to end on the CPU model (evidence collection took under 1 s). This is our first CPU inference timing; Week 5 measures it properly.
- Evidence (`quantum-platform`): `true: 1`, `false: 0`, `unknown: 0`.
- The explanation is an interpretation by Qwen2.5-1.5B and is not a measurement. It correctly restates the namespace, the observation time, the one ready pod and the stated limitation.

### Evidence checked against Prometheus

Prometheus queried at the evidence's own timestamp (`1794942004.946`) with `sum by (condition) (kube_pod_status_ready{namespace="quantum-platform"})` returned `true: 1`, `false: 0`, `unknown: 0`. This matches the ACP evidence exactly. A later query (about 7 minutes after) gave the same counts.

### Staff only, nothing secret in the browser

Non-staff users get 403 (`06`). The browser never sees the signing key or the token: the platform backend checks the user, signs a 60-second Ed25519 token, and calls the ACP.

## Problems we hit

Recorded as they happened, with the fix.

- **2026-11-07, ACP not there yet.** When first checked, the `agent-control-plane` namespace and its Argo app did not exist, and there was no `acp-signing` secret in `student-platform`. Cloud automation and CI/CD delivered these later.
- **2026-11-07, no CSRF protection.** The platform had `checkOrigin: false`, so form posts had no CSRF protection. We added a session-bound CSRF token to the diagnostic request.
- **2026-11-07, merge does not deploy.** The Deployment pins the image by `sha-<commit>`, so merging code does not deploy it. Each platform change needs a second PR that bumps the tag.
- **2026-11-07, unreadable signing key.** The platform runs as user 1000 but mounted secrets belong to root; mode `0400` would make the key unreadable. The pod uses `fsGroup: 1000` with mode `0440`.
- **2026-11-08, Service name mismatch.** The Cloud template called the API Service `agent-control-plane-api`, but it was deployed as `acp-api`. We pointed `ACP_BASE_URL` at `acp-api` (PR bundled with Task 4).
- **2026-11-09, 401 from the ACP (tenant mismatch).** We signed tokens with tenant `nyameko` (the ACP's code default) while the ACP was deployed with `student-platform`. Fixed by setting `ACP_TENANT_ID=student-platform` in `platform.yaml`.
- **2026-11-09, task stuck in Queued (worker tenant).** The Hermes StatefulSet had no `ACP_TENANT_ID`, so the worker defaulted to `nyameko`, and `claim()` only selects runs for its own tenant. Hermes logged nothing because it saw no work. Fixed by adding `ACP_TENANT_ID=student-platform` to `hermes.yaml`.
- **2026-11-09, "No metrics found".** The diagnostic hard-codes `namespace="quantum-platform"`, but the site runs in `student-platform`, so every run ended `diagnostic_no_data`. The page showed this as a failure, not as healthy. Fixed by a test pod (`diagnostic-target`) in `quantum-platform`.
- **2026-11-15/16, Hermes hung until timeout (`hermes_timeout`, 300 s).** At startup Hermes ran `pip install boto3` (Bedrock adapter, `lazy_deps.ensure`), but the `agent-control-plane` network policy blocks internet egress. We found it by running the Hermes step by hand with a stack dump, because the worker discards the subprocess's error output. Confirmed in the pod: `boto3` missing, `pypi.org` blocked. We first suspected an API key mismatch (three "Invalid API Key" lines in the model log), but the key hashes matched, so that was wrong. Setting `HERMES_DISABLE_LAZY_INSTALLS=1` on the pod did not help: the worker forwards only a fixed list of variables to the subprocess.
- **2026-11-16, Hermes 64K context minimum.** With the install bypassed, Hermes refused the model: "context window of 4,096 tokens, which is below the minimum 64,000". The CPU model gives 4,096 per request and Qwen2.5-1.5B tops out near 32K, so no server setting can meet it. GPUs were not available. **Fix (Gavin):** a team image built FROM the instructor's pinned digest plus a checked patch (`images/acp-hermes/patch_acp.py`) that turns lazy installs off and lets `ACP_HERMES_MIN_CONTEXT=4096` lower the floor for this tool-less admin run. This is a deliberate deviation from the instructor's image: the model's real context is not faked, and the refuse-if-any-tool check stays.
- **2026-11-17, "Succeeded" with no explanation shown.** Our page guessed the ACP's field names. The ACP returns the model's text in `summary`, events as `kind` and `occurred_at`, and failures as `failure_code`. Fixed in PR #109 and deployed in PR #110 (image `sha-9e2a80e`). The stored task was re-opened to show the explanation.

## Pull request description

See `pr-description.md` (paste it into the Week 4 PR).
