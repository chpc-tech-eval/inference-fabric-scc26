Week 1: OpenStack → Terraform → Ansible
===========================================

This week takes you from an **empty Sebowa OpenStack project** to a small, reproducible set of Linux virtual machines that can be configured automatically.

The objective is not to memorise Terraform or Ansible syntax. The objective is to understand the ownership chain:

```text
OpenStack provides the cloud
        ↓
Terraform declares which cloud resources should exist
        ↓
Ansible configures the operating systems and host services
        ↓
Week 2 can safely build Kubernetes on top
```

> [!IMPORTANT]
> The public `infra-hpc-qc-k8s` repository documents a larger reference platform. **Do not apply its full production-style Terraform environment unchanged.** Your team is building the reduced five-node POC described below, using the same modules, patterns and lessons.

# Checklist

Use this checklist throughout the week. A box is complete only when **every team member can explain what was done and why**.

- [ ] Confirm the correct Sebowa OpenStack project and quota.
- [ ] Generate/use SSH keys safely; private keys never enter Git.
- [ ] Explain the difference between an OpenStack network, subnet, router, port, security group and floating IP.
- [ ] Decide your team's private management and Kubernetes CIDRs without overlapping instructor-provided ranges.
- [ ] Decide the five VM roles and choose suitable available OpenStack flavors.
- [ ] Install and authenticate the OpenStack CLI.
- [ ] Run `openstack token issue` successfully.
- [ ] Clone and inspect `nyameko/infra-hpc-qc-k8s`.
- [ ] Build a **student-sized** Terraform environment from the upstream patterns.
- [ ] Run `terraform fmt`, `terraform validate`, `terraform plan` and review the plan before applying it.
- [ ] Create the five VMs from Terraform.
- [ ] Confirm only the intended edge/recovery path is externally reachable.
- [ ] Build a private Ansible inventory for the five hosts.
- [ ] Run Ansible connectivity checks and base bootstrap.
- [ ] Configure the API load balancer host with HAProxy.
- [ ] Record evidence of the final VM/network state.

# Target POC

Your team designs the final details, but this is the expected starting point:

| Role | vCPU | RAM | Root storage | Main purpose |
| --- | ---: | ---: | ---: | --- |
| `edge-01` | 4 | 10 GiB | 50 GiB | WireGuard, DNS/Pi-hole, nftables, Wazuh Manager, Suricata |
| `api-lb-01` | 2 | 4 GiB | 25 GiB | HAProxy and stable Kubernetes API endpoint |
| `k8s-cp-01` | 4 | 8 GiB | 30 GiB | Kubernetes control plane |
| `k8s-worker-01` | 8 | 16 GiB | 40 GiB | platform/workbench/project workloads |
| `k8s-worker-02` | 8 | 16 GiB | 40 GiB | platform/workbench/project workloads |
| **Total** | **26** | **54 GiB** | **185 GiB** | normal POC footprint |

The figures are a design target, not a reason to ignore the actual flavors and quotas available in your project.

## Logical topology

```text
                              Your workstation
                                    │
                                    │ WireGuard / SSH
                                    ▼
                              ┌───────────┐
                              │  edge-01  │
                              │ VPN / DNS │
                              │ security  │
                              └─────┬─────┘
                                    │
                  ┌─────────────────┴──────────────────┐
                  │                                    │
                  ▼                                    ▼
            ┌───────────┐                       ┌─────────────┐
            │ api-lb-01 │                       │ Kubernetes  │
            │  HAProxy  │                       │   cluster   │
            └─────┬─────┘                       └──────┬──────┘
                  │                                    │
                  │ :6443                       ┌──────┴──────┐
                  └────────────────────────────►│ k8s-cp-01  │
                                               └──────┬──────┘
                                                      │
                                             ┌────────┴────────┐
                                             ▼                 ▼
                                      ┌─────────────┐   ┌─────────────┐
                                      │k8s-worker-01│   │k8s-worker-02│
                                      └─────────────┘   └─────────────┘
```


A sensible cloud network layout is:

```text
Internet / provider network
          │
       router
      ┌───┴──────────────────────┐
      │                          │
management subnet          Kubernetes subnet
      │                          │
  edge-01                  api-lb-01
                           k8s-cp-01
                           k8s-worker-01
                           k8s-worker-02
```

The exact CIDRs, fixed addresses, provider IDs and credentials are **environment data**. Do not publish them merely because the source repository is public.

# 1. Before you automate: understand OpenStack

OpenStack is the Infrastructure-as-a-Service layer. In this project you will use several concepts repeatedly:

| Concept | Plain-language meaning |
| --- | --- |
| Project | Your team's isolated cloud workspace and quota boundary |
| Image | Operating-system template used to create a VM |
| Flavor | A predefined amount of vCPU and RAM |
| Network | A Layer-2 virtual network |
| Subnet | IP address range and gateway/DHCP information inside a network |
| Router | Routes between your private networks and the provider/external network |
| Port | A virtual network interface attached to a VM/service |
| Security group | Cloud firewall policy applied to ports/instances |
| Floating IP | Provider-routable address associated with a private port |
| Volume | Persistent block storage, supplied later to VMs or Kubernetes through Cinder |

> [!NOTE]
> A security group and a host firewall are **not the same thing**. OpenStack security groups filter traffic before it reaches the guest VM. `nftables` is configured inside the Linux guest. The reference design uses both on the edge host for defence in depth.

## Verify your workspace

Use Horizon to confirm that you are in the correct project, then install/use the OpenStack CLI with the credentials provided by the instructor.

Useful first commands:

```bash
openstack token issue
openstack quota show
openstack network list
openstack subnet list
openstack router list
openstack image list
openstack flavor list
openstack server list
openstack volume list
```

Save the output you need for your architecture notes, but **do not paste credentials, application-credential secrets or private keys into GitHub**.

# 2. Prepare a clean working directory

A simple layout on your workstation is:

```bash
mkdir -p ~/scc26
cd ~/scc26

git clone https://github.com/chpc-tech-eval/inference-fabric-scc26.git
git clone https://github.com/nyameko/infra-hpc-qc-k8s.git
```

Record the upstream baseline you are working from:

```bash
cd ~/scc26/infra-hpc-qc-k8s
git status
git rev-parse HEAD
```

When the instructor announces a tested weekly baseline, use that baseline consistently across the team. Do not silently update one member's environment in the middle of debugging and then compare it with another member's older checkout.

# 3. Credentials and secrets

Terraform and the OpenStack CLI need credentials. Ansible may later need vaulted or local-only values. Keep these outside the public repository.

Typical safe locations include:

```text
~/.config/openstack/clouds.yaml
private tfvars outside Git
ansible/inventories/private/
Ansible Vault files
local temporary Secret JSON used only as input to kubeseal
```

Protect local credentials:

```bash
chmod 600 ~/.config/openstack/clouds.yaml
```

Check your project repository before every push:

```bash
git status
git diff --cached
```

> [!CAUTION]
> Never commit OpenStack passwords/application credentials, private SSH keys, WireGuard private keys, kubeconfigs, unsealed Kubernetes Secrets, model API keys, Discord bot tokens or database passwords.

# 4. Terraform: describe the cloud resources

Terraform answers the question:

> **What OpenStack infrastructure should exist?**

The upstream repository separates reusable modules from environment-specific values. Start by studying:

```text
infra-hpc-qc-k8s/
└── terraform/
    ├── modules/
    │   ├── network/
    │   ├── security/
    │   ├── compute/
    │   └── api_lb/
    └── environments/
        └── template/
```

The `template` environment is deliberately larger than your five-node POC. Use it as a **reference**, then remove roles that you do not need for Weeks 1–4:

```text
KEEP
  edge
  api-lb
  k8s-cp-01
  k8s-worker-01
  k8s-worker-02

DO NOT CREATE FOR THE COMMON POC
  dedicated Hermes VM
  Slurm controller
  Slurm login nodes
  Slurm compute nodes
  extra Kubernetes control planes
  extra Kubernetes worker pools
  dedicated research NFS server
```

For a single-control-plane POC, the HAProxy Kubernetes API backend must point only at `k8s-cp-01`.

Your team should be able to explain **why** the public reference topology is larger: it is teaching/research infrastructure with additional schedulers, storage roles and higher-availability options; your student environment preserves the architecture while reducing scale.

## Terraform workflow

From your student environment directory:

```bash
terraform init
terraform fmt -recursive
terraform validate
terraform plan
```

Read the plan. Do not treat `Plan: 12 to add` as a magic success string. Ask:

- Are the expected networks/subnets present?
- Is there exactly one router?
- Are there exactly five intended VMs?
- Are flavors correct?
- Are security groups attached to the right roles?
- Is a floating IP exposed only where required?
- Is the API load-balancer address on the Kubernetes network?
- Are there accidental deletes/replacements?

Only then:

```bash
terraform apply
```

After apply:

```bash
openstack server list
openstack network list
openstack port list
openstack security group list
```

## Terraform state

Terraform state records what Terraform believes it owns. It can contain sensitive infrastructure metadata.

Rules for this project:

1. Do not casually delete the state file to "fix" Terraform.
2. Do not commit private local state unless the instructor has explicitly configured a protected remote backend.
3. Review a plan before every apply.
4. If Terraform wants to destroy something unexpected, stop and investigate.

# 5. Build the Ansible inventory

Ansible answers a different question:

> **How should the Linux hosts be configured?**

Terraform creates a VM; Ansible turns it into a useful role.

Use the upstream `ansible/inventories/example-slurm-hosts.yml` and role/playbook structure as examples, but create a **private student inventory** for your five nodes.

At minimum your inventory needs logical groups equivalent to:

```yaml
all:
  children:
    edge_nodes:
      hosts:
        edge-01:
          ansible_host: <EDGE_ADDRESS>

    api_lb:
      hosts:
        api-lb-01:
          ansible_host: <API_LB_ADDRESS>

    control_plane:
      hosts:
        k8s-cp-01:
          ansible_host: <K8S_CP_ADDRESS>

    workers:
      hosts:
        k8s-worker-01:
          ansible_host: <WORKER_1_ADDRESS>
        k8s-worker-02:
          ansible_host: <WORKER_2_ADDRESS>
```

Your actual variables will also include the SSH user, private addresses, API endpoint and platform-specific settings.

Inspect the resulting inventory:

```bash
cd ~/scc26/infra-hpc-qc-k8s/ansible
ansible-inventory -i inventories/private/hosts.yml --graph
ansible all -i inventories/private/hosts.yml -m ping
```

If `ping` fails, debug SSH/networking before running a large playbook.

# 6. Bootstrap the hosts

The upstream bootstrap playbook configures the common operating-system foundation:

```bash
ansible-playbook \
  -i inventories/private/hosts.yml \
  playbooks/bootstrap.yml
```

Then validate basic Linux health:

```bash
ansible all -i inventories/private/hosts.yml -m command -a 'hostname'
ansible all -i inventories/private/hosts.yml -m command -a 'uname -r'
ansible all -i inventories/private/hosts.yml -m command -a 'timedatectl show -p NTPSynchronized --value'
```

The reference bootstrap also installs Wazuh agent components. Full security-plane validation belongs in Week 3; this week only confirm that the base host configuration is repeatable.

# 7. Configure the API load balancer

The Kubernetes API should have a stable endpoint even though your POC has only one control plane.

```text
kubectl / kubeadm / clients
          │
          ▼
     api-lb-01:6443
          │
          ▼
     k8s-cp-01:6443
```

Configure the HAProxy host from Ansible:

```bash
ansible-playbook \
  -i inventories/private/hosts.yml \
  playbooks/api-lb.yml
```

On `api-lb-01`, verify HAProxy configuration and service state using the methods configured by the role, for example:

```bash
sudo systemctl status haproxy --no-pager
sudo ss -lntp | grep 6443
```

At this point the backend Kubernetes API does not exist yet, so an end-to-end API health check is a **Week 2** gate. This week you are proving that the stable front door exists and is configured correctly.

# 8. Edge node: minimum Week 1 state

The final edge role will provide WireGuard, Pi-hole/DNS, nftables, Wazuh Manager and Suricata. Do not try to investigate every security product in Week 1.

For the Week 1 gate, prioritise:

- known SSH/recovery access;
- correct routing;
- WireGuard/private-administration path if the instructor has supplied peer data;
- correct resolver/DNS design;
- validated nftables syntax before loading rules;
- documented security-group policy.

The complete Wazuh/Suricata evidence path is intentionally delayed until Week 3.

# Success state

By the end of Week 1 you should be able to draw your own environment and prove that it can be recreated from code.

Required evidence:

```text
✓ correct OpenStack project and quota recorded
✓ five intended VMs ACTIVE
✓ network/subnet/router/security-group design documented
✓ only intended external access exposed
✓ terraform fmt/validate pass
✓ reviewed terraform plan retained in notes or CI artifact
✓ terraform apply succeeds
✓ Ansible inventory graph is correct
✓ ansible all -m ping succeeds
✓ bootstrap is repeatable
✓ HAProxy service is installed/configured on api-lb-01
✓ no secrets committed to Git
```

# Troubleshooting order

When something fails, debug from the bottom up:

```text
OpenStack resource exists?
        ↓
port / fixed address correct?
        ↓
route correct?
        ↓
security group permits the path?
        ↓
SSH reachable?
        ↓
Linux service running?
        ↓
Ansible variables correct?
        ↓
application behavior
```

Useful commands:

```bash
openstack server show <server>
openstack port list --server <server>
openstack security group rule list <group>
ip addr
ip route
ss -lntup
systemctl --failed
journalctl -b -p warning
```

Do not destroy/recreate an environment as your first debugging step. You learn far more by identifying which layer is wrong.

# Deliverable

Commit a short Week 1 record to your project repository containing:

- architecture diagram;
- VM/resource table;
- logical network design;
- Terraform validation/apply evidence;
- Ansible inventory/connection evidence;
- one meaningful failure you encountered and how you diagnosed it;
- the exact upstream commit SHA(s) you used.

Do **not** commit private environment values.

# Next week

Week 2 turns these five Linux VMs into a Kubernetes platform with Cilium networking, Cinder persistent storage, Argo CD, Sealed Secrets and Traefik ingress.
