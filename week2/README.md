# Week 2 — Kubernetes substrate, Cilium, Cinder & GitOps

Week 2 turns the verified Week-1 Linux VMs into a small Kubernetes platform, proves networking and persistent storage, and establishes the GitOps boundary. This is the week where **`k8s-cp-01` becomes the Kubernetes administration host**.

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

## The ownership model

```text
Terraform → OpenStack infrastructure
Ansible   → OS + containerd + kubeadm/bootstrap
kubeadm   → Kubernetes control-plane/worker registration
Cilium    → pod/service networking + NetworkPolicy datapath
Argo CD   → long-lived Kubernetes application lifecycle
CSI       → persistent storage implementation
```

The important upstream lesson is that Ansible should not gradually become a Kubernetes application installer. Bootstrap the cluster and GitOps controllers; then hand long-lived application state to Argo CD.

## Deployment order

```text
0. Confirm Week-1 exit gate
1. Ansible: containerd + Kubernetes prerequisites
2. Validate CRI and host kernel settings
3. Ansible/kubeadm: initialize k8s-cp-01 and join two workers
4. From k8s-cp-01: prove API healthy (nodes may be NotReady)
5. Install Cilium
6. Prove all nodes Ready and run connectivity test
7. Bootstrap Argo CD + Sealed Secrets
8. Point root Application at this team's repo/dev branch
9. Obtain only the Sealed Secrets PUBLIC certificate for workstation use
10. Seal Cinder/OpenStack credentials on workstation
11. Argo: deploy Cinder CSI + StorageClasses
12. PVC write/recreate/read persistence test
13. Argo: deploy Traefik/cert-manager/DNS/TLS baseline
14. GitOps drift test
15. Week-2 PR and acceptance gate
```

---

# Part A — Kubernetes host prerequisites

## 1. Verify Week 1 first

```bash
# RUN ON: WORKSTATION
cd infrastructure/terraform/environment
terraform plan
```

There should be no unexplained infrastructure changes.

```bash
# RUN ON: WORKSTATION
cd ../../ansible
ansible all -i inventories/private/hosts.yml -m ping
```

If either fails, fix Week 1 before proceeding.

## 2. Install Kubernetes prerequisites using Ansible

The reference platform separates runtime ownership cleanly:

```text
containerd role
  ├── repository/package
  ├── /etc/containerd/config.toml
  ├── SystemdCgroup=true
  └── service

kube prerequisites role
  ├── overlay
  ├── br_netfilter
  ├── bridge netfilter sysctls
  ├── ip_forward
  ├── kubelet/kubeadm/kubectl
  └── crictl config
```

Run the student equivalent:

```bash
# RUN ON: WORKSTATION
cd infrastructure/ansible
ansible-playbook -i inventories/private/hosts.yml playbooks/kubernetes-prereqs.yml
```

The current instructor reference uses Kubernetes `v1.36.4` and containerd `2.3.4`. Use the instructor-pinned weekly baseline; do not silently upgrade one node independently.

## 3. Validate the runtime before kubeadm

```bash
# RUN ON: WORKSTATION
ansible control_plane:workers -i inventories/private/hosts.yml -b -m shell \
  -a 'containerd --version; systemctl is-active containerd; crictl info >/dev/null && echo CRI_OK'
```

Also verify kernel settings:

```bash
# RUN ON: WORKSTATION
ansible control_plane:workers -i inventories/private/hosts.yml -b -m shell \
  -a 'lsmod | egrep "overlay|br_netfilter"; sysctl net.ipv4.ip_forward net.bridge.bridge-nf-call-iptables'
```

A `permission denied` on `/run/containerd/containerd.sock` when testing as an unprivileged user is a **local Unix socket permission problem**, not a cloud security-group problem. Run the CRI check with privilege escalation.

---

# Part B — kubeadm bootstrap

## 4. Initialize the cluster through the stable API endpoint

The kubeadm configuration should use:

```text
controlPlaneEndpoint = <API_LB_PRIVATE_IP_OR_DNS>:6443
advertiseAddress     = <K8S_CP_01_PRIVATE_IP>
podSubnet            = <TEAM_POD_CIDR>
serviceSubnet        = 10.96.0.0/12 (unless instructor specifies otherwise)
CRI socket           = unix:///run/containerd/containerd.sock
```

Run the student cluster playbook:

```bash
# RUN ON: WORKSTATION
ansible-playbook -i inventories/private/hosts.yml playbooks/kubernetes.yml
```

For this POC it should:

1. initialize `k8s-cp-01` if `/etc/kubernetes/admin.conf` is absent;
2. generate temporary worker join material;
3. join `k8s-worker-01` and `k8s-worker-02` serially;
4. configure the administrator kubeconfig **on `k8s-cp-01`**.

Kubeadm bootstrap tokens are temporary runtime material. Do not commit them to inventory/Git.

## 5. Switch your operational viewpoint to `k8s-cp-01`

```bash
# RUN ON: WORKSTATION
ssh <admin-user>@<k8s-cp-private-ip>
```

Then:

```bash
# RUN ON: k8s-cp-01
kubectl cluster-info
kubectl get --raw='/readyz?verbose'
kubectl get nodes -o wide
kubectl get pods -A -o wide
```

Immediately after kubeadm and before Cilium, this is normal:

```text
API healthy
control-plane static pods Running
workers registered
nodes NotReady
CoreDNS Pending
```

That means **Kubernetes API healthy ≠ pod networking ready**.

## 6. Validate HAProxy after kubeadm

```bash
# RUN ON: api-lb-01
sudo systemctl is-active haproxy
sudo journalctl -u haproxy --since '-10 min' --no-pager | tail -n 80
```

The CP backend should transition from DOWN to UP.

From `k8s-cp-01` or another private/VPN client:

```bash
# RUN ON: k8s-cp-01
curl -k https://<api-lb-address>:6443/healthz
```

Expected: `ok`.

---

# Part C — Cilium networking

## 7. Confirm cloud network rules before Cilium

For the reference VXLAN baseline, Kubernetes node security groups must permit at least the instructor-approved Cilium node-to-node paths, including VXLAN (`UDP 8472`) and health traffic (`TCP 4240`) inside the Kubernetes network.

Do not put these rules in edge nftables; they are Kubernetes-node traffic.

If rules are missing, change Terraform, review the plan and apply it from the workstation.

## 8. Install the instructor-pinned Cilium baseline

The instructor reference is Cilium `1.20.1`, initially retaining kube-proxy. Use the course-provided pinned values rather than enabling advanced features during first bring-up.

The first CNI bootstrap may use the Cilium CLI/Helm from `k8s-cp-01`; after GitOps is established, configuration should be represented in Git/Argo.

Illustrative baseline:

```bash
# RUN ON: k8s-cp-01
cilium install --version 1.20.1
cilium status --wait
```

If your starter repository supplies a values file, use it exactly and record its Git SHA.

## 9. Prove the cluster is actually network-ready

```bash
# RUN ON: k8s-cp-01
kubectl get nodes
kubectl -n kube-system get pods -o wide
cilium status --wait
cilium connectivity test
```

Your exit condition is not merely “Cilium pods Running.” The connectivity test exercises pod-to-pod/service/policy paths.

If Cilium pods run but cross-node networking fails, check the **OpenStack node security groups first** before changing Cilium modes.

---

# Part D — Bootstrap Argo CD and Sealed Secrets

## 10. Why this is the ownership transition

The upstream platform tried Ansible+Helm for CSI application lifecycle and ran into increasing coupling: remote Python Kubernetes client dependencies, kubeconfig permissions and package-install responsibilities. The architectural conclusion was:

```text
Terraform → cloud
Ansible   → machines/bootstrap
Argo CD   → Kubernetes applications
```

Your team should learn the final boundary, not repeat every dead end.

## 11. Bootstrap controllers with Ansible

The student playbook may install Argo CD and the Sealed Secrets controller by executing cluster-side `kubectl` on `k8s-cp-01`. The workstation itself still has no kubeconfig.

```bash
# RUN ON: WORKSTATION
ansible-playbook -i inventories/private/hosts.yml playbooks/argocd.yml
```

Then inspect from the control plane:

```bash
# RUN ON: k8s-cp-01
kubectl -n argocd get pods
kubectl -n kube-system get deployment sealed-secrets-controller
kubectl -n argocd get applications
```

Your root Application should point to **this team repository**, normally tracking protected `dev` during the active project:

```text
repoURL: https://github.com/chpc-tech-eval/<team-repo>.git
targetRevision: dev
path: gitops/applications-or-root
```

`main` remains the reviewed release branch.

## 12. Public certificate to the workstation; private key stays in cluster/recovery storage

The Sealed Secrets private key belongs to the cluster and secure DR storage. It is never copied into the repository.

Use the instructor/student bootstrap helper to export **only the public sealing certificate** from the cluster to a temporary path on `k8s-cp-01`, then copy that public certificate to your workstation. The exact helper may be provided by the course scaffold.

Result on workstation:

```text
~/.config/scc26-secrets/<team>-sealed-secrets.cert
```

This file is public cryptographic material; the controller's private key is not.

---

# Part E — Cinder CSI persistent storage

## 13. Understand the credential separation

```text
Argo CD Kubernetes identity  ≠  OpenStack Cinder credential
```

Argo CD uses its in-cluster ServiceAccount to create Kubernetes objects. Cinder CSI separately needs an OpenStack application credential so it can provision/attach volumes.

## 14. Create the plaintext Cinder Secret only in a private workstation directory

Use the course template and your team OpenStack application credential. Do not type secrets into a tracked file.

```bash
# RUN ON: WORKSTATION
cp gitops/templates/cinder-csi-secret.example.yaml \
  ~/.config/scc26-secrets/cinder-csi-secret.yaml
chmod 600 ~/.config/scc26-secrets/cinder-csi-secret.yaml
$EDITOR ~/.config/scc26-secrets/cinder-csi-secret.yaml
```

Seal it offline with the public certificate:

```bash
# RUN ON: WORKSTATION
kubeseal \
  --cert ~/.config/scc26-secrets/<team>-sealed-secrets.cert \
  --format yaml \
  < ~/.config/scc26-secrets/cinder-csi-secret.yaml \
  > gitops/resources/cinder-csi/cinder-csi-cloud-config-sealed.yaml
```

Inspect the resulting YAML: it must be a `SealedSecret`, not a plaintext `Secret` containing your credential.

Securely retain/recreate the plaintext source according to instructor policy; never commit it.

## 15. Deploy CSI through Argo

Commit/push the Cinder Application, StorageClasses and sealed credential through the normal PR/GitOps path.

From `k8s-cp-01`:

```bash
# RUN ON: k8s-cp-01
kubectl -n argocd get applications
kubectl -n kube-system get pods | grep -i cinder
kubectl get storageclass
```

The reference platform models `cinder-ssd`, `cinder-hdd` and provider-default classes where those volume types exist. Use only types available in your Sebowa project.

## 16. Persistence exercise — write, recreate, read

Create the provided Git-managed PVC/test workload. Once Argo reconciles it:

```bash
# RUN ON: k8s-cp-01
kubectl get pvc -A
kubectl get pv
```

Write a marker using the test pod, record it, delete/recreate the pod (not the PVC), and verify the marker survives.

A successful test proves:

```text
PVC requested
→ Cinder volume provisioned
→ attached
→ mounted
→ data written
→ pod replaced
→ same persistent data read
```

Do not claim persistence merely because the PVC is `Bound`.

---

# Part F — Traefik, cert-manager, DNS and TLS

## 17. Keep controller and configuration concerns separate

A useful GitOps model is:

```text
cert-manager            → controller/chart
cert-manager-config     → ClusterIssuer + encrypted credential
Traefik                 → ingress controller
student-platform        → Deployment/Service/Ingress
```

Use Argo sync waves only for real prerequisites; do not create a decorative dependency maze.

## 18. DNS/TLS baseline

Use the instructor-approved domain strategy. The Student Project Platform in Week 3 should request TLS through its Ingress rather than manually creating certificates whenever possible.

From `k8s-cp-01`:

```bash
# RUN ON: k8s-cp-01
kubectl -n cert-manager get pods
kubectl -n traefik get pods,svc
kubectl get ingress -A
kubectl get certificate -A
```

If the environment uses external HAProxy/NodePorts for ingress, an empty Kubernetes `LoadBalancer` status is not automatically a failure. Validate the actual traffic path.

---

# Part G — GitOps behavior and drift

## 19. Prove Argo owns the application lifecycle

Make a harmless Git change (for example replica count or test ConfigMap) on a feature branch, merge it to `dev`, and watch Argo reconcile it.

```bash
# RUN ON: k8s-cp-01
kubectl -n argocd get applications
kubectl -n <test-namespace> get deploy,pod,configmap
```

Then deliberately create a small temporary drift only if instructed, observe Argo detect/self-heal it, and document what happened.

The rule for the rest of the course is:

> `kubectl` is for inspection, diagnosis and bounded tests. Desired application state lives in Git.

---

# Week-2 acceptance gate

| Gate | Required proof |
| --- | --- |
| Runtime | containerd active + `crictl info` works on all K8s nodes |
| kubeadm | API `/readyz` healthy through stable HAProxy endpoint |
| Nodes | CP + two workers registered |
| Cilium | all nodes Ready + connectivity test passes |
| Argo | root app follows this repo/`dev` and controller healthy |
| Sealed Secrets | controller healthy; workstation has public cert only |
| Cinder | real PVC write/recreate/read persistence test |
| Ingress | Traefik/cert-manager baseline reachable through approved path |
| GitOps | a Git change produces the intended cluster reconciliation |
| PR | Week-2 changes reviewed and merged into `dev` |

Record the versions/Git SHA used. A green dashboard is not a substitute for the tests above.
