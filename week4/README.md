Week 4: Agent Control Plane & Hermes
=====================================

By now you have cloud infrastructure, Kubernetes, persistent storage, GitOps, monitoring/security telemetry and a user-facing platform. This week connects those pieces through a deliberately **small and bounded agent workflow**.

Do not try to build an autonomous administrator.

The shortest useful path is the existing Agent Control Plane Phase-1 vertical slice:

```text
Quantum Platform private/admin surface
             ↓
short-lived signed identity
             ↓
Agent Control Plane API
             ↓
PostgreSQL task/run/event history
             ↓
fixed Prometheus diagnostic
             ↓
persistent Hermes worker
             ↓
remote OpenAI-compatible model endpoint
             ↓
explanation + stored evidence
```

The Hermes worker uses CPU on your Kubernetes cluster. **Inference runs on separately provided A100/H200 resources** through an approved remote endpoint; do not assume that your Sebowa Kubernetes workers have GPUs.

# Checklist

- [ ] Explain the difference between an agent runtime, model server, control plane and Kubernetes scheduler.
- [ ] Clone and read the current `agent-control-plane` Phase 1 documentation.
- [ ] Run the ACP source tests appropriate to the current baseline.
- [ ] Understand the one allowed diagnostic and why it is deliberately fixed.
- [ ] Deploy dedicated ACP PostgreSQL state.
- [ ] Create/seal ACP database, signing/verifying and model credentials correctly.
- [ ] Configure an instructor-provided OpenAI-compatible A100/H200 model endpoint.
- [ ] Deploy the ACP API and singleton Hermes worker through Argo CD.
- [ ] Verify `/health` and `/ready` semantics.
- [ ] Enable the compatible Quantum Platform administrator integration.
- [ ] Submit one diagnostic through the portal/admin path.
- [ ] Locate the corresponding task, run, evidence and explanation.
- [ ] Delete/restart the Hermes worker and prove persistent runtime/task state behaves as documented.
- [ ] Demonstrate one safe failure (for example temporarily unavailable model endpoint) and inspect the recorded failure/evidence.
- [ ] Confirm the Hermes Pod has no broad Kubernetes/OpenStack administrator credential.

# 1. The four things students often confuse

## Agent Control Plane

The ACP is the policy/task/history service. It accepts an authorised task, persists its lifecycle and invokes a bounded worker.

## Hermes

Hermes is the **agent runtime/harness** used by the Phase-1 worker. It is not your source of user identity and it is not allowed to invent its own infrastructure permissions.

## Model server

The model server performs inference. It may be vLLM, Ollama, llama.cpp or another compatible service running on A100/H200 resources.

## Kubernetes

Kubernetes schedules the ACP API, database and worker Pods in your Sebowa cluster. It does not magically move the language model onto an H200.

Put together:

```text
Kubernetes schedules the worker
        ↓
Hermes runs inside the worker
        ↓
ACP controls what task/evidence Hermes receives
        ↓
Hermes calls a remote model API
        ↓
A100/H200 model server performs inference
```

# 2. Read the implemented boundary before deploying

Clone the source:

```bash
cd ~/scc26
git clone https://github.com/nyameko/agent-control-plane.git
cd agent-control-plane
git rev-parse HEAD
```

Read:

```text
README.md
docs/12-phase1.md
```

Then read the deployment runbook in infrastructure:

```text
infra-hpc-qc-k8s/docs/tutorials/10-agent-control-plane-phase1.md
```

The current Phase 1 is intentionally narrow. It is **not** a generic shell tool, Kubernetes administrator, Slurm submitter or autonomous infrastructure engineer.

# 3. Understand the first diagnostic

The implemented Phase-1 action asks a fixed Prometheus question about Quantum Platform Pod readiness. The important safety feature is not the exact metric; it is that user/model input cannot turn this into arbitrary PromQL, a shell command or a cluster-admin action.

The execution pattern is deterministic:

```text
API accepts one allowed task type
         ↓
worker fetches fixed evidence
         ↓
evidence is stored
         ↓
Hermes/model explains the evidence
```

If inference fails after evidence collection, the run can still show what evidence was gathered. This distinction matters when debugging agent systems.

# 4. Validate source before deployment

Follow the Python/runtime versions declared by the current ACP repository. Typical local validation is:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check src tests scripts
pytest
```

Some database/Hermes integration tests require explicit disposable dependencies and may skip locally. Read the test output; a skipped integration test is not the same thing as a passing production guarantee.

# 5. ACP persistent state

The student deployment keeps two different PostgreSQL responsibilities:

```text
Quantum Platform PostgreSQL
    → user / programme / application state

Agent Control Plane PostgreSQL
    → administrative task / run / event / evidence history
```

Do not merge them just because both are PostgreSQL. The separation is deliberate and teaches ownership boundaries.

ACP also gives the Hermes profile its own retained Cinder-backed PVC. Hermes runtime state does **not** replace the ACP task ledger.

# 6. Generate and seal credentials

The upstream Phase-1 runbook includes `scripts/create_secrets.py` and the expected Secret names. Generate plaintext Secret material only in a private local directory, then seal it for the actual student cluster.

Conceptual flow:

```text
create private local ACP credentials
          ↓
kubeseal for THIS cluster/namespace
          ↓
commit only SealedSecrets
          ↓
Argo reconciles
          ↓
runtime Kubernetes Secrets created
```

The design separates credentials:

```text
portal signing private key     → Quantum Platform only
verification public key        → ACP API
DB owner credential            → migration/bootstrap only
restricted app DB credential   → API/worker
model API key                  → Hermes worker only
```

That is what least privilege looks like in practice.

# 7. Configure the remote inference endpoint

The instructor will provide an approved endpoint and credential/placeholder suitable for your team.

The ACP worker expects an OpenAI-compatible base URL including `/v1`, for example conceptually:

```text
https://<approved-inference-endpoint>/v1
```

You will also receive or select the exact model ID exposed by that service.

Do not put the API key in Git. Do not broaden network policy to an entire external network merely because one host is difficult to reach; diagnose DNS/routing/firewall policy first.

# 8. Configure the deployment from `infra-hpc-qc-k8s`

The upstream runbook provides a configuration helper that pins image digests, model route and the Quantum Platform admin integration.

The workflow is intentionally Git-based:

```text
publish/choose compatible image digests
        ↓
configure infra desired state
        ↓
inspect git diff
        ↓
seal required credentials
        ↓
Argo sync ACP
        ↓
promote compatible Quantum Platform integration
```

Before syncing, render and validate the Kustomize output as documented by the current runbook.

> [!IMPORTANT]
> Do not activate the Quantum Platform integration before the compatible portal image/signing Secret and ACP service are ready. Cross-repository integration is an ordering problem, not just a YAML problem.

# 9. Runtime validation

Check the ACP namespace:

```bash
kubectl -n agent-control-plane get pod,svc,pvc
kubectl -n agent-control-plane get events --sort-by=.lastTimestamp | tail -n 30
```

Check application probes through the service path available inside the cluster:

```text
/health  → process-level health
/ready   → includes required database/readiness checks
```

A process can be alive while its database is unavailable; that is why both probes exist.

Confirm the worker is singleton as required by the current Phase-1 contract.

# 10. End-to-end acceptance

Use the Quantum Platform administrator surface to submit the supported diagnostic.

You should be able to demonstrate:

```text
1. authenticated administrator submits diagnostic
2. portal creates a short-lived signed assertion
3. ACP commits task/run to PostgreSQL
4. worker claims the queued run
5. fixed Prometheus evidence is collected
6. evidence is persisted
7. Hermes calls the approved remote model endpoint
8. explanation or explicit failure is persisted
9. portal shows task/run/evidence/event history
```

Record the task/run identifier so you can correlate UI state with database/API/worker logs without exposing secrets.

# 11. Persistence and failure drill

Delete the Hermes worker Pod and allow the StatefulSet/controller to recreate it:

```bash
kubectl -n agent-control-plane get pods
kubectl -n agent-control-plane delete pod <hermes-worker-pod>
kubectl -n agent-control-plane get pods -w
```

Then verify the behavior promised by the Phase-1 documentation:

- retained task/run history still exists in ACP PostgreSQL;
- the Hermes profile PVC remains attached/reused as designed;
- queued/completed/abandoned run behavior is understandable;
- you do not claim "exactly once" execution if the implementation does not provide it.

Also perform one safe failure experiment, such as temporarily using an intentionally unreachable **test** model endpoint under instructor guidance, and confirm the failure is visible rather than silently replaced by an external provider.

# 12. Security acceptance

Inspect the Pod/deployment specification and be able to show that the worker does **not** receive:

```text
cluster-admin RBAC
OpenStack credentials
Docker socket
host filesystem mount
portal signing private key
generic unrestricted shell capability
```

The model can explain evidence. It does not gain authority by being intelligent.

# Success state

Required Week 4 evidence:

```text
✓ ACP source revision recorded and tests reviewed
✓ dedicated ACP PostgreSQL PVC Bound
✓ Hermes profile PVC Bound
✓ only sealed/referential secrets committed
✓ ACP API /health and /ready understood/validated
✓ singleton worker healthy
✓ worker can reach approved A100/H200 model endpoint
✓ Quantum Platform admin integration works
✓ diagnostic creates task/run/event/evidence records
✓ explanation references collected evidence
✓ worker restart preserves required state/history
✓ one controlled failure is visible and understandable
✓ no broad infrastructure credentials granted to Hermes
```

# Troubleshooting model

```text
portal authentication okay?
       ↓
signing/verifying keys compatible?
       ↓
ACP API ready?
       ↓
ACP database/migration healthy?
       ↓
worker claims task?
       ↓
Prometheus evidence reachable?
       ↓
model endpoint reachable/authenticated?
       ↓
Hermes returns output?
       ↓
result/event persisted and shown in portal?
```

Do not skip straight to "the AI is broken." Most failures in an agentic distributed system are ordinary identity, network, database, deployment or configuration failures.

# Deliverable

Commit a Week 4 record containing:

- architecture diagram showing portal → ACP → DB/evidence → Hermes → remote model;
- image/source revisions used;
- proof of one successful end-to-end diagnostic;
- task/run/evidence identifier(s), with secrets redacted;
- worker restart/persistence result;
- controlled failure result;
- a short least-privilege explanation of what credentials the worker has and deliberately does not have.


# Project hand-off

Week 5 turns the common platform into the client and observability plane for your CPU/A100/H200 inference experiments. GPU access is separate from the Sebowa project; do not assume a GPU is attached to the Kubernetes workers.
