Week 2: Kubernetes Substrate & GitOps
========================================

Week 1 created and configured the virtual machines. This week you build the **platform substrate** that will run the rest of the project.

The ownership chain becomes:

```text
Terraform      → OpenStack resources
Ansible        → host/bootstrap configuration
kubeadm        → Kubernetes cluster
Cilium         → pod networking and network policy
Cinder CSI     → persistent Kubernetes block storage
Argo CD        → long-lived Kubernetes desired state
Sealed Secrets → encrypted secret material safe to reconcile from Git
Traefik        → HTTP/HTTPS application ingress
cert-manager   → TLS certificates
```

The most important idea of this week is that each tool has a boundary. Do not make Terraform deploy applications, and do not use `kubectl edit` as a permanent replacement for GitOps.

# Checklist

- [ ] Explain the Kubernetes control plane, worker, Pod, Deployment, Service, Namespace and Ingress concepts.
- [ ] Verify all five Week 1 VMs are healthy before changing them.
- [ ] Install Kubernetes prerequisites/containerd through the upstream Ansible path.
- [ ] Initialise `k8s-cp-01` through the stable HAProxy API endpoint.
- [ ] Join both workers.
- [ ] Confirm all nodes are `Ready`.
- [ ] Install/validate Cilium.
- [ ] Run a Cilium connectivity test and understand what it proves.
- [ ] Install/configure OpenStack cloud integration and Cinder CSI using the upstream GitOps path.
- [ ] Dynamically provision and mount a Cinder PVC.
- [ ] Install Argo CD with Ansible.
- [ ] Install Sealed Secrets and understand the plaintext → sealed → runtime Secret flow.
- [ ] Deploy Traefik through Argo CD.
- [ ] Deploy a simple test application through Git, not an imperative long-term `kubectl` command.
- [ ] Obtain/validate TLS for a team hostname or instructor-provided test hostname.
- [ ] Prove that `Synced`, `Healthy` and `reachable by a user` are three different checks.

# 1. Kubernetes in plain language

Kubernetes schedules containerised workloads across a set of machines.

For this POC:

```text
api-lb-01
    │ stable :6443 endpoint
    ▼
k8s-cp-01
    │ control plane
    ├──────────────────────┐
    ▼                      ▼
k8s-worker-01        k8s-worker-02
```

Important objects:

| Object | Meaning |
| --- | --- |
| Node | A machine participating in the cluster |
| Pod | Smallest scheduled Kubernetes workload unit |
| Deployment | Controller that maintains a desired number of stateless Pods |
| StatefulSet | Controller for workloads that need stable identity/storage semantics |
| Service | Stable virtual endpoint in front of Pods |
| Namespace | Logical grouping/boundary for Kubernetes objects |
| ConfigMap | Non-secret configuration data |
| Secret | Sensitive runtime data; still requires careful access control |
| PVC | Request for persistent storage |
| Ingress | HTTP/HTTPS routing request into a Service |
| NetworkPolicy | Rules governing Pod network communication |

# 2. Preflight

Before Kubernetes:

```bash
cd ~/scc26/infra-hpc-qc-k8s/ansible
ansible all -i inventories/private/hosts.yml -m ping
```

Confirm time, DNS and package access on all Kubernetes hosts. Kubernetes failures caused by broken DNS or clock skew are much harder to understand later.

Check the API LB configuration:

```bash
ssh <api-lb-host>
sudo systemctl is-active haproxy
sudo ss -lntp | grep 6443
```

# 3. Build the cluster with the upstream Ansible roles

The upstream `kubernetes.yml` playbook initialises `k8s-cp-01` and joins the hosts in the `workers` group. Your student inventory deliberately contains only one control plane.

Run the appropriate Kubernetes prerequisite/bootstrap path documented by the current upstream repository, then:

```bash
ansible-playbook \
  -i inventories/private/hosts.yml \
  playbooks/kubernetes.yml
```

Run `kubectl` from the control-plane node (or from a deliberately configured admin workstation):

```bash
kubectl get nodes -o wide
kubectl get pods -A
kubectl get --raw='/readyz?verbose'
```

Expected POC nodes:

```text
k8s-cp-01
k8s-worker-01
k8s-worker-02
```

> [!IMPORTANT]
> `kubectl get nodes` is not a complete acceptance test. It tells you that nodes registered and currently report a status. You still need networking, storage and application-level checks.

# 4. Cilium: the Kubernetes network

A Pod must be able to communicate according to cluster and policy rules even when it moves between worker nodes. Cilium provides the CNI/network dataplane in the reference platform.

After the upstream Cilium application/configuration is installed, check:

```bash
cilium status --wait
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
```

Then run the connectivity test:

```bash
cilium connectivity test --debug
```

A connectivity test is valuable because it tests real Pod/service network paths. If it fails, do not immediately change Cilium configuration. Work through:

```text
OpenStack SGs
    ↓
node routing
    ↓
required Kubernetes ports
    ↓
Cilium agent health
    ↓
pod/service path
```

A healthy Cilium status alone does not prove every NodePort, Ingress or external path works.

# 5. Persistent storage with Cinder CSI

Pods are disposable. Databases and durable application state are not.

OpenStack Cinder provides block volumes; the Cinder CSI driver allows Kubernetes to request and attach them through a `StorageClass` and `PersistentVolumeClaim`.

Conceptually:

```text
Pod
 ↓ mounts
PVC
 ↓ binds
PV
 ↓ implemented by
Cinder CSI
 ↓ creates/attaches
OpenStack Cinder volume
```

Follow the upstream Cinder/Argo path for your cloud. Then inspect:

```bash
kubectl get storageclass
kubectl get pods -A | grep -i cinder
```

Create a small test PVC using the StorageClass available in your environment, for example:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: week2-storage-test
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: <YOUR-CINDER-STORAGECLASS>
  resources:
    requests:
      storage: 1Gi
```

Apply it for the test:

```bash
kubectl apply -f week2-storage-test.yaml
kubectl get pvc week2-storage-test
```

Use a temporary Pod to write a file, delete the Pod, recreate it with the same claim and prove the file still exists.

> [!NOTE]
> Persistence is not the same thing as backup. A Cinder PVC surviving a Pod restart does not prove that you can recover from accidental data deletion, a broken database or loss of the volume.

# 6. Argo CD: the GitOps boundary

The reference repository uses Ansible to bootstrap Argo CD and Sealed Secrets:

```bash
ansible-playbook \
  -i inventories/private/hosts.yml \
  playbooks/argocd.yml
```

Once Argo exists, long-lived Kubernetes applications should normally follow:

```text
Git commit
   ↓
Argo CD
   ↓
render desired state
   ↓
compare with live cluster
   ↓
sync/reconcile
   ↓
Kubernetes
```

The rule for this project is:

> **Use imperative `kubectl` commands to inspect, test and diagnose. Put permanent desired-state changes in Git and let Argo reconcile them.**

Useful checks:

```bash
kubectl -n argocd get pods
kubectl -n argocd get applications
```

Learn the distinction:

```text
Synced   = live resources match the desired Git revision
Healthy  = Argo's health assessment considers the resources healthy
Reachable = an end user can actually use the service end-to-end
```

You need all three forms of evidence.

# 7. Sealed Secrets

A normal Kubernetes Secret manifest is only base64-encoded, not safe to publish as a credential store.

The reference flow is:

```text
plaintext Secret generated locally
          ↓
kubeseal encrypts for your cluster
          ↓
SealedSecret committed to Git
          ↓
Argo applies SealedSecret
          ↓
Sealed Secrets controller creates runtime Secret
```

Example workflow shape:

```bash
kubectl create secret generic example-secret \
  --namespace example \
  --from-literal=EXAMPLE_VALUE='replace-me' \
  --dry-run=client \
  -o json > /tmp/example-secret.json

kubeseal \
  --format yaml \
  < /tmp/example-secret.json \
  > example-secret-sealed.yaml

rm -f /tmp/example-secret.json
```

Your exact `kubeseal` controller/context arguments depend on the cluster.

> [!CAUTION]
> Never commit the intermediate plaintext Secret. Verify the generated SealedSecret is intended for the correct namespace and cluster before relying on it.

# 8. Traefik, DNS and TLS

Traefik is the HTTP/HTTPS ingress controller in the reference platform. It does **not** replace the HAProxy Kubernetes API endpoint.

Different jobs:

```text
HAProxy api-lb-01
    → Kubernetes API :6443

Traefik in Kubernetes
    → application HTTP/HTTPS ingress
```

Typical request path:

```text
browser
  ↓ DNS
team hostname
  ↓
edge/external routing
  ↓
Traefik
  ↓
Kubernetes Service
  ↓
application Pod
```

TLS is obtained through cert-manager using the configured issuer/DNS challenge path. The public `infra-hpc-qc-k8s` manifests show the pattern; your team uses instructor-approved hostnames and credentials.

# 9. Deploy a tiny test application through Git

Before Week 3's real services, prove the entire GitOps/Ingress path with something deliberately simple.

A minimal deployment needs:

```text
Namespace (optional but recommended)
Deployment
Service
Ingress
```

Commit it under a clearly named project-owned path, let Argo reconcile it, then prove:

```bash
kubectl -n <namespace> get deploy,pod,svc,ingress
kubectl -n argocd get applications
curl -vk https://<your-test-hostname>/
```

Check the certificate presented by the endpoint; do not merely see `HTTP 200` and assume TLS is correct.

# Success state

Required Week 2 evidence:

```text
✓ 1 control plane + 2 workers Ready
✓ Kubernetes /readyz healthy
✓ Cilium status healthy
✓ Cilium connectivity test passes or every exception is explained
✓ Cinder StorageClass available
✓ dynamic PVC Bound
✓ data survives Pod replacement using the same PVC
✓ Argo CD running
✓ Sealed Secrets controller running
✓ permanent test app reconciled from Git
✓ Traefik route reachable
✓ TLS certificate valid for intended hostname
✓ team can explain Synced vs Healthy vs reachable
```

# Troubleshooting order

For a failed application path:

```text
Argo desired state correct?
      ↓
Kubernetes object exists?
      ↓
Pod Ready?
      ↓
Service has endpoints?
      ↓
Ingress accepted?
      ↓
Traefik reachable?
      ↓
DNS resolves correctly?
      ↓
TLS valid?
      ↓
user request succeeds?
```

Useful commands:

```bash
kubectl get events -A --sort-by=.lastTimestamp | tail -n 50
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace>
kubectl get endpoints -A
kubectl get ingress -A
kubectl -n argocd get applications
```

# Deliverable

Commit a Week 2 record containing:

- cluster topology and node roles;
- Cilium acceptance evidence;
- storage persistence test evidence;
- Argo application/status evidence;
- explanation of your Sealed Secret flow without exposing a secret;
- working HTTPS test route;
- at least one failure and the layer where you found it.

# Next week

Week 3 installs the observability/security planes and deploys the Quantum Platform user-facing application so you can see both **what the platform is doing** and **what users experience**.
