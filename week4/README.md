# Week 4 — Agent Control Plane & Hermes

Week 4 adds one deliberately bounded agentic vertical slice. The aim is to understand **identity → authorised task → persistent evidence/history → Hermes explanation → remote inference**, not to create an unrestricted autonomous administrator.

You operate the instructor-approved upstream ACP/Hermes images; you do not need to clone the ACP repository merely to deploy it.

# Where commands run

This programme has a deliberately strict administration boundary. **Do not install or use `kubectl` or the Argo CD CLI on your personal workstation for this project.**

| Location | Tools / responsibilities |
| --- | --- |
| **Your workstation / laptop / desktop** | Git, SSH, OpenStack CLI, Terraform, Ansible and `kubeseal` |
| **GitHub** | source control, pull requests, CI, container builds, GHCR images and GitOps desired state |
| **`edge-01`** | WireGuard, Pi-hole/DNS, nftables, Wazuh Manager, Suricata and edge troubleshooting |
| **`api-lb-01`** | HAProxy and API-endpoint troubleshooting |
| **`k8s-cp-01`** | `kubectl`, Cilium CLI, Kubernetes bootstrap/diagnostics and any optional Argo CD CLI use |
| **Kubernetes** | Argo CD, Cinder CSI, Traefik, cert-manager, Prometheus/Grafana, Wazuh components, Student Project Platform, ACP and Hermes |
| **A100/H200 systems** | separately authorised model serving or project-specific GPU experiments |

A command block in these tutorials is prefixed with its execution location. For example:

```bash
# RUN ON: WORKSTATION
terraform plan
```

or:

```bash
# RUN ON: k8s-cp-01
kubectl get nodes
```

The objective is to keep Kubernetes credentials and cluster administration **inside the cluster administration boundary**, while your workstation remains the infrastructure-authoring and automation machine.


## Mental model

```text
Student browser
      ↓
Student Project Platform
      ↓ short-lived server-side authenticated assertion
Agent Control Plane API
      ↓
ACP PostgreSQL task/run/event history
      ↓
fixed diagnostic/evidence collection
      ↓
Hermes worker (CPU pod in Sebowa)
      ↓
approved remote model endpoint
      ↓
A100 / H200 inference
      ↓
persisted evidence + explanation
```

Important distinctions:

```text
ACP        != Hermes
Hermes     != the language model
model      != Kubernetes
Kubernetes != owner of the A100/H200 allocation
```

## Checklist

- [ ] Deploy dedicated ACP PostgreSQL storage through GitOps.
- [ ] Deploy pinned ACP API and Hermes worker images.
- [ ] Configure a team-specific approved model endpoint/credential using Sealed Secrets.
- [ ] Keep the ACP API private/internal; the browser talks to the Student Platform, not directly to ACP.
- [ ] Validate one fixed/read-only diagnostic end-to-end.
- [ ] Show persistent task/run/evidence/result history in Student Project Platform.
- [ ] Delete/respawn Hermes and prove canonical ACP history remains.
- [ ] Record the exact ACP/Hermes image digests and model endpoint identifier used.
- [ ] Merge the accepted Week-4 state into `dev`.

## 1. What ACP owns

For this student slice:

- Student Project Platform owns the student's web session/identity surface.
- ACP owns authorised agent tasks, runs, events/evidence and policy checks.
- ACP PostgreSQL is the canonical operational ledger.
- Hermes is a runtime/harness with its own bounded persistent profile.
- the A100/H200 endpoint performs inference.
- Kubernetes runs the small CPU-side services but does not become the GPU scheduler.

## 2. GitOps layout

Keep deployment configuration in this repository:

```text
gitops/resources/agent-control-plane/
├── namespace.yaml
├── storage.yaml
├── postgres.yaml
├── api.yaml
├── hermes.yaml
├── networkpolicy.yaml
└── *-sealed.yaml
```

Use immutable image references announced/provided by the instructor. Do not float on `latest` during the assessed baseline.

## 3. Secrets are created/sealed from the workstation without local kubectl

The workstation may generate local secret/key material and use `kubeseal`; it does not need a Kubernetes kubeconfig.

For example, generate an Ed25519 signing key pair for the Student Platform → ACP assertion contract if the provided starter does not already supply an instructor-managed key:

```bash
# RUN ON: WORKSTATION (private directory outside Git)
openssl genpkey -algorithm ED25519 -out acp-signing-private.pem
openssl pkey -in acp-signing-private.pem -pubout -out acp-signing-public.pem
chmod 600 acp-signing-private.pem
```

Use the supplied Secret YAML templates, populate them only in a private temporary directory, seal them with the controller public certificate:

```bash
# RUN ON: WORKSTATION
kubeseal --cert team-sealed-secrets-public.pem --format yaml   < /private/path/acp-model-secret.yaml   > gitops/resources/agent-control-plane/acp-model-sealed.yaml
```

Then securely remove the temporary plaintext manifest when it is no longer required. Do not commit raw keys/API tokens.

## 4. Remote model endpoint

The Hermes worker should normally be a small CPU workload in your Sebowa Kubernetes cluster. Inference happens remotely:

```text
Hermes pod
   │ HTTPS/OpenAI-compatible request
   ▼
approved model service
   ├── A100
   └── H200
```

The instructor provides/approves endpoint details and access policy. Never expose someone else's shared GPU service publicly merely to make your lab easier.

Inference Fabric students later experiment with the serving layer itself; other teams should consume stable approved endpoints.

## 5. Deploy through Git/Argo

Push the reviewed SealedSecrets/config/image references and let Argo reconcile them. Inspect only from the cluster admin node:

```bash
# RUN ON: k8s-cp-01
kubectl -n agent-control-plane get pod,svc,pvc
kubectl -n agent-control-plane get events --sort-by=.lastTimestamp | tail -n 30
kubectl -n argocd get applications
```

The exact namespace/resource names may follow the supplied student overlay.

## 6. Student Project Platform agent panel

A minimal Week-4 UI is enough:

```text
┌──────────────────────────────────────────────┐
│ SCC26 — Inference Fabric                         │
│                                              │
│ Platform                                     │
│ ● Kubernetes                                │
│ ● Prometheus                                │
│ ● Wazuh                                     │
│                                              │
│ Agent Control Plane                          │
│ [ Run Platform Diagnostic ]                  │
│                                              │
│ Recent Agent Runs                            │
│ <id>   Complete   <time>                     │
│                                              │
│ Hermes                                       │
│ <evidence-grounded explanation>              │
└──────────────────────────────────────────────┘
```

The browser must never receive ACP database credentials, model keys or a broad administrator token.

## 7. Required end-to-end demonstration

Demonstrate and record:

```text
1. Student logs into Student Project Platform.
2. Student requests the allowed diagnostic.
3. Platform authenticates/authorises and makes its server-side ACP request.
4. ACP records the task/run.
5. Worker collects the fixed evidence.
6. Hermes invokes the approved A100/H200 model endpoint.
7. Explanation is stored and displayed with task/evidence history.
8. Failure is explicit if evidence/model is unavailable; do not fabricate healthy state.
```

## 8. Restart/persistence test

```bash
# RUN ON: k8s-cp-01
kubectl -n agent-control-plane get pods
kubectl -n agent-control-plane delete pod <hermes-worker-pod>
kubectl -n agent-control-plane get pods -w
```

After restart:

- previous ACP task/run/evidence records must remain visible;
- the persistent Hermes profile should behave according to the provided volume policy;
- a new diagnostic should complete normally;
- students should be able to explain which state belongs in PostgreSQL versus the runtime profile.

## 9. What is deliberately not Week 4

Do not add these just because they sound exciting:

- arbitrary shell commands from the agent;
- Kubernetes cluster-admin credentials in Hermes;
- OpenStack administrator credentials in Hermes;
- autonomous remediation;
- Paperclip meta-orchestration before the basic vertical slice works;
- personal long-term research memory;
- uncontrolled model routing.

Paperclip or richer specialist agents are stretch work after the bounded ACP path is reliable and auditable.

## Exit gate

```text
[GitHub/Argo] ACP desired state and encrypted secrets are reproducible
[k8s-cp-01]  ACP API, PostgreSQL and Hermes worker are healthy
[Student UI] authenticated fixed diagnostic can be submitted
[ACP]         task/run/evidence/explanation persist
[Inference]   approved A100/H200 endpoint is used remotely
[Restart]     Hermes pod replacement does not erase canonical history
[Security]    no plaintext secrets or broad cluster credentials are exposed
```

Week 5 now uses this common platform for the project-specific MVP.
