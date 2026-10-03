# Week 3 — Observability, Security Telemetry & Student Project Platform

Week 3 makes the platform observable and useful. You will deploy operational telemetry, establish host/network security evidence, and put a small authenticated **Student Project Platform** in front of the team environment.

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

## The three observability questions

Do not blur these systems together:

```text
Prometheus/Grafana → Is the platform behaving and consuming resources as expected?
Wazuh              → What host/security events and integrity signals were observed?
Suricata           → What network IDS events were observed?
```

They complement one another. An LLM/agent in Week 4 will explain evidence; it does not replace the evidence sources.

## Deployment order

```text
1. Verify Week-2 Kubernetes/storage/GitOps gates
2. Deploy Prometheus + kube-state-metrics + node exporters
3. Deploy Grafana and Git-managed dashboards
4. Verify actual scrape targets/queries
5. Ansible: Wazuh agents + edge Wazuh Manager
6. Ansible: Suricata on edge in IDS mode
7. Argo: Wazuh indexer/dashboard and required encrypted credentials
8. Prove a fresh benign host/network security event end-to-end
9. Build Student Project Platform image in GitHub CI
10. Argo: PostgreSQL + Student Project Platform
11. Prove login/health/TLS and DB persistence
12. Introduce experiment/evidence provenance contract
13. Week-3 PR and acceptance gate
```

---

# Part A — Prometheus and Grafana

## 1. Deploy through GitOps

The reference platform uses persistent Prometheus/Grafana storage. Your student sizing may be smaller, but keep enough headroom for a six-week lab and do not silently remove persistence.

Merge the monitoring Applications/resources into `dev`, then inspect from the control plane:

```bash
# RUN ON: k8s-cp-01
kubectl -n argocd get applications
kubectl -n monitoring get pods,pvc
kubectl -n monitoring get svc
```

## 2. Verify Prometheus data, not just pods

A `Running` Prometheus pod proves the process started. It does not prove important targets are being scraped.

Query the API:

```bash
# RUN ON: k8s-cp-01
kubectl -n monitoring exec deploy/prometheus-server -c prometheus-server -- \
  wget -qO- 'http://127.0.0.1:9090/api/v1/query?query=up'
```

Check that critical jobs report `1`. Inspect the real scrape configuration/labels before writing dashboards. Do not guess PromQL label names.

## 3. Grafana must be Git-managed

Dashboards used for assessment should live in Git and be loaded by the configured dashboard mechanism/sidecar. Do not manually build the final dashboard only in the Grafana GUI.

Your minimum Week-3 dashboard should show:

- node CPU/memory/filesystem;
- Kubernetes node/pod health;
- Student Project Platform workload health once deployed;
- enough timestamp context to correlate a Week-5 experiment/security run.

---

# Part B — Wazuh and Suricata

## 4. Add host security telemetry deliberately

Week 1 intentionally kept the base bootstrap small. Week 3 is where you deploy/validate security agents and the edge security services.

Canonical student flow:

```text
all team VMs → Wazuh agents → edge Wazuh Manager
                                  │
                                  ▼
                              Filebeat
                                  │
                                  ▼
                       Wazuh indexer in K8s
                                  │
                                  ▼
                              dashboard

edge NIC/traffic → Suricata IDS → EVE JSON → Wazuh/analysis path
```

From workstation:

```bash
# RUN ON: WORKSTATION
cd infrastructure/ansible
ansible-playbook -i inventories/private/hosts.yml playbooks/wazuh-agents.yml
ansible-playbook -i inventories/private/hosts.yml playbooks/edge.yml --tags wazuh,suricata
```

If your student scaffold uses `security.yml`, run that instead. Do not change the architecture simply to match a filename.

## 5. Validate the manager and agents

```bash
# RUN ON: edge-01
sudo systemctl is-active wazuh-manager
sudo /var/ossec/bin/agent_control -l
```

All expected hosts should appear with the intended active state after enrollment/connectivity settles.

If an agent is missing, check:

```text
agent service
→ DNS/manager address
→ OpenStack SG
→ edge nftables
→ enrollment/key state
→ manager logs
```

## 6. Validate Suricata in IDS mode

```bash
# RUN ON: edge-01
sudo systemctl is-active suricata
sudo suricata -T -c /etc/suricata/suricata.yaml
sudo tail -n 20 /var/log/suricata/eve.json
```

The course baseline is **IDS first**. Do not place untested inline IPS blocking in the Week-3 critical path.

## 7. Deploy Wazuh indexer/dashboard through Argo

Keep credentials as SealedSecrets. The current reference platform uses a persistent single Wazuh indexer for the POC and exposes the dashboard only through the intended private/authenticated path.

```bash
# RUN ON: k8s-cp-01
kubectl -n wazuh get pods,svc,pvc
kubectl -n wazuh get events --sort-by=.lastTimestamp | tail -n 40
```

OpenSearch/Wazuh indexer is one of the heavier Week-3 workloads. If scheduling fails, check **requested memory and actual worker capacity** before assuming Kubernetes is broken.

## 8. Perform one fresh, benign detection drill

Use only instructor-approved, non-destructive actions. Examples include a deliberately failed login to a team-owned test account, a harmless request matching a local IDS test rule, or another scenario supplied by the instructor.

Record exact start/end timestamps.

Your evidence chain should be able to answer:

```text
What did we do?
When did we do it?
What did Suricata observe?
What did Wazuh record?
What was the platform health at that time?
Can another team member reconstruct the timeline?
```

Never use historical log lines as proof of a fresh test.

---

# Part C — Student Project Platform

## 9. Why you are not deploying the full Quantum Platform

The production `quantum-platform` includes identity/programme/workbench functionality that would distract from a six-week student POC. You are instead building a deliberately small platform that teaches the same systems boundaries:

```text
Astro frontend
    ↓
small authenticated backend/API
    ↓
PostgreSQL
    ↓
Cinder PVC
```

Week 4 then adds an authenticated server-side ACP client.

## 10. Minimum Week-3 product

The platform should provide:

- team/project name;
- authenticated login/logout;
- a simple profile/home page;
- backend `/health` or equivalent;
- PostgreSQL-backed user/application state;
- a small platform status view driven by **safe backend data**, not cluster-admin credentials in the browser.

Do not spend the week polishing animations while persistence/authentication is broken.

## 11. Build images in GitHub, not manually on the workstation

Preferred path:

```text
source change
→ PR / GitHub Actions
→ tests/lint
→ OCI image build
→ GHCR immutable sha-<commit> tag/digest
→ GitOps image reference
→ Argo CD
```

The workload image should not contain environment credentials or private keys.

Record the exact image digest used for your accepted Week-3 deployment.

## 12. Deploy PostgreSQL first

Through GitOps:

```text
namespace/storage policy
→ Secret/SealedSecret
→ PostgreSQL StatefulSet/PVC
→ migration/init job (if required)
→ backend
→ Astro/static frontend
→ Service/Ingress/TLS
```

From control plane:

```bash
# RUN ON: k8s-cp-01
kubectl -n student-platform get pod,svc,pvc,ingress
kubectl -n student-platform get events --sort-by=.lastTimestamp | tail -n 40
```

## 13. Prove persistence rather than assuming it

Create a test user or other non-sensitive DB-backed object. Record its identifier. Then delete the PostgreSQL **pod** without deleting the PVC:

```bash
# RUN ON: k8s-cp-01
kubectl -n student-platform get pods
kubectl -n student-platform delete pod <postgres-pod>
kubectl -n student-platform get pods -w
```

After recreation, verify the application still sees the previously created record.

That proves your state is not living only in the container filesystem.

## 14. Prove the browser path

Validate:

```text
DNS
→ TLS certificate
→ Traefik route
→ frontend/backend
→ PostgreSQL
```

A successful `kubectl get pod` is not a browser acceptance test.

---

# Part D — Start recording provenance now

`quantum-workflows` treats provenance as part of every scientific result. Adopt the same discipline for all SCC26 projects.

For every significant Week-3+ experiment/demo, record a small machine-readable run manifest such as:

```yaml
schema_version: '1.0'
run_id: <uuid-or-timestamp>
project: inference-fabric-scc26
started_at: <UTC RFC3339>
finished_at: <UTC RFC3339>
source:
  repository: <team-repo-url>
  commit: <git-sha>
  dirty: false
software:
  images:
    student_platform: <immutable digest>
execution:
  location: sebowa-kubernetes
  namespace: <namespace>
parameters: {}
observability:
  prometheus_window: <start/end>
artifacts:
  - path: <relative path or result reference>
    sha256: <digest if retained>
status: completed|failed
```

Never dump the whole environment into provenance. Use an allowlist so future unknown secrets cannot leak.

See `docs/EXPERIMENT-PROVENANCE.md`.

---

# Week-3 acceptance gate

| Gate | Proof |
| --- | --- |
| Prometheus | real targets/queries return current data |
| Grafana | Git-managed dashboard renders live metrics |
| Wazuh | manager active; expected agents enrolled/active |
| Suricata | config valid; fresh EVE event from authorised test |
| Security chain | fresh event reconstructable from timestamps/evidence |
| Student Platform | CI-built immutable image deployed through Argo |
| Auth | real browser login/logout works |
| PostgreSQL | state survives DB pod replacement |
| TLS/Ingress | intended hostname/path works |
| Provenance | at least one run manifest recorded without secrets |
| PR | Week-3 state reviewed and merged into `dev` |

Week 4 will consume this telemetry and platform identity through a bounded Agent Control Plane path.
