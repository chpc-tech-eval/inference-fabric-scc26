# Week 5 hardware record (CPU benchmarks)

Measured 2026-11-08 19:15 UTC by gavin. Raw output: `hardware-workers.txt`. Clocks: `clock-sync.txt`.

| Item | k8s-worker-01 and k8s-worker-02 (identical) |
| --- | --- |
| Cloud | CHPC Sebowa (OpenStack), flavor `C8.medium` |
| vCPUs / RAM / disk | 8 vCPU, 16 GB RAM, 100 GB disk |
| CPU model | Intel Xeon (Cascade Lake), virtual |
| CPU features | AVX2, AVX-512 (avx512f), AVX-512 VNNI; no AMX |
| Topology | 8 sockets x 1 core, 1 thread per core (no SMT), 1 NUMA node |
| OS / kernel | Rocky Linux 9.5, kernel 5.14.0-503.14.1.el9_5 |

**Explanation**

- These are **virtual CPUs on shared cloud hardware**, so the speed can vary. Every warm run is repeated 3 times.
- **AVX-512 VNNI** speeds up the integer maths that 4-bit models use.
- Each inference server gets **6 of the 8 vCPUs**, leaving 2 for Kubernetes and monitoring.
- The L3 cache size inside the VM is what the hypervisor presents, so it is not used in any analysis.
- All five machines' clocks were within 0.1 ms of NTP before the runs.
