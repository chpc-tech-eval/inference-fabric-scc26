# Week 4 controlled failure test

Goal: show that when the model is unavailable, the agent fails honestly (an explicit failure, not "succeeded"), keeps the evidence it collected before the model call, and recovers once the model is back.

Method: the CPU model server `llm-cpu` was scaled to zero replicas **through Git** (not `kubectl`), one diagnostic was requested from the website, the change was reverted through Git, and a final diagnostic was requested. No database, PVC or disk was touched; the model disk is retained at zero replicas.

Setup: Hermes worker on the team image (`ghcr.io/chpc-tech-eval/inference-fabric-scc26/acp-hermes@sha256:187720bd32aa05c2400af94eaf80ecb388612d80c7003c80b84c415d6b5a9bd6`) with Hermes's context floor lowered to 4,096 (see `images.md`). The diagnostic reads the stand-in `quantum-platform` namespace (one `pause` pod), not the Student Platform.

## Timeline (UTC)

| Step | Time | Detail |
| --- | --- | --- |
| Baseline run | 2026-11-17 19:00:04 | Task `5ceee7e7-b2ba-4383-b9e8-270c8f468423`, total 15 s, succeeded |
| Model scaled to 0 | about 2026-11-18 20:36 (per Prometheus) | First `up{job="llm-cpu"}` = 0 sample at 20:36:00Z; the sample at 20:35Z read 1 (1-minute resolution). Scale-down PR: https://github.com/chpc-tech-eval/inference-fabric-scc26/pull/112 . `kubectl -n inference get deploy,pods` showed 0/0  |
| Failure run | 2026-11-18 21:03:18 | Task `c69c7af2-856e-424d-b253-3511f26ef680`, final status **Failed** |
| Model restored | by 2026-11-18 21:20:14 | The recovery run requested at 21:20:14Z succeeded, so the model was serving by then; first `up` = 1 sample at 21:21:00Z (scrape lag). Revert PR: https://github.com/chpc-tech-eval/inference-fabric-scc26/pull/113 . Rollout complete and pod 1/1 Running |
| Recovery run | 2026-11-18 21:20:14 | Task `05fc897d-95c0-4eba-b15f-c59686520cc9`, total 16 s, final status **SUCCEEDED** |

Independent confirmation from Prometheus: `up{job="llm-cpu"}` (the scrape of the model server, 1-minute samples) read 0 in every sample from at least 2026-11-18T20:50:00Z through 21:20:00Z and read 1 from 21:21:00Z. The failure run at 21:03:18Z falls inside that outage. The recovery run was requested at 21:20:14Z and succeeded, so the model was serving by then; the first `up=1` sample at 21:21:00Z lags because of the scrape interval. Transitions over 18:00-22:00Z: `up = 1` at 18:00:00Z, `up = 0` from 20:36:00Z, `up = 1` from 21:21:00Z. So the model was unreachable for about 45 minutes, and the failure run came about 27 minutes after the outage began.

## Results against the three outcomes

| Outcome required | Observed | Result |
| --- | --- | --- |
| The run ends in an explicit failure, not "succeeded" | Final status `Failed` for task `c69c7af2-856e-424d-b253-3511f26ef680`. The page headline reads "Explanation failed" and says "The model could not produce an explanation. The evidence below was collected before the model call." The page gives no more specific cause, and the worker log lines captured so far show only the Prometheus query, not the model error (see below) | Pass |
| The evidence collected before the model call is still visible | Yes. The failed task page shows the evidence first, above an explanation section reading "No explanation available": tool `quantum-platform-pod-readiness`, counts true 1 / false 0 / unknown 0, namespace `quantum-platform`, the stated limitation ("Ready counts only; does not measure app health or scrape freshness."), observed at 2026-11-18T21:03:18.9Z. The event history lists `diagnostic_completed` at 21:03:18 before `failed` at 21:03:46, and the worker log shows the Prometheus query returning 200 at the same moment | Pass |
| After reverting in Git, a new diagnostic succeeds | Task `05fc897d-...` ended `SUCCEEDED` in 16 s, similar to the baseline's 15 s | Pass |

How long the failure run took: 29 s in total. Event history: queued 21:03:18, started 21:03:18, diagnostic_completed 21:03:18, failed 21:03:46, so the run ended 28 s after the evidence was stored. That is well short of the 300 s run timeout, so the run did not hang; the specific error from the model call is not in the log lines captured so far, so the cause is recorded only as "the model could not produce an explanation". The worker log is in local time (+02:00): 23:03:18.9+02:00 is 21:03:18.9Z.

Worker log for the failure window: the Prometheus query for the diagnostic returned `HTTP/1.1 200 OK` at 2026-11-18T23:03:18.9+02:00 (21:03:18.9Z), matching the evidence's `observed_at`.
The agent log files note the reason for the error: /var/lib/hermes/admin-readonly/logs 2>/dev/null | head -15'
/var/lib/hermes/admin-readonly/logs/errors.log:819:2026-11-18 21:03:23,383 ERROR agent.chat_completion_helpers: Streaming failed before delivery: Connection error.

Screenshots:`grafana-dashboard-llm_cpu_model_down_gap.png` `grafana-dashboard-llm_cpu_model_down_gap_2.png` `platform_diagnostic_erro_test.png` `platform_diagnostic_failure_test_revert.png` `platform_diagnostic_baseline_test.png` 

## Notes

- Evidence here comes from the stand-in diagnostic target, so "the evidence" is the count of Ready pods in a namespace holding one `pause` pod, not a health measurement of the Student Platform.
- The explanation on the recovery run came from the in-cluster CPU model (`qwen2.5-1.5b-instruct`, Q4_K_M).
- Change history is in Git: the scale-down and revert are separate reviewed PRs.
