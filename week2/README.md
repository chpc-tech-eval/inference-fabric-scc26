# Week 2 — Kubernetes Substrate & GitOps

Week 2 turns the verified Linux VMs into a small Kubernetes platform and then moves persistent application management into GitOps.

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


## The most important boundary this week

```text
WORKSTATION
  Ansible + Git + kubeseal
      │
      ├── bootstrap/configure hosts
      └── push desired state

k8s-cp-01
  kubectl + Cilium CLI + bootstrap diagnostics
      │
      ▼
Kubernetes
  Argo CD reconciles Git
```

**Do not install/use local `kubectl` for this project.** The kubeconfig/admin context stays on `k8s-cp-01`.

## Checklist

- [ ] Bootstrap one control plane and two workers using the provided automation.
- [ ] Validate Kubernetes readiness from `k8s-cp-01`.
- [ ] Install/validate Cilium networking.
- [ ] Install/validate OpenStack Cinder CSI and a dynamic PVC.
- [ ] Bootstrap Argo CD in-cluster.
- [ ] Point an Argo root/application at this team's repository `gitops/` path.
- [ ] Install Sealed Secrets; export only its **public certificate** for workstation `kubeseal` use.
- [ ] Deploy a small application through Git → Argo, not by maintaining imperative YAML manually.
- [ ] Establish Traefik/cert-manager/TLS as provided for the student environment.
- [ ] Merge the validated Week-2 PR into `dev`.

## 1. Bootstrap Kubernetes with Ansible

Host preparation/bootstrap begins from the workstation:

```bash
# RUN ON: WORKSTATION
cd infrastructure/ansible
ansible-playbook -i inventories/private/hosts.yml playbooks/kubernetes-prereqs.yml
ansible-playbook -i inventories/private/hosts.yml playbooks/kubernetes.yml
```

The exact split may change as the scaffold improves. The important point is that Ansible remains the host/bootstrap automation layer.

## 2. Kubernetes administration begins on `k8s-cp-01`

```bash
# RUN ON: WORKSTATION
ssh <k8s-cp-01>
```

Then:

```bash
# RUN ON: k8s-cp-01
kubectl get nodes -o wide
kubectl get pods -A
kubectl get --raw='/readyz?verbose'
```

Expected topology:

```text
k8s-cp-01       Ready   control-plane
k8s-worker-01   Ready
k8s-worker-02   Ready
```

`kubectl get nodes` is not the final acceptance test. It proves registration/readiness at one level only.

## 3. Cilium

Cilium supplies pod networking and network-policy capability.

```bash
# RUN ON: k8s-cp-01
cilium status --wait
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
```

Run the connectivity test if it is part of the supplied baseline:

```bash
# RUN ON: k8s-cp-01
cilium connectivity test
```

If Cilium is unhealthy, investigate before deploying more applications. Cloud security-group mistakes can look like CNI failures.

## 4. Cinder CSI and persistent storage

Cinder CSI allows Kubernetes PVCs to become OpenStack block volumes.

```bash
# RUN ON: k8s-cp-01
kubectl get storageclass
kubectl get pods -A | grep -i cinder
```

Create a small PVC test manifest in **Git** under an appropriate test/evidence path. After review/temporary apply for the storage exercise, prove:

- claim becomes `Bound`;
- a pod can write data;
- deleting/recreating the pod preserves that data;
- you can identify the corresponding OpenStack volume.

Inspect with:

```bash
# RUN ON: k8s-cp-01
kubectl get pvc -A
kubectl get pv
```

Use the workstation only for cloud-side confirmation:

```bash
# RUN ON: WORKSTATION
openstack volume list
```

## 5. Bootstrap Argo CD, then let Git take over

The first Argo installation/root application is a bootstrap operation performed from `k8s-cp-01`. After that, long-lived application state should come from this repository.

```bash
# RUN ON: k8s-cp-01
kubectl -n argocd get pods
kubectl -n argocd get applications
```

The normal steady-state workflow is:

```text
WORKSTATION: edit/commit/push
          ↓
GITHUB: reviewed desired state
          ↓
ARGO CD IN KUBERNETES
          ↓
cluster reconciles
```

Use `kubectl` to inspect/test/diagnose. Repair permanent state in Git rather than `kubectl edit`.

## 6. One GitOps repository: this one

Argo does not need a separate student repository. Use:

```text
gitops/
├── bootstrap/
│   └── root-application.yaml
├── applications/
└── resources/
```

The root application can point back to this repository and discover/reconcile the app definitions beneath `gitops/`.

## 7. Sealed Secrets: `kubeseal` stays on the workstation

The controller's **private sealing key stays inside Kubernetes**. Students need only its public certificate locally.

Export the public cert using the instructor-approved method from the cluster and copy only that public file to your workstation.

Then create the temporary plaintext Secret manifest locally (outside Git), seal it with the public certificate, and delete the plaintext file.

```bash
# RUN ON: WORKSTATION
kubeseal   --cert team-sealed-secrets-public.pem   --format yaml   < /private/path/example-secret.yaml   > gitops/resources/example/example-secret-sealed.yaml
```

Only the encrypted `SealedSecret` belongs in Git.

Conceptually:

```text
plaintext secret (workstation, temporary)
          ↓ kubeseal + public cert
encrypted SealedSecret (safe to review/commit)
          ↓ GitHub / Argo
cluster controller + private key
          ↓
Kubernetes Secret
```

Never copy the controller's private key to a workstation.

## 8. Traefik, DNS and TLS

The student platform eventually needs browser-facing routes. Keep the concepts separate:

```text
DNS        → name resolves to the intended access endpoint
Traefik    → routes HTTP(S) to Kubernetes Services
cert-manager / issuer → obtains/manages certificates
TLS Secret → certificate material consumed by ingress
```

Validation happens from the cluster and a browser/client path—not simply because an Ingress object exists.

```bash
# RUN ON: k8s-cp-01
kubectl get ingress -A
kubectl get certificate -A || true
kubectl get pods -A | grep -E 'traefik|cert-manager'
```

## 9. GitOps smoke application

Create a very small test workload under `gitops/resources/smoke/` and an Argo application for it. Push the change through a feature branch/PR into `dev`, then let Argo reconcile it.

Acceptance evidence should show:

```bash
# RUN ON: k8s-cp-01
kubectl -n argocd get applications
kubectl -n <smoke-namespace> get deploy,pod,svc
```

Do not manually fix the deployment after Argo owns it. Change Git and observe reconciliation.

## Troubleshooting commands

```bash
# RUN ON: k8s-cp-01
kubectl get events -A --sort-by=.lastTimestamp | tail -n 50
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace>
kubectl get endpoints -A
kubectl -n argocd get applications
```

Ask which layer owns the failure before changing things: OpenStack SG? host? Kubernetes API? CNI? CSI? Git? Argo? ingress?

## Exit gate

```text
[k8s-cp-01] 1 control plane + 2 workers Ready
[k8s-cp-01] Cilium healthy/connectivity validated
[k8s-cp-01] dynamic Cinder PVC proven
[k8s-cp-01] Argo CD running and watching this repository
[WORKSTATION] kubeseal works using public controller certificate only
[GitHub]      smoke app deployed by GitOps from a reviewed PR
[cluster]     ingress/TLS baseline validated for the supplied environment
```

Week 3 assumes these platform services are dependable.
