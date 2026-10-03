Open LLM Inference Fabric — Ollama, llama.cpp & vLLM on CPU/GPU
===============================================================

Welcome. This repository is one of the CHPC student engineering projects for the 2026 SCC follow-on programme. You will spend the first four weeks building the same small cloud-native research platform as the other teams, then use that platform for your team's project-specific experiment.

The project is intentionally ambitious, but the path is deliberately staged. **Do not try to understand every technology before you begin.** Build one layer, validate it, understand what it owns, then continue.

> [!IMPORTANT]
> The objective is not to copy commands until something turns green. By the end, every team member should be able to explain the full platform at a useful high level, even though each person has a primary role.

# Project question

> Given a model, runtime, hardware class and service objective, what measured evidence should the platform use to choose an inference route?

# Start here

Work through the common platform weeks in order:

1. [Week 1 — OpenStack → Terraform → Ansible](week1/README.md)
2. [Week 2 — Kubernetes Substrate & GitOps](week2/README.md)
3. [Week 3 — Observability, Security & Quantum Platform](week3/README.md)
4. [Week 4 — Agent Control Plane & Hermes](week4/README.md)
5. **Week 5 — project-specific implementation**
6. **Week 6 — technical journal article, poster and reproducibility rebuild**
7. **Week 7 — consolidation, cleanup and upstream handover**

The upstream implementation/reference repositories are:

- [`nyameko/infra-hpc-qc-k8s`](https://github.com/nyameko/infra-hpc-qc-k8s) — OpenStack/Terraform, Ansible, Kubernetes, GitOps, storage, observability and security deployment;
- [`nyameko/quantum-platform`](https://github.com/nyameko/quantum-platform) — Astro/Django/PostgreSQL user-facing platform;
- [`nyameko/agent-control-plane`](https://github.com/nyameko/agent-control-plane) — bounded agent task API, persistent history and Hermes worker;
- [`chpc-tech-eval/scc`](https://github.com/chpc-tech-eval/scc) — teaching/tutorial style and HPC learning lineage.

These repositories are active. Record the exact commit SHA you use each week. When a tested baseline is announced, keep the whole team on that baseline until instructed otherwise.

# Programme cadence

The current plan is a **six-week core project** followed by **Week 7 consolidation**. Team captains should coordinate the Friday working session, tentatively **14:00–18:00**, through the programme Discord. The current expected infrastructure access window runs through **15 December 2026**; watch GitHub/Discord for any operational changes.

Discord: https://discord.gg/PNMknPydJ

# What you will build

The common platform is approximately:

| Role | vCPU | RAM | Storage | Purpose |
| --- | ---: | ---: | ---: | --- |
| `edge-01` | 4 | 10 GiB | 50 GiB | WireGuard, Pi-hole/DNS, nftables, Wazuh Manager, Suricata |
| `api-lb-01` | 2 | 4 GiB | 25 GiB | HAProxy and stable Kubernetes API endpoint |
| `k8s-cp-01` | 4 | 8 GiB | 30 GiB | Kubernetes control plane |
| `k8s-worker-01` | 8 | 16 GiB | 40 GiB | platform/workbench/project workloads |
| `k8s-worker-02` | 8 | 16 GiB | 40 GiB | platform/workbench/project workloads |
| **POC total** | **26** | **54 GiB** | **185 GiB** | excluding separately allocated GPU systems |

Your team may adjust the final design within the project quota, but every change needs a technical reason.

## Common architecture

```text
                              Your workstation
                                    │
                                    │ WireGuard / SSH
                                    ▼
                              ┌───────────┐
                              │  edge-01  │
                              │ VPN / DNS │
                              │ security  │
                              └─────┬─────┘
                                    │
                  ┌─────────────────┴──────────────────┐
                  │                                    │
                  ▼                                    ▼
            ┌───────────┐                       ┌─────────────┐
            │ api-lb-01 │                       │ Kubernetes  │
            │  HAProxy  │                       │   cluster   │
            └─────┬─────┘                       └──────┬──────┘
                  │                                    │
                  │ :6443                       ┌──────┴──────┐
                  └────────────────────────────►│ k8s-cp-01  │
                                               └──────┬──────┘
                                                      │
                                             ┌────────┴────────┐
                                             ▼                 ▼
                                      ┌─────────────┐   ┌─────────────┐
                                      │k8s-worker-01│   │k8s-worker-02│
                                      └─────────────┘   └─────────────┘
```


A100 and H200 access is **separate** from the Sebowa OpenStack project. The normal design is for small services/agents in Kubernetes to call approved model endpoints remotely.

# Why the first four weeks are shared

All four projects depend on the same engineering foundations. The common build teaches the control boundaries once:

```text
Terraform       → OpenStack infrastructure
Ansible         → Linux host configuration/bootstrap
kubeadm         → Kubernetes bootstrap
Cilium          → Kubernetes networking/policy
Cinder CSI      → Kubernetes persistent block storage
Argo CD         → long-lived Kubernetes application state
Sealed Secrets  → encrypted secret material in GitOps
Traefik         → application ingress
Prometheus      → metrics collection
Grafana         → metrics visualisation
Wazuh           → host/security event evidence
Suricata        → network IDS evidence
Quantum Platform→ user identity/product surface
Agent Control Plane → bounded agent tasks/history/policy
Hermes          → agent runtime/harness
A100/H200 model server → inference
```

If you do not know a term yet, that is expected. The weekly tutorials introduce it when you need it.

# Six-week core + Week 7 consolidation

| Week | Common goal | Exit condition |
| --- | --- | --- |
| 1 | OpenStack → Terraform → Ansible | five-node POC reproducibly deployed and bootstrapped |
| 2 | Kubernetes substrate + GitOps | 1 CP + 2 workers, Cilium, Cinder, Argo, Sealed Secrets, Traefik/TLS |
| 3 | Observability/security + Quantum Platform | Prometheus/Grafana, Wazuh/Suricata evidence and working browser login |
| 4 | ACP + Hermes | portal → ACP → evidence → Hermes → remote model round trip |
| 5 | Project specialisation | project-specific MVP demonstrated on the common platform |
| 6 | Report + reproducibility | 2-page technical journal article, poster and tear-down/rebuild evidence |
| 7 | Consolidation | cleanup, final fixes, documented handover and upstream-ready contributions |

### Week 5 — Inference Fabric experiments

Your common platform becomes the client, telemetry and orchestration environment for a controlled inference study. You will compare **Ollama**, **llama.cpp** and **vLLM** across CPU and the separately allocated A100/H200 resources where compatible.

Keep the scientific comparison fair: use the same logical model or the closest compatible representation, the same prompt corpus, comparable generation settings and clearly recorded hardware allocations.

Required Week 5 outcomes:

- CPU baseline for Ollama and/or llama.cpp;
- at least one A100 or H200 GPU baseline;
- vLLM deployment on a compatible NVIDIA resource;
- machine-readable measurement of latency, throughput and resource usage;
- Prometheus/Grafana visibility of the client/platform side and available inference telemetry;
- an ACP/Hermes configuration that can call at least one approved remote endpoint;
- a short evidence-based explanation of when each runtime is useful.

Do **not** try to crown a universal winner. Your result must be conditional on workload, model, hardware and service objective.


# Week 6 — report, poster and reproducibility

Your final Week 6 assessment is **not** "our environment has been alive for six weeks." You must demonstrate that the project is reproducible.

At minimum:

1. preserve the required state/results and record the exact source/image revisions;
2. tear down the disposable infrastructure using the documented method;
3. recreate the common platform from your Terraform/Ansible/GitOps sources and protected environment inputs;
4. rerun the core acceptance checks;
5. rerun the project-specific MVP or a representative reproducibility test;
6. record failures, manual exceptions and time-consuming steps honestly.

You will prepare:

- a **two-page technical journal-style article**;
- a **project poster**;
- a short live demonstration;
- reproducibility evidence.

The article/poster should answer: problem, architecture, method, evidence/results, limitations, lessons learned and future work.

# Week 7 — consolidation

Use the consolidation week to:

- fix documentation discovered to be incomplete during the rebuild;
- clean secrets/test credentials and stale resources;
- turn useful project changes into clear commits/PRs;
- identify improvements that belong upstream in `infra-hpc-qc-k8s`, `quantum-platform` or `agent-control-plane`;
- freeze final results and architecture diagrams;
- make the repository understandable to the next student who did not attend your meetings.

# Team roles

There are four students per team. Use the following primary ownership areas to parallelise the work:

| Role | Primary responsibility |
| --- | --- |
| **Infrastructure deployment** | OpenStack, Terraform, networking, security groups, DNS/firewall design |
| **Cloud automation** | Ansible, Kubernetes, Cilium, Cinder |
| **CI/CD, telemetry & security** | Argo CD, CI, Prometheus/Grafana, Wazuh, Suricata |
| **Frontend, agents & specialisation** | Astro/Quantum Platform, ACP, Hermes and project-specific implementation |

These are **not silos**. Rotate ownership after major milestones and review one another's work. Any team member may be asked to explain any part of the final architecture.

# Working method

Use the same pattern every week:

```text
READ
  ↓
DESIGN
  ↓
DEPLOY
  ↓
VERIFY
  ↓
BREAK / OBSERVE
  ↓
FIX
  ↓
DOCUMENT
  ↓
COMMIT
```

A command completing without an error is not proof that the system works. Prefer end-to-end acceptance evidence.

> [!TIP]
> **Show the working system, not slides about the working system.** Screenshots and diagrams are useful evidence, but they do not replace a live command, request, query or reproducible run.

# Git workflow

Keep changes small and reviewable. A simple student flow is:

```text
feature/<short-topic>
        ↓ Pull Request
      main
```

Use issues for tasks/bugs and pull requests for reviewed changes. Do not store secrets in issue comments, Discord, screenshots or Git history.

Before pushing:

```bash
git status
git diff --cached
```

Commit messages should say what changed and why.

# Secrets and safety

Never commit:

- OpenStack credentials/application-credential secrets;
- private SSH or WireGuard keys;
- kubeconfigs;
- plaintext Kubernetes Secrets;
- database passwords;
- model API keys;
- Discord bot tokens;
- TLS private keys.

Use the approved private-variable/Vault/Sealed Secret workflow described in the weekly guides.

A useful project layout after the common deployment is:

```text
inference-fabric-scc26/
├── README.md
├── week1/ ... week4/
├── deploy/
│   ├── ollama/
│   ├── llama-cpp/
│   └── vllm/
├── benchmarks/
├── results/
├── dashboards/
└── reports/
```

Benchmark results should record versions, model identity, hardware allocation and test parameters. Never commit API keys or provider credentials.


# Final project deliverable

A reproducible CPU/GPU inference comparison with pinned runtime/model information, measurable latency/throughput/resource evidence and an endpoint catalogue usable by Agent Control Plane experiments.

# Getting help

Use your project repository for technical issues and decisions, and the programme Discord for collaborative teaching/discussion. When asking for help, include:

```text
what you expected
what actually happened
the exact command/request
relevant error/log excerpt
which layer you already checked
source commit(s) in use
```

Redact credentials and private infrastructure values.

Most importantly: **Keep Calm and Carry On.** The purpose is to learn how the layers fit together, not to already know them on day one.
