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
