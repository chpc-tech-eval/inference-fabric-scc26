# Week 3 — Observability, Security & Student Project Platform

This week answers two questions:

1. **Can we see what the platform is doing?**
2. **Can a real user reach an authenticated, persistent application deployed through our GitOps path?**

You are **not cloning/deploying the production `quantum-platform` repository**. The student exercise uses a deliberately smaller **Student Project Platform** contained in this team repository.

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


## Checklist

- [ ] Deploy Prometheus and Grafana through GitOps.
- [ ] Validate live scrape targets and a real PromQL query.
- [ ] Deploy/validate Wazuh components and edge Wazuh Manager path.
- [ ] Validate Suricata on `edge-01` with a fresh, authorised benign event.
- [ ] Build Student Project Platform images through GitHub Actions and publish immutable GHCR tags/digests.
- [ ] Deploy Student Project Platform through Argo CD.
- [ ] Prove browser login/authenticated page works.
- [ ] Prove PostgreSQL state survives application pod replacement.
- [ ] Capture Week-3 evidence and merge through PR into `dev`.

## 1. Know the three evidence planes

Do not treat all dashboards as interchangeable:

```text
Prometheus / Grafana
    operational metrics, capacity, health trends

Wazuh
    host/security events, integrity/authentication/investigation evidence

Suricata
    network IDS/event evidence
```

A good investigation may correlate all three.

## 2. Prometheus and Grafana

Desired state belongs under `gitops/` and is reconciled by Argo.

```bash
# RUN ON: k8s-cp-01
kubectl -n monitoring get pods,pvc,svc
kubectl -n argocd get applications
```

Check the actual metric path, not merely pod status. Example:

```bash
# RUN ON: k8s-cp-01
kubectl -n monitoring exec deploy/prometheus-server -c prometheus-server --   wget -qO- 'http://127.0.0.1:9090/api/v1/query?query=up'
```

A Grafana dashboard should be explainable in terms of:

```text
metric endpoint → Prometheus scrape → labels → PromQL → panel
```

Do not manually import a dashboard that GitOps claims to own.

## 3. Wazuh

Your exact split follows the provided student scaffold; `edge-01` hosts the Wazuh Manager and Kubernetes may host index/dashboard components.

Host-side validation:

```bash
# RUN ON: edge-01
systemctl is-active wazuh-manager
sudo /var/ossec/bin/agent_control -l
```

Cluster-side validation:

```bash
# RUN ON: k8s-cp-01
kubectl -n wazuh get statefulset,deploy,pod,svc,pvc
```

Focus on **fresh evidence**. Historical errors from earlier setup are not proof of a current incident.

## 4. Suricata

Suricata belongs on the network/security edge in this POC.

```bash
# RUN ON: edge-01
systemctl is-active suricata
sudo test -f /var/log/suricata/eve.json && echo 'eve.json exists'
sudo tail -n 20 /var/log/suricata/eve.json
```

Generate only instructor-approved benign traffic inside your allocated environment. Record:

- event start/end time;
- source/target logical roles;
- expected Suricata evidence;
- corresponding Wazuh or operational evidence where applicable.

Security teams will deepen this in Week 5; all teams need the basic evidence path now.

## 5. Student Project Platform

The platform is intentionally small enough that you can understand it:

```text
Browser
   ↓
Traefik/TLS
   ↓
Astro frontend
   ↓
small authenticated backend/API
   ↓
PostgreSQL
   ↓
Cinder-backed PVC
```

Its purpose is to teach containerisation, authentication, persistent application state, CI, GitOps and the Week-4 ACP integration—not to reproduce the full research portal.

Source/configuration lives under:

```text
platform/
gitops/resources/student-platform/
```

Read [`platform/README.md`](../platform/README.md) before editing it.

## 6. Build images in GitHub, not as an unmanaged laptop artifact

The preferred flow is:

```text
student source change
      ↓ PR / GitHub
GitHub Actions test/build
      ↓
GHCR immutable image
      ↓
GitOps image reference
      ↓
Argo CD
      ↓
Kubernetes
```

Docker/Podman may be useful locally if you already know them, but they are not required to become another mandatory workstation administration dependency.

Record the image tag/digest used for the Week-3 accepted deployment.

## 7. Deploy and inspect from `k8s-cp-01`

After the reviewed Git change is merged/synced:

```bash
# RUN ON: k8s-cp-01
kubectl -n student-platform get deploy,statefulset,pod,svc,pvc,ingress
kubectl -n argocd get applications
```

The browser acceptance test should prove:

```text
DNS resolves
TLS is valid for the intended access path
frontend loads
login succeeds
backend is reachable
PostgreSQL is reachable
an authenticated page renders
```

## 8. Persistence test

Create a harmless test account/record, identify the application/API pod, delete that pod and allow Kubernetes to recreate it.

```bash
# RUN ON: k8s-cp-01
kubectl -n student-platform get pods
kubectl -n student-platform delete pod <application-pod>
kubectl -n student-platform get pods -w
```

Then confirm the record still exists. The objective is to demonstrate that application pods are replaceable while canonical state lives in PostgreSQL/Cinder.

Do **not** delete the PostgreSQL PVC during this test.

## 9. Week-3 platform view

A simple dashboard is enough:

```text
┌──────────────────────────────────────────┐
│ SCC26 — Inference Fabric                     │
│                                          │
│ Welcome, <student>                       │
│                                          │
│ Platform                                 │
│ ● Kubernetes                             │
│ ● PostgreSQL                             │
│ ● Prometheus                             │
│                                          │
│ Team                                     │
│ <members / project>                      │
│                                          │
│ [ Profile ]                  [ Sign out ]│
└──────────────────────────────────────────┘
```

Do not spend Week 3 building a huge UI. Working identity/state/deployment is more important than visual complexity.

## Exit gate

```text
[k8s-cp-01] Prometheus/Grafana running with live data
[edge-01]    Wazuh Manager + active agents evidenced
[edge-01]    Suricata produces a fresh authorised event
[GitHub]     Student Platform image built/tested and pinned
[Kubernetes] Student Platform + PostgreSQL deployed through Argo
[Browser]    authenticated page works over the intended route
[Persistence] state survives application-pod replacement
```

Next week the Student Project Platform becomes a client of Agent Control Plane.
