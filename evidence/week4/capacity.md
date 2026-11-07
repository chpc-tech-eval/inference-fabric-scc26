# Week 4 capacity (before llm-cpu)

Measured 2026-11-07 11:09 UTC by gavin. Raw output: `capacity.txt`.

| Worker | Allocatable CPU / RAM | Already requested | Free for scheduling | Real RAM available | Root disk free |
| --- | --- | --- | --- | --- | --- |
| k8s-worker-01 | 8 / 15.3 GiB | 0.15 CPU / 0.1 GiB | 7.85 CPU / 15.1 GiB | 11 GiB | 85 GB |
| k8s-worker-02 | 8 / 15.3 GiB | 0.97 CPU / 2.6 GiB | 7.0 CPU / 12.6 GiB | 12 GiB | 84 GB |

**llm-cpu** (requests 6 CPU / 4 GiB, limit 6 GiB) fits on either worker.

**Recommendation:** pin llm-cpu to `k8s-worker-01`. Worker-02 already has 4.2 CPU of limits;
adding 6 more allows 10.2 cores of demand on 8, which would make Week 5 timings noisy.
