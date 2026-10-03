# Week 1 — OpenStack → Terraform → Ansible

This week takes you from an empty Sebowa project to a reproducible five-node Linux environment. **Everything in the main Week-1 deployment path runs from your workstation**: OpenStack CLI, Terraform and Ansible. You SSH into hosts only for validation/troubleshooting when required.

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


## The ownership chain

```text
OpenStack provides cloud resources
        ↓
Terraform declares what infrastructure should exist
        ↓
Ansible configures the guest operating systems/services
        ↓
Week 2 builds Kubernetes on that verified foundation
```

## Week-1 checklist

- [ ] Confirm your team's correct Sebowa project and quota.
- [ ] Confirm this repository has a protected `main` and an integration `dev` branch.
- [ ] Create your own short-lived working branch from `dev`.
- [ ] Configure OpenStack credentials locally without committing them.
- [ ] Run `openstack token issue` successfully.
- [ ] Explain network, subnet, router, port, security group and floating IP.
- [ ] Review the student-sized Terraform under `infrastructure/terraform/`.
- [ ] Run `terraform fmt`, `validate`, `plan`, peer-review the plan and then apply.
- [ ] Create exactly the intended five-node POC (unless your approved architecture documents a change).
- [ ] Build/use the private Ansible inventory and validate all hosts.
- [ ] Apply base host configuration and HAProxy/edge roles.
- [ ] Prove external exposure is limited to the intended access path.
- [ ] Commit only non-secret desired state/documentation and open a PR into `dev`.

## 1. Prepare the workstation

Required local tools for the programme are deliberately small:

```text
Git
SSH
OpenStack CLI
Terraform
Ansible
kubeseal   (used from Week 2 onward)
```

Do **not** add `kubectl` or the Argo CD CLI to the course workstation tool list. Kubernetes administration belongs on `k8s-cp-01`.

```bash
# RUN ON: WORKSTATION
git --version
terraform version
ansible --version
openstack --version
kubeseal --version
```

## 2. Work only in the team repository

The student-sized Terraform and Ansible needed for this exercise belong in **this repository**. You do not need to clone the full `infra-hpc-qc-k8s` repository to deploy the lab.

Suggested paths:

```text
infrastructure/
├── terraform/
│   ├── modules/
│   └── environment/
└── ansible/
    ├── inventories/
    ├── playbooks/
    └── roles/
```

The larger upstream repository remains useful background reading when you want to understand why the full platform has extra Slurm, storage, HA and worker roles.

## 3. Verify OpenStack access

```bash
# RUN ON: WORKSTATION
openstack token issue
openstack quota show
openstack image list
openstack flavor list
openstack network list
openstack subnet list
openstack router list
openstack server list
openstack volume list
```

Do not paste credential output into GitHub/Discord/screenshots. Record only the non-sensitive information needed for your design.

### OpenStack concepts

| Concept | Meaning |
| --- | --- |
| project | your team's isolated workspace/quota boundary |
| image | OS template used to create a VM |
| flavor | predefined vCPU/RAM allocation |
| network | virtual Layer-2 network |
| subnet | address range/DHCP/gateway within a network |
| router | routes between private and provider networks |
| port | virtual NIC/end point |
| security group | cloud firewall applied to ports/instances |
| floating IP | provider-routable address associated with a private port |
| volume | persistent Cinder block storage |

A security group is **not** the same as `nftables`. The former acts in OpenStack; the latter acts inside the VM.

## 4. Target topology

| Role | vCPU | RAM | Disk | Week-1 responsibility |
| --- | ---: | ---: | ---: | --- |
| `edge-01` | 4 | 10 GiB | 50 GiB | access path, DNS/firewall/security service host |
| `api-lb-01` | 2 | 4 GiB | 25 GiB | HAProxy stable API endpoint |
| `k8s-cp-01` | 4 | 8 GiB | 30 GiB | future Kubernetes control plane |
| `k8s-worker-01` | 8 | 16 GiB | 40 GiB | worker |
| `k8s-worker-02` | 8 | 16 GiB | 40 GiB | worker |

For a single-control-plane POC, HAProxy's Kubernetes API backend ultimately points to `k8s-cp-01` only. The stable endpoint still teaches the correct abstraction and allows the topology to evolve later.

## 5. Terraform workflow

Terraform answers: **what OpenStack resources should exist?**

Before applying, review variables for project-specific image/flavor/network values and ensure secret inputs are ignored by Git.

```bash
# RUN ON: WORKSTATION
cd infrastructure/terraform/environment
terraform init
terraform fmt -recursive
terraform validate
terraform plan
```

Read the plan. Confirm the VM count, network attachments, security groups, router and floating-IP design. Then:

```bash
# RUN ON: WORKSTATION
terraform apply
```

After apply:

```bash
# RUN ON: WORKSTATION
openstack server list
openstack port list
openstack floating ip list
openstack security group list
```

### Terraform acceptance questions

Every team member should be able to answer:

- why Terraform owns these resources rather than Ansible;
- which values are public desired state and which are protected environment data;
- what would happen on a second `terraform plan` with no changes;
- why `terraform destroy` must be deliberate and reviewed;
- why a VM in `ACTIVE` state does not prove its OS/service is healthy.

## 6. Ansible workflow

Ansible answers: **how should these Linux hosts be configured?**

Keep live credentials/private keys outside Git. Commit an example inventory containing semantic placeholders if useful.

```bash
# RUN ON: WORKSTATION
cd infrastructure/ansible
ansible-inventory -i inventories/private/hosts.yml --graph
ansible all -i inventories/private/hosts.yml -m ping
```

Then apply the provided student bootstrap in small steps rather than one giant play if possible:

```bash
# RUN ON: WORKSTATION
ansible-playbook -i inventories/private/hosts.yml playbooks/bootstrap.yml
ansible-playbook -i inventories/private/hosts.yml playbooks/edge.yml
ansible-playbook -i inventories/private/hosts.yml playbooks/api-lb.yml
```

Exact playbook names may differ in the scaffold supplied by the instructor; preserve the ownership boundary even if implementation details change.

## 7. Validate from the correct hosts

Use SSH only where host-level evidence is needed.

```bash
# RUN ON: WORKSTATION
ssh <edge-host>
```

Then on edge:

```bash
# RUN ON: edge-01
hostname
ip -brief address
sudo nft list ruleset
sudo ss -lntup
```

For HAProxy:

```bash
# RUN ON: api-lb-01
sudo haproxy -c -f /etc/haproxy/haproxy.cfg
systemctl status haproxy --no-pager
sudo ss -lntp | grep 6443 || true
```

Do not confuse a syntactically valid HAProxy configuration with a reachable Kubernetes API; Kubernetes does not exist yet.

## 8. Week-1 Git evidence

Work through a PR into `dev` rather than directly changing protected branches.

Your Week-1 PR should contain/point to:

- architecture diagram;
- non-secret Terraform/Ansible desired state;
- `terraform plan` summary or sanitised evidence;
- OpenStack resource list with secrets/internal details redacted as appropriate;
- Ansible convergence evidence;
- known issues/assumptions;
- the exact Git commit accepted for Week 1.

Do not commit Terraform state, `clouds.yaml`, SSH private keys, application credentials, private WireGuard keys or raw secret files.

## Exit gate

Week 1 is complete only when:

```text
[WORKSTATION] terraform plan/apply is understood and reproducible
[WORKSTATION] Ansible reaches/configures all five intended hosts
[OpenStack]   topology/security groups match the documented design
[edge-01]     host firewall/access services validate at the current stage
[api-lb-01]   HAProxy configuration validates
[GitHub]      reviewed Week-1 PR is merged into dev
```

If the infrastructure is unstable, do not rush into Kubernetes. Week 2 assumes Week 1 is real.
