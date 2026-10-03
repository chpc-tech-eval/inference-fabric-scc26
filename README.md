# Open LLM Inference Fabric — Ollama, llama.cpp & vLLM on CPU/GPU

Welcome to the CHPC SCC26 student engineering programme. The first four weeks are a common platform build shared by all five teams; Week 5 applies that platform to **Inference Fabric**, Week 6 produces the technical paper/poster and reproducibility evidence, and Week 7 consolidates the work.

> [!IMPORTANT]
> You are not expected to know every technology on day one. Build one layer, validate it, understand what owns it, then continue. The goal is competence and reproducibility—not surviving a giant command dump.

## Project question

> Given a model, hardware class and service objective, what measurable evidence should determine the choice of inference runtime and resource placement?

## Start here

1. [Week 1 — OpenStack → Terraform → Ansible](week1/README.md)
2. [Week 2 — Kubernetes substrate & GitOps](week2/README.md)
3. [Week 3 — Observability, security & Student Project Platform](week3/README.md)
4. [Week 4 — Agent Control Plane & Hermes](week4/README.md)
5. **Week 5 — project-specific MVP**
6. **Week 6 — IEEE-style short paper, poster and reproducibility rebuild**
7. **Week 7 — consolidation and handover**

Read [CONTRIBUTING.md](CONTRIBUTING.md) before making repository changes and [docs/COMMAND-LOCATIONS.md](docs/COMMAND-LOCATIONS.md) before running infrastructure/Kubernetes commands.

## Programme cadence

- Core project: six weeks, followed by Week 7 consolidation.
- Tentative collaborative working session: **Friday 14:00–18:00**.
- Sebowa, A100 and H200 access are separate resource domains and may have different credentials/authorisation.
- Current expected access horizon: **15 December 2026**, subject to instructor/provider updates.
- Discord is the live collaboration space; GitHub is the engineering system of record.

## Common five-node POC

| Role | vCPU | RAM | Storage | Purpose |
| --- | ---: | ---: | ---: | --- |
| `edge-01` | 4 | 10 GiB | 50 GiB | WireGuard, Pi-hole/DNS, nftables, Wazuh Manager, Suricata |
| `api-lb-01` | 2 | 4 GiB | 25 GiB | HAProxy and stable Kubernetes API endpoint |
| `k8s-cp-01` | 4 | 8 GiB | 30 GiB | Kubernetes control plane and cluster administration point |
| `k8s-worker-01` | 8 | 16 GiB | 40 GiB | platform/workbench/project workloads |
| `k8s-worker-02` | 8 | 16 GiB | 40 GiB | platform/workbench/project workloads |
| **POC total** | **26** | **54 GiB** | **185 GiB** | excludes separate A100/H200 resources |

Your team owns the final architecture. If you depart from this baseline, document the reason and the evidence supporting the change.

## The operating model

```text
                    STUDENT WORKSTATION
          Git · OpenStack CLI · Terraform · Ansible · kubeseal
                              │
                     provision/configure
                              ▼
                    SEBOWA OPENSTACK
        edge-01 · api-lb-01 · k8s-cp-01 · workers
                              │
                              ▼
                       KUBERNETES
         Cilium · Cinder · Argo CD · Traefik · monitoring
                   │                    │
                   │                    └── Student Project Platform
                   │                               │
                   └───────────────────────────────┤
                                                   ▼
                                          Agent Control Plane
                                                   │
                                                Hermes
                                                   │
                                      approved remote inference
                                           ┌───────┴───────┐
                                           ▼               ▼
                                         A100             H200
```

**Kubernetes administration happens from `k8s-cp-01`, not from your personal workstation.** Permanent Kubernetes application changes live in Git and are reconciled by Argo CD.

## One team repository

You need only this repository for the student project. It contains student-sized infrastructure, Student Project Platform source/configuration, GitOps desired state, project-specific work, evidence, paper and poster material. See [docs/REPOSITORY-MODEL.md](docs/REPOSITORY-MODEL.md).

You are **not required to clone** the production `quantum-platform` repository. You are also not required to clone ACP just to operate it; use pinned instructor-approved images and configuration first.

## Weeks 1–4: common platform qualification

| Week | Goal | Exit gate |
| --- | --- | --- |
| 1 | OpenStack → Terraform → Ansible | five-node POC reproducibly provisioned and host bootstrap validated |
| 2 | Kubernetes + GitOps | 1 CP + 2 workers, Cilium, Cinder, Argo, Sealed Secrets, Traefik/TLS |
| 3 | observability/security + Student Project Platform | live metrics, fresh Wazuh/Suricata evidence and authenticated browser platform with persistent DB |
| 4 | ACP + Hermes | Student Platform → ACP → evidence → Hermes → approved remote model → persistent history |

## Week 5 — Inference Fabric

Establish CPU Ollama/llama.cpp baselines, then exercise approved A100/H200 endpoints with Ollama, llama.cpp and vLLM where compatible. Collect latency, throughput and resource telemetry under a controlled workload and expose the resulting endpoint catalogue to ACP.

Minimum project evidence:

- A common model/workload compared fairly across compatible runtimes.
- CPU baseline plus at least one A100 or H200 GPU baseline.
- Machine-readable measurements for TTFT/latency/throughput and errors.
- CPU/RAM/GPU/VRAM telemetry correlated to benchmark windows.
- A runtime/model/execution-class catalogue and workload-specific conclusions—not a universal winner.

## Week 6 — publication + reproducibility

Week 6 is not “show the cluster that has survived since Week 2”. You must demonstrate that the system can be reconstructed from its declared sources and protected inputs.

Deliverables:

- a **3–5 page, two-column IEEE-style technical paper** using the scaffold under [`paper/`](paper/README.md);
- a high-quality technical poster using [`poster/`](poster/README.md);
- a short live demonstration;
- a tear-down/rebuild or instructor-approved equivalent reproducibility exercise;
- exact Git SHAs, image digests, configuration/experiment identifiers and acceptance evidence;
- an honest limitations/failure section.

## Week 7 — consolidation

Use Week 7 to fix documentation revealed by the rebuild, close/triage issues, remove stale resources and secrets, prepare clean upstream contributions where appropriate, and merge the reviewed `dev` release state into protected `main`.

## Four student roles

| Primary role | Ownership |
| --- | --- |
| **Infrastructure deployment** | OpenStack, Terraform, networking, security groups, DNS/firewall design |
| **Cloud automation** | Ansible, Kubernetes bootstrap, Cilium, Cinder |
| **CI/CD, telemetry & security** | GitHub Actions, Argo CD, Prometheus/Grafana, Wazuh, Suricata |
| **Frontend, agents & project specialisation** | Student Project Platform, ACP/Hermes integration and Week-5 work |

These are starting responsibilities, not silos. Rotate ownership after major milestones and make sure every team member can explain the full architecture.

## Engineering rules

1. **No plaintext secrets in Git.**
2. **No `kubectl` or Argo administration from personal workstations.** Use `k8s-cp-01`.
3. **No permanent `kubectl edit` fixes.** Diagnose imperatively; repair desired state in Git.
4. **No direct student pushes to protected `main` or `dev`.** Use short-lived branches and PRs.
5. **Do not treat Argo `Synced`, a green pod, or a successful Terraform command as end-to-end proof.** Validate the user/service outcome.
6. **Record evidence as you work.** Do not try to reconstruct six weeks of provenance on submission day.
7. **GPU access is separate from Sebowa.** Never assume Kubernetes has direct ownership of A100/H200 hardware unless the instructor explicitly configures it that way.

## Reference repositories

These are reference/upstream implementations, not mandatory student checkouts:

- `nyameko/infra-hpc-qc-k8s` — instructor/reference infrastructure architecture and deeper tutorials;
- `nyameko/quantum-platform` — production portal architecture **for reference only**; students use Student Project Platform;
- `nyameko/agent-control-plane` — upstream ACP/Hermes source and immutable images;
- `chpc-tech-eval/scc` — teaching/tutorial style and HPC learning lineage.

When the instructor announces a tested version/image, record it. Avoid silently mixing different weekly baselines across team members.

## What success looks like

A successful team can explain and reproduce this chain:

```text
Git / Terraform / Ansible
          ↓
OpenStack infrastructure
          ↓
Kubernetes + Cilium + Cinder
          ↓
GitHub + Argo CD
          ↓
observability + security evidence
          ↓
Student Project Platform
          ↓
Agent Control Plane + Hermes
          ↓
project-specific result
          ↓
paper/poster with traceable evidence
```

Keep calm, ask good questions, validate one layer at a time, and leave the repository better than you found it.
