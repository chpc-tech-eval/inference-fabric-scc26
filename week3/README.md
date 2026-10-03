Week 3: Observability, Security & Quantum Platform
===================================================

This is the week your cluster stops being a collection of mostly opaque services and becomes something you can **observe, investigate and use through a browser**.

You will deploy and validate three different kinds of visibility:

```text
Prometheus / Grafana
    → operational metrics and resource health

Wazuh
    → host/security events and investigation

Suricata
    → network IDS evidence
```

You will also deploy the small **Quantum Platform** web application stack:

```text
Astro user interface
        ↓
Django user API / authentication
        ↓
PostgreSQL
```

These are complementary systems. Grafana is not a replacement for Wazuh; Wazuh is not a replacement for Prometheus.

# Checklist

- [ ] Explain metrics, logs/events, alerts and traces at a high level.
- [ ] Deploy Prometheus through the GitOps path.
- [ ] Deploy Grafana and verify it queries the live Prometheus instance.
- [ ] Validate node/Kubernetes metrics from actual targets.
- [ ] Bring the edge Wazuh Manager into its intended Week 3 state.
- [ ] Confirm Wazuh agents are enrolled with stable identities.
- [ ] Deploy/validate the Wazuh Indexer and Dashboard in Kubernetes.
- [ ] Deploy/validate Suricata on the edge path.
- [ ] Generate one **benign, authorised, fresh** security event and trace the evidence path.
- [ ] Clone/build/test the current `quantum-platform` source.
- [ ] Deploy Quantum Platform through the infrastructure GitOps manifests.
- [ ] Confirm PostgreSQL persistence.
- [ ] Create a user/login session through the browser.
- [ ] Verify HTTP health endpoints independently of the user-facing page.
- [ ] Explain why a healthy Pod is not necessarily a healthy application.

# 1. Operational telemetry: Prometheus and Grafana

Prometheus periodically scrapes numeric metrics. Grafana queries and visualises them.

```text
metric endpoint
     ↓ scrape
Prometheus
     ↓ PromQL
Grafana
```

The key learning objective is not "install Grafana". It is:

> **Prove that what Grafana displays corresponds to live metrics from the components you think you are observing.**

After the upstream applications are reconciled:

```bash
kubectl -n monitoring get pods,pvc,svc
kubectl -n argocd get applications
```

Query Prometheus directly before trusting a dashboard:

```bash
kubectl -n monitoring exec deploy/prometheus-server -c prometheus-server -- \
  wget -qO- 'http://127.0.0.1:9090/api/v1/query?query=up'
```

Look for the actual target labels and job names in your deployment. Do not copy a PromQL query from a screenshot and assume your labels are identical.

Useful questions:

- Which targets are `up == 1`?
- Which targets are missing?
- How much CPU and memory are your worker nodes using?
- What changes when you start/stop a test workload?
- Does the graph time window actually include your experiment?

# 2. Wazuh: host/security event evidence

The reference architecture deliberately keeps the Wazuh Manager on `edge-01` while the Wazuh Indexer/Dashboard run in Kubernetes.

Simplified path:

```text
VM Wazuh agent
      ↓
edge-01 Wazuh Manager
      ↓
alerts.json
      ↓ Filebeat/TLS
Wazuh Indexer in Kubernetes
      ↓
Wazuh Dashboard
```

Why split it this way? The management/security sensor can keep collecting host evidence even if the Kubernetes application plane is unhealthy.

Use the upstream runbook as the detailed source:

```text
infra-hpc-qc-k8s/docs/tutorials/wazuh-suricata-deployment.md
infra-hpc-qc-k8s/docs/tutorials/wazuh-suricata-operational-drills.md
```

First check the Manager locally on edge:

```bash
sudo systemctl status wazuh-manager --no-pager
sudo /var/ossec/bin/agent_control -l
sudo tail -n 50 /var/ossec/logs/ossec.log
sudo test -s /var/ossec/logs/alerts/alerts.json && echo 'alerts.json has events'
```

Then validate Kubernetes components:

```bash
kubectl -n wazuh get statefulset,deploy,pod,svc,pvc
kubectl -n wazuh get events --sort-by=.lastTimestamp | tail -n 25
```

Do not expose the Wazuh Indexer or administrative APIs publicly just to make testing convenient.

# 3. Suricata: network IDS evidence

Suricata examines network traffic and writes structured EVE JSON records.

Reference path:

```text
edge network interface
       ↓
Suricata
       ↓
/var/log/suricata/eve.json
       ↓
Wazuh log collector / decoder / rules
       ↓
security investigation
```

Validate the service and fresh data:

```bash
sudo systemctl status suricata --no-pager
sudo test -s /var/log/suricata/eve.json && echo 'eve.json has events'
sudo tail -n 20 /var/log/suricata/eve.json
```

> [!IMPORTANT]
> Always use a **fresh time window** when proving a detection. Old alerts from yesterday are not evidence that today's configuration works.

# 4. Run one benign security drill

Use an instructor-approved, harmless event that should produce observable evidence. The purpose is to prove the chain, not to perform a sophisticated attack.

Record:

```text
start timestamp
source host
expected event
actual Wazuh evidence
actual Suricata evidence (where applicable)
Prometheus health context
end timestamp
```

Then answer:

- Which component first observed the event?
- Which component stored the canonical security record?
- Was there any delay?
- Was the event visible in Grafana? If so, was that security evidence or only operational context?
- What would be lost if Kubernetes were down?

# 5. Quantum Platform: what you are deploying

The `quantum-platform` repository separates the user experience from the backend business logic:

```text
browser
  ↓
Astro users frontend
  ↓ same-origin API/session path
Django user API
  ↓
PostgreSQL
```

Astro owns presentation. Django owns authentication/authorisation and application rules. PostgreSQL owns durable platform state.

Clone and record the exact source revision:

```bash
cd ~/scc26
git clone https://github.com/nyameko/quantum-platform.git
cd quantum-platform
git rev-parse HEAD
```

Read the project root README before deploying it. The application has moved quickly; use the instructor's tested baseline rather than combining arbitrary commits from different days.

# 6. Build/test the application source

Frontend checks from the repository root:

```bash
npm install
npm run check
npm run build
```

For the Django API, use the Python version and dependency instructions declared by the current repository. Typical checks include:

```bash
cd apps/user-api
python -m venv .venv
source .venv/bin/activate
pip install -e .
python manage.py check
python manage.py makemigrations --check
```

Do not run the Django development server as your production deployment. The purpose of local/source checks is to fail early before publishing/deploying an image.

# 7. Container images and immutable deployment

The application repository builds OCI images for the frontend/backend components. Your Week 2 work already established the GitOps control plane.

The deployment chain should be:

```text
source commit
    ↓ CI/build
container image
    ↓ preferably immutable SHA/digest reference
infra Git desired state
    ↓
Argo CD
    ↓
Kubernetes
```

Do not deploy a locally modified image under an ambiguous floating tag and then lose track of what code actually ran.

# 8. Deploy Quantum Platform

The Kubernetes desired state lives in `infra-hpc-qc-k8s`, under the Argo/Quantum Platform resources.

The student POC may reduce non-essential replicas, but preserve the key service boundaries:

```text
Astro users frontend
Django user-api
PostgreSQL
Ingress / TLS
persistent database volume
```

After sync:

```bash
kubectl -n quantum-platform get deploy,statefulset,pod,svc,pvc,ingress
kubectl -n argocd get application quantum-platform -o wide
```

Check the API health endpoint through the service/ingress path used in your environment.

Then use the browser. A successful Kubernetes rollout is not enough; test the actual user workflow.

# 9. Browser acceptance

At minimum:

```text
1. Open the team Quantum Platform URL.
2. Reach the user/login interface.
3. Create or use the instructor-approved test account.
4. Complete the available login/session flow.
5. Open the authenticated dashboard/profile surface.
6. Log out.
```

The exact account/verification workflow depends on the tested application baseline and environment email configuration. Do not weaken Django security settings merely to skip a step; document any lab-specific mail/verification mechanism.

# 10. Prove PostgreSQL persistence

Find the PostgreSQL StatefulSet/PVC:

```bash
kubectl -n quantum-platform get statefulset,pod,pvc
```

Create a known test record through the normal application workflow, then restart/delete the application/database Pod in the safe manner described by the deployment runbook. Confirm the record remains.

Again:

```text
persistent volume ≠ backup
```

Your evidence is that routine Pod replacement does not erase the application database.

# Success state

Required Week 3 evidence:

```text
✓ Prometheus running with expected live targets
✓ Grafana displays a query you independently verified in Prometheus
✓ Wazuh Manager healthy on edge
✓ intended Wazuh agents enrolled/active
✓ Wazuh Indexer/Dashboard storage healthy
✓ Suricata service healthy and fresh EVE data visible
✓ one authorised benign event traced through the security evidence path
✓ Quantum Platform images/source baseline recorded
✓ Quantum Platform Pods/Services/PVC/Ingress healthy
✓ browser login/session path works
✓ PostgreSQL-backed state survives Pod replacement
✓ no plaintext application/security secrets committed to Git
```

# Troubleshooting mental model

For observability:

```text
source emits metric?
   ↓
Prometheus target discovers/reaches it?
   ↓
query returns expected labels/data?
   ↓
Grafana query uses those labels?
```

For Wazuh:

```text
agent active?
   ↓
Manager receives/processes event?
   ↓
alert generated?
   ↓
Filebeat/indexer path healthy?
   ↓
Dashboard query/time window correct?
```

For Quantum Platform:

```text
image correct?
   ↓
Pod Ready?
   ↓
Service endpoints?
   ↓
Ingress/TLS?
   ↓
Django health?
   ↓
PostgreSQL reachable?
   ↓
browser auth/session workflow?
```

# Deliverable

Commit a Week 3 record containing:

- screenshot/query evidence for one live Grafana metric;
- Wazuh agent inventory evidence with sensitive details redacted;
- benign event timeline and Wazuh/Suricata evidence references;
- Quantum Platform deployment revision/image references;
- browser acceptance evidence;
- persistence test result;
- one example where `Argo Healthy` or `Pod Ready` did **not** by itself prove the user experience.

# Next week

Week 4 connects Quantum Platform to a bounded Agent Control Plane and a persistent Hermes worker. The worker runs on your Kubernetes CPU resources but makes inference calls to separately provided A100/H200 model endpoints.
