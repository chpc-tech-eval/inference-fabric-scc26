# Week 4 — Agent Control Plane, Hermes & Remote A100/H200 Inference

Week 4 adds one bounded agentic vertical slice. The purpose is to learn **authorisation, durable task state, evidence, runtime separation and remote inference**. The purpose is not to hand an LLM unrestricted infrastructure credentials.

## Command-location rule — read this before doing anything

The course deliberately separates **infrastructure authoring** from **cluster administration**.

| Location | Allowed/expected tools |
| --- | --- |
| **WORKSTATION** | Git, SSH, OpenStack CLI, Terraform, Ansible and `kubeseal` |
| **`edge-01`** | WireGuard, Pi-hole/DNS, nftables, Wazuh Manager, Suricata and host diagnostics |
| **`api-lb-01`** | HAProxy and load-balancer diagnostics |
| **`k8s-cp-01`** | `kubectl`, Cilium CLI, Kubernetes diagnostics/bootstrap and optional Argo CD CLI |
| **GitHub** | PRs, CI, OCI image builds, GHCR and GitOps desired state |
| **Kubernetes** | Argo CD, CSI, ingress, monitoring, Wazuh components, Student Project Platform, ACP/Hermes |
| **A100/H200 resource** | only the separately authorised GPU/inference experiment for your project |

> [!IMPORTANT]
> Do **not** copy a Kubernetes admin kubeconfig to your laptop for this project. Do not make permanent application changes with `kubectl edit`. Diagnose from `k8s-cp-01`; repair desired state in Git and let Argo CD reconcile it.

Every command block below states where it runs.

## Mental model

```text
Student browser
      ↓
Student Project Platform
      ↓ authenticated server-side assertion
Agent Control Plane API
      ↓
ACP PostgreSQL (task/run/event/evidence ledger)
      ↓
fixed read-only diagnostic
      ↓
Hermes worker in Sebowa Kubernetes
      ↓ OpenAI-compatible request
approved A100/H200 inference endpoint
      ↓
persisted explanation + evidence
```

Critical distinctions:

```text
Student Platform owns the user-facing session.
ACP owns authorised operational tasks/history.
Hermes is a runtime/harness, not the security boundary.
The model performs inference, not authorisation.
Kubernetes runs the small control-side services; it does not automatically own A100/H200 GPUs.
```

## Deployment order

```text
1. Get instructor-approved immutable ACP/Hermes image references
2. Confirm approved model endpoint and network path
3. Prepare DB/signing/model secrets privately
4. Seal Kubernetes secrets on workstation
5. GitOps: namespace/storage/network policies
6. GitOps: ACP PostgreSQL
7. Run migration job
8. Deploy ACP API
9. Deploy singleton persistent Hermes worker
10. Configure Student Platform server-side ACP integration
11. Run fixed diagnostic end-to-end
12. Test model outage/failure behavior
13. Delete Hermes pod and prove canonical history persists
14. Record image/model/provenance
15. Week-4 PR and acceptance gate
```

---

# Part A — Treat ACP as upstream software first

## 1. Do not fork source merely to deploy it

The team repository owns the deployment/configuration. Use the instructor-approved ACP and Hermes images by immutable digest/tag.

A source contribution to `agent-control-plane` can happen later if your project actually identifies a reusable change.

Record:

```text
ACP API image digest
Hermes worker image digest
Student Platform image digest
ACP schema/migration version
approved model logical ID
model base URL (non-secret endpoint metadata only)
```

## 2. Phase-1 boundary

The reference ACP Phase-1 slice intentionally has:

- one fixed/read-only diagnostic;
- PostgreSQL as durable queue/history;
- one singleton Hermes worker/profile;
- no Kubernetes token in Hermes;
- no shell tool;
- no OpenStack credential;
- no general provisioning endpoint;
- one explicit remote model route.

Preserve this safety boundary before experimenting with richer agents.

---

# Part B — Identity and secrets

## 3. Use a short-lived server-side assertion

The browser authenticates to the Student Project Platform. The platform backend—not JavaScript in the browser—creates the short-lived assertion used to call ACP.

Conceptually:

```text
browser cookie/session
      ↓
Student Platform backend checks user/role
      ↓
signs short-lived assertion
      ↓
ACP verifies public key, issuer/audience/scope/expiry
```

The browser never receives the signing private key or ACP database credentials.

## 4. Generate private values outside Git

If the course starter does not already provide an instructor-managed signing setup:

```bash
# RUN ON: WORKSTATION (private directory)
cd ~/.config/scc26-secrets
openssl genpkey -algorithm ED25519 -out acp-signing-private.pem
openssl pkey -in acp-signing-private.pem -pubout -out acp-signing-public.pem
chmod 600 acp-signing-private.pem
```

Generate strong database passwords using an approved local tool and populate the provided Secret templates. Do not paste them into Discord/issues.

## 5. Seal Kubernetes secrets offline

```bash
# RUN ON: WORKSTATION
kubeseal --cert ~/.config/scc26-secrets/<team>-sealed-secrets.cert \
  --format yaml \
  < ~/.config/scc26-secrets/acp-db-owner-secret.yaml \
  > gitops/resources/agent-control-plane/acp-db-owner-sealed.yaml
```

Repeat for the restricted app DB credential, ACP verification key, Student Platform signing key and model credential as required by the supplied manifests.

Commit only encrypted `SealedSecret` resources/public material.

---

# Part C — GitOps ordering

## 6. Storage and policies before workloads

Recommended order/sync waves:

```text
-4 storage class/persistent policy if needed
-3 namespace + base policy
-2 encrypted secrets
 0 PostgreSQL
 1 migration/bootstrap job
 2 ACP API + Hermes worker
 3 Student Platform ACP integration
```

Do not cargo-cult wave numbers; preserve the real prerequisite order.

## 7. ACP PostgreSQL

Deploy a dedicated ACP PostgreSQL PVC/database instead of reusing the Student Platform DB role/schema. This teaches explicit state ownership.

From `k8s-cp-01`:

```bash
# RUN ON: k8s-cp-01
kubectl -n agent-control-plane get pvc,pod,svc
kubectl -n agent-control-plane get events --sort-by=.lastTimestamp | tail -n 40
```

The API `/ready` should verify the database/schema; process-only `/health` is not enough.

## 8. Migration then API then worker

```bash
# RUN ON: k8s-cp-01
kubectl -n agent-control-plane get jobs
kubectl -n agent-control-plane logs job/<migration-job>
kubectl -n agent-control-plane get deploy,statefulset,pod
```

The worker is intentionally singleton for this phase. Do not scale replicas just because Kubernetes makes it easy.

---

# Part D — Remote inference

## 9. Keep model serving separate from the agent runtime

```text
Hermes CPU pod in Sebowa
       │
       │ authenticated OpenAI-compatible API request
       ▼
A100 or H200 model service
```

Other teams normally **consume** an approved stable endpoint. Inference Fabric later studies the serving layer itself.

Before enabling the worker, confirm the approved destination hostname/IP/port and network policy. Do not open an entire GPU subnet when one endpoint is required.

## 10. Failure semantics matter

A correct system must distinguish:

```text
no telemetry data
model endpoint unavailable
ACP DB unavailable
worker interrupted
successful evidence collection but failed inference
```

Do not turn any of these into a fabricated “healthy” explanation.

---

# Part E — End-to-end acceptance

## 11. Required diagnostic flow

Perform this from the user interface:

```text
1. Login to Student Project Platform.
2. Request the one allowed platform diagnostic.
3. Platform validates the user and signs the short-lived request.
4. ACP persists task + queued run before returning the ID.
5. Worker claims the run.
6. Fixed diagnostic reads the approved Prometheus evidence.
7. Evidence is persisted.
8. Hermes asks the approved model to explain only the supplied evidence.
9. Explanation/status/events are persisted.
10. Student Platform renders the task history/result.
```

From `k8s-cp-01`, correlate system state while the task runs:

```bash
# RUN ON: k8s-cp-01
kubectl -n agent-control-plane get pods
kubectl -n agent-control-plane logs deploy/agent-control-plane-api --tail=100
kubectl -n agent-control-plane logs statefulset/agent-control-plane-hermes --tail=100
```

Use actual resource names from the starter overlay.

## 12. Test one controlled failure

With instructor approval, temporarily point the worker at an unavailable test endpoint or otherwise trigger a safe expected failure. Verify:

- task/run becomes an explicit failure state;
- already-collected evidence remains visible where the contract says it should;
- no result is misreported as success;
- the system recovers after reverting the Git configuration.

Do not test failure by deleting databases/PVCs.

## 13. Restart/persistence test

First identify the Hermes pod:

```bash
# RUN ON: k8s-cp-01
kubectl -n agent-control-plane get pods
```

Delete only the worker pod:

```bash
# RUN ON: k8s-cp-01
kubectl -n agent-control-plane delete pod <hermes-pod>
kubectl -n agent-control-plane get pods -w
```

After recreation, prove:

- historical ACP tasks/runs/evidence are still queryable from PostgreSQL;
- the Hermes profile PVC behaves according to the intended persistence policy;
- a new diagnostic can complete;
- students can explain which data is canonical in PostgreSQL versus runtime-local profile state.

---

# Part F — Security checklist

Before declaring success, verify Hermes/ACP do **not** receive:

- Kubernetes cluster-admin token;
- OpenStack admin credential;
- workstation SSH private key;
- Docker socket/host filesystem mount;
- arbitrary shell endpoint;
- Student Platform signing private key in the ACP API container;
- plaintext model credential in Git.

The language model should receive the minimum evidence/context required to explain the bounded task.

---

# Part G — Provenance

Create a Week-4 run manifest using `docs/EXPERIMENT-PROVENANCE.md`. Include:

```text
team Git SHA
Student Platform image digest
ACP image digest
Hermes image digest
model logical ID / endpoint class
run/task ID
UTC timestamps
result status
safe evidence references
```

Do not record bearer tokens, database passwords or raw private telemetry that is not suitable for the repository.

---

# Week-4 acceptance gate

| Gate | Proof |
| --- | --- |
| GitOps | ACP desired state and encrypted secrets reproducible from repo/private inputs |
| DB | ACP PostgreSQL PVC/schema ready |
| API | health + readiness; authenticated task accepted |
| Worker | singleton Hermes worker healthy with persistent profile |
| Inference | approved A100/H200 endpoint used remotely |
| Evidence | fixed diagnostic persists deterministic evidence before explanation |
| UI | Student Platform displays task/run/evidence/result |
| Failure | one safe failure is explicit, not hallucinated as success |
| Restart | Hermes pod replacement does not erase canonical history |
| Security | no broad cluster/cloud credentials or plaintext secrets exposed |
| PR | accepted Week-4 state merged into `dev` |

Only after this bounded path works should Paperclip or richer specialist agents become optional stretch work.
