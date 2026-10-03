# Week 6 — Reproducibility Rebuild, IEEE Paper & Poster

Week 6 is the proof that your environment is **reproducible rather than merely long-lived**. It is also when the evidence collected since Week 1 becomes your 3–5 page IEEE-style paper and technical poster.

## Freeze the candidate baseline

Create a release-candidate branch from the accepted `dev` state only if the instructor asks; otherwise record the exact `dev` commit:

```bash
# RUN ON: WORKSTATION
git switch dev
git pull --ff-only
git rev-parse HEAD
git status --porcelain
```

The working tree should be clean for the reproducibility trial.

Record immutable images and Week-5 run IDs before teardown.

## Back up recovery material before destroying anything

The rebuild must not become a secret-loss exercise. Follow instructor policy for:

- Terraform state/backend;
- OpenStack application credentials;
- SSH/WireGuard private keys;
- Sealed Secrets recovery keys **or** the plaintext-secret recovery source used for re-sealing;
- Student Platform/ACP data that the assessment requires preserving;
- paper/poster figures and result artifacts.

Never put these private backups in Git.

### Sealed Secrets choice

A fresh cluster creates a new sealing key. Choose one documented instructor-approved recovery path:

1. **DR restoration:** securely back up/restore the controller sealing key so existing SealedSecrets continue to decrypt; or
2. **Fresh re-seal:** let the new cluster create a new key, obtain the new public certificate, and re-seal secrets from protected private source material.

Explain which path you used.

## Rebuild order

Use your own Week-1/2 documentation, not memory:

```text
1. terraform plan/destroy (review carefully)
2. prove resources removed as intended
3. terraform apply from clean desired state
4. Ansible base bootstrap
5. edge private-access path
6. HAProxy
7. Kubernetes prerequisites
8. kubeadm + workers
9. Cilium
10. Argo + Sealed Secrets
11. Cinder persistence path
12. monitoring/security services
13. Student Project Platform
14. ACP/Hermes
15. project-specific Week-5 workload
```

Time major stages and record every undocumented manual intervention. Each manual surprise is a documentation/automation defect to fix in Week 7.

## Minimum conformance test after rebuild

```text
OpenStack topology matches documented design
WireGuard/private admin path works
Kubernetes API + nodes + Cilium healthy
Cinder can provision a fresh PVC
Argo reconciles team repo/dev
Prometheus has live targets
Wazuh/Suricata path passes a benign smoke test
Student Platform login and DB persistence work
ACP diagnostic reaches approved model and persists history
Week-5 project MVP produces at least one accepted run
```

## Paper workflow

Use `paper/main.tex` and `paper/README.md`.

Do not invent numbers. Populate Results only from accepted run manifests/logs/telemetry.

Recommended writing order:

1. freeze research/project question;
2. choose the 2–4 figures/tables that actually answer it;
3. write Methodology from the reproducible runbook;
4. write Results from measured evidence;
5. write Discussion/Limitations honestly;
6. write Introduction after the contribution is clear;
7. write Abstract last.

The 3–5 page limit rewards precision.

## Poster workflow

Use `poster/README.md`. The poster should be understandable in roughly 60–90 seconds:

```text
problem/question
→ architecture/method
→ strongest result figure
→ interpretation
→ reproducibility/limitations
```

Avoid paragraphs copied from the paper. Prefer diagrams, short captions, large legible plots and a reproducibility footer with Git SHA/image/run IDs.

## Exit gate

- rebuild completed from documented sources/private inputs;
- manual interventions documented and converted to issues/fixes;
- one final accepted project run produced after rebuild;
- paper compiles and contains no invented placeholders in Results;
- poster has final architecture + actual result visuals;
- demo script fits the allotted time.
