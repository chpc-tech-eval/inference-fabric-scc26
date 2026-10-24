# Week 2 evidence: Kubernetes, Cilium, storage and GitOps

Each file below is the raw command output that proves one Week 2 check.
Status: ⬜ not yet · 🟡 received, needs checking · ✅ verified

## Environment

| Item | Value |
| --- | --- |
| Git commit (dev) | `<git rev-parse --short origin/dev>` |
| Kubernetes | 1.36.4 |
| containerd | 2.3.4 |
| Cilium | 1.20.1 (kube-proxy kept) |
| Argo CD | v3.5.0 |
| Sealed Secrets | v0.39.1 |
| Pod network | 10.244.0.0/16 |
| API endpoint | 10.151.0.100:6443 (HAProxy on api-lb-01) |

## Evidence index

| File | Shows | From | Status |
| --- | --- | --- | --- |
| `security-rules.txt` | the Kubernetes firewall rules | Infrastructure | ⬜ |
| `haproxy-api.txt` | API healthy through HAProxy; backend UP | Infrastructure | ⬜ |
| `containerd.txt` | containerd active on all three k8s nodes | Cloud automation | ⬜ |
| `nodes.txt` | three nodes `Ready` | Cloud automation | ⬜ |
| `cilium-status.txt` | Cilium healthy; connectivity test passed | Cloud automation | ⬜ |
| `argocd.txt` | Argo CD apps `Synced` / `Healthy` | CI/CD & security | ⬜ |
| `sealed-secrets.txt` | controller running; only the sealed Cinder secret in Git | CI/CD & security | ⬜ |
| `ingress.txt` | Traefik reachable via VPN → HAProxy → workers | Infrastructure + CI/CD | ⬜ |
| `persistence-test.txt` | the marker survived a pod replacement | Frontend & project | ✅ |
| `gitops-test.txt` | a Git change reached the cluster (with PR link) | Frontend & project | ⬜ |
| `versions.txt` | the versions actually running | Cloud automation | ⬜ |

## How to produce each file

Run on **k8s-cp-01** unless marked otherwise. Paste the command *and* its output.

| File | Command(s) |
| --- | --- |
| `security-rules.txt` | (workstation, operator) `terraform -chdir=infrastructure/terraform output security_rules` |
| `haproxy-api.txt` | `curl -sk https://10.151.0.100:6443/healthz; echo` → `ok`; then `curl -s "http://10.151.0.100:8404/stats;csv" \| grep control-plane` → `UP` |
| `containerd.txt` | on each of k8s-cp-01, k8s-worker-01, k8s-worker-02: `systemctl is-active containerd` and `sudo crictl info \| head -20` |
| `nodes.txt` | `kubectl get nodes -o wide` |
| `cilium-status.txt` | `cilium status`, plus the final summary lines of `cilium connectivity test` |
| `argocd.txt` | `kubectl -n argocd get applications` |
| `sealed-secrets.txt` | `kubectl get pods -A \| grep sealed-secrets`; `kubectl get sealedsecrets -A` |
| `ingress.txt` | (workstation, VPN on) `curl -sI http://10.151.0.100/`, plus Traefik pods: `kubectl get pods -A \| grep traefik` |
| `persistence-test.txt` | see role guide, Task 3 |
| `gitops-test.txt` | see role guide, Task 4 |
| `versions.txt` | `kubectl version`; `kubeadm version -o short`; `cilium version`; `containerd --version` |

## Rules for evidence

- Never paste private keys, passwords, tokens, kubeconfig files or unsealed secrets.
- Replace the edge public IP with `<edge-public-ip>`.
- Start each file with: date, who ran it, and which machine.

## Design decisions

- `storage-test` uses a **bare Pod** (not a Deployment) so it keeps the name
  `persistence-test` when Argo CD recreates it.
- Both test Applications have **selfHeal on** and `CreateNamespace=true`.
  Without selfHeal on `storage-test`, Argo CD would not recreate the deleted pod.
- `gitops-test` mounts the ConfigMap **as a file** (`index.html`), so a Git change
  also appears on the web page without restarting the pod.

## Problems we hit

Copy this block for each problem.

### <short title>

- **Who / when:** <role>, <date>
- **Symptom:** <what we saw, with the error message>
- **Cause:** <why it happened>
- **Fix:** <what we changed; link the commit or PR>
- **Lesson:** <what we'd do differently>
