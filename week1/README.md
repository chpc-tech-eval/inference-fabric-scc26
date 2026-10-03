# Week 1 — OpenStack → Terraform → Ansible

Week 1 takes your team from an empty Sebowa project to a reproducible five-node Linux environment. The goal is not merely to create five VMs. You must understand **what OpenStack owns, what Terraform owns, what Ansible owns, what is secret, what is reproducible, and how to prove each layer independently**.

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

## What you should understand by Friday

By the end of the week every team member should be able to explain this chain without notes:

```text
OpenStack project / quota
        ↓
Neutron networks, router, ports and security groups
        ↓
Nova instances + Cinder-backed storage where configured
        ↓
Terraform state and desired infrastructure
        ↓
SSH reachability through the edge/bastion path
        ↓
Ansible inventory
        ↓
Rocky Linux host convergence
        ↓
edge networking services + HAProxy API endpoint
```

A VM showing `ACTIVE` in OpenStack is **not** proof that Linux is reachable. An Ansible play ending without failure is **not** proof that a service is reachable through the intended network path. Each layer has its own acceptance test.

## Reference architecture for the student POC

| Host | vCPU | RAM | Root storage | Primary role |
| --- | ---: | ---: | ---: | --- |
| `edge-01` | 4 | 10 GiB | 50 GiB | bastion/VPN, DNS, host firewall; security services added in Week 3 |
| `api-lb-01` | 2 | 4 GiB | 25 GiB | stable Kubernetes API endpoint using HAProxy |
| `k8s-cp-01` | 4 | 8 GiB | 30 GiB | single control plane and cluster-admin host |
| `k8s-worker-01` | 8 | 16 GiB | 40 GiB | platform/project workloads |
| `k8s-worker-02` | 8 | 16 GiB | 40 GiB | platform/project workloads |

This is a **student-sized derivative** of `infra-hpc-qc-k8s`. Do not provision the upstream production/reference topology unchanged: it contains additional control planes, Slurm nodes, storage, login hosts and agent roles that are intentionally outside this six-week baseline.

## Deployment order

Do the work in this order. Do not skip forward because a later command looks more exciting.

```text
0. Git branch and local-secret hygiene
1. Prove OpenStack authentication
2. Discover project quota/provider resources
3. Review the team's network and trust model
4. Terraform init/fmt/validate
5. Terraform plan and peer review
6. Terraform apply
7. Verify OpenStack resources independently of Terraform
8. Prove SSH to edge
9. Validate Ansible inventory and bastion routing
10. Base host bootstrap
11. Configure edge access/DNS/firewall
12. Prove WireGuard/private recovery path
13. Configure HAProxy
14. Re-run/idempotence checks
15. Open the Week-1 PR into dev
```

---

# Part A — Git and workstation preparation

## 0.1 Start from `dev`, not `main`

`main` is the protected release branch. `dev` is the protected integration branch. Normal student work starts from `dev`.

```bash
# RUN ON: WORKSTATION
git switch dev
git pull --ff-only
git switch -c feature/week1-foundation
```

Before committing anything, check:

```bash
# RUN ON: WORKSTATION
git status
git branch --show-current
```

Do not work directly on `main` or `dev`.

## 0.2 Verify the small workstation toolset

```bash
# RUN ON: WORKSTATION
git --version
ssh -V
openstack --version
terraform version
ansible --version
kubeseal --version
```

For the current instructor reference implementation, Terraform is `>=1.9` and the OpenStack provider is pinned to `3.4.0`. Your student scaffold should also pin versions rather than silently accepting any future provider release.

You do **not** need local `kubectl`, Helm or an Argo CD CLI.

## 0.3 Create private local directories

Use a private path outside the repository for credentials and generated secret material.

```bash
# RUN ON: WORKSTATION
mkdir -p ~/.config/openstack ~/.config/scc26-secrets
chmod 700 ~/.config/openstack ~/.config/scc26-secrets
```

Your repository `.gitignore` should exclude at least:

```text
*.tfstate
*.tfstate.*
.terraform/
terraform.tfvars
*.auto.tfvars
clouds.yaml
*.pem
*.key
*.crt.private
secrets-private/
```

A public **certificate** may be committed if the project deliberately chooses to do so; private keys and credentials may not.

---

# Part B — OpenStack: understand the cloud before Terraform changes it

## 1. Authenticate

The instructor/provider may give you either a `clouds.yaml`, an application credential, or an OpenStack RC file. Store it outside Git.

If using `clouds.yaml`:

```bash
# RUN ON: WORKSTATION
export OS_CLOUD=<team-cloud-name>
openstack token issue
```

If using an RC file, source it into the current shell only:

```bash
# RUN ON: WORKSTATION
source /private/path/team-openrc.sh
openstack token issue
```

**Stop here if `openstack token issue` fails.** Terraform will not repair broken cloud authentication.

## 2. Identify your project and quota

```bash
# RUN ON: WORKSTATION
openstack project show <your-project-id-or-name>
openstack quota show
openstack server list
openstack volume list
```

Record a **sanitised** quota summary in your Week-1 evidence. Do not publish tokens, application credential secrets or private endpoint configuration.

Your nominal five-node platform consumes approximately 26 vCPU and 54 GiB RAM before project-specific extras. Confirm you have enough headroom before applying Terraform.

## 3. Discover provider resources instead of guessing them

```bash
# RUN ON: WORKSTATION
openstack image list
openstack flavor list
openstack network list
openstack network list --external
openstack volume type list
openstack keypair list
openstack security group list
```

Write down the exact **IDs/names you are expected to use** in your private Terraform variables.

### Why this matters

A common upstream failure came from confusing a human-readable OpenStack flavor name with the identifier expected by a configuration path. Treat provider objects as data you must inspect, not names you should invent.

## 4. OpenStack concepts you must know

| Object | What it means | Typical owner in this course |
| --- | --- | --- |
| Project | Team isolation and quota boundary | instructor/OpenStack |
| Image | OS template | provider |
| Flavor | vCPU/RAM shape | provider |
| Network | Virtual L2 network | Terraform |
| Subnet | CIDR, gateway and DHCP on a network | Terraform |
| Router | Connects private networks/provider network | Terraform |
| Port | Virtual NIC | Terraform/Nova |
| Security group | Cloud firewall enforced before guest OS | Terraform |
| Floating IP | Provider-routable IP mapped to private port | Terraform |
| Cinder volume | Persistent block storage | Terraform/CSI depending layer |

Never confuse an OpenStack security group with `nftables`:

```text
packet
  ↓
OpenStack security group
  ↓
VM virtual NIC
  ↓
Linux nftables
  ↓
service
```

## 5. Draw the Week-1 trust path

Use instructor-assigned, non-overlapping CIDRs and keep real internal values in private environment files.

Conceptually:

```text
Internet / your workstation
        │
   temporary bootstrap SSH
        │
        ▼
     edge-01  ← one floating IP
        │
        ├── management network
        │
        └── routed/private access to Kubernetes network
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
          api-lb-01   k8s-cp-01   workers
```

The target steady-state admin path is WireGuard through `edge-01`; public SSH is a **bootstrap/recovery step**, not the final architecture.

---

# Part C — Terraform: declare the OpenStack infrastructure

## 6. Understand what Terraform owns

Terraform answers:

> **What cloud infrastructure should exist?**

It should own, at minimum, your team networks/subnets/router, cloud-side security groups, five instance/port definitions, one edge floating IP, and any static route required for the VPN return path.

It does **not** install Kubernetes, Wazuh, Prometheus or your Student Project Platform.

Suggested student layout:

```text
infrastructure/terraform/
├── modules/
│   ├── network/
│   ├── security/
│   └── compute/
└── environment/
    ├── providers.tf
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    ├── terraform.tfvars.example
    └── README.md
```

Keep actual `terraform.tfvars` private.

## 7. Initialize and format

```bash
# RUN ON: WORKSTATION
cd infrastructure/terraform/environment
terraform init
terraform fmt -recursive
terraform validate
```

Do not proceed while `validate` is failing.

### What `init` does

`terraform init` initializes the working directory, obtains the pinned provider and prepares the selected state backend. It should not create your VMs.

### What `validate` does not do

Validation proves configuration syntax/schema coherence. It does **not** prove that your quota, image ID, security-group logic or network design are correct.

## 8. Create and review a plan

```bash
# RUN ON: WORKSTATION
terraform plan -out=tfplan
terraform show tfplan
```

Read the plan together before applying it.

You should be able to account for:

- two private networks/subnets (or your documented approved variant);
- one router and required interfaces/routes;
- the intended security groups/rules;
- exactly five student POC hosts;
- one edge floating IP;
- fixed private IPs where the design requires them.

Terraform symbols:

```text
+ create
~ change in place
-/+ replace
- destroy
```

Treat `-/+` as a warning: a resource will be destroyed/recreated.

## 9. Apply the reviewed plan

```bash
# RUN ON: WORKSTATION
terraform apply tfplan
```

Do not run `terraform apply -auto-approve` as the normal teaching workflow. The plan review is part of the exercise.

After apply:

```bash
# RUN ON: WORKSTATION
terraform output
terraform state list
```

Never commit local Terraform state.

## 10. Independently verify OpenStack

Terraform saying “Apply complete” is not your acceptance test.

```bash
# RUN ON: WORKSTATION
openstack server list
openstack port list
openstack floating ip list
openstack security group list
openstack router list
```

For suspicious resources:

```bash
# RUN ON: WORKSTATION
openstack server show <server>
openstack port show <port-id>
openstack security group show <group>
```

Verify expected private addresses, network membership and the single intended public exposure.

## 11. Run a no-change plan

```bash
# RUN ON: WORKSTATION
terraform plan
```

After a stable apply, the desired result is **no infrastructure drift**. If Terraform proposes changes you did not expect, understand them before continuing.

---

# Part D — First access and Ansible inventory

## 12. Prove the edge is reachable

```bash
# RUN ON: WORKSTATION
ssh <bootstrap-user>@<edge-floating-ip>
```

On the edge:

```bash
# RUN ON: edge-01
hostnamectl
ip -brief address
ip route
chronyc tracking || true
```

If the VM is `ACTIVE` but SSH times out, investigate the path in order:

```text
floating IP association
→ security group
→ guest NIC/routing
→ guest firewall
→ sshd
```

Do not randomly disable SELinux/firewalls.

## 13. Build the private Ansible inventory

Keep the real inventory in a private path excluded from Git; commit only an example/template.

A simple pattern is:

```yaml
all:
  vars:
    ansible_user: <bootstrap-or-admin-user>
  children:
    edge_nodes:
      hosts:
        edge-01:
          ansible_host: <edge-floating-ip>
    api_lb:
      hosts:
        api-lb-01:
          ansible_host: <api-lb-private-ip>
    control_plane:
      hosts:
        k8s-cp-01:
          ansible_host: <cp-private-ip>
    workers:
      hosts:
        k8s-worker-01:
          ansible_host: <worker1-private-ip>
        k8s-worker-02:
          ansible_host: <worker2-private-ip>
```

For private hosts, use SSH `ProxyJump`/Ansible SSH common args through `edge-01` during bootstrap. Once WireGuard is established, your workstation can route directly to the private team networks through the VPN and the inventory can be simplified.

## 14. Inspect what Ansible actually sees

```bash
# RUN ON: WORKSTATION
cd infrastructure/ansible
ansible-inventory -i inventories/private/hosts.yml --graph
ansible-inventory -i inventories/private/hosts.yml --host edge-01
ansible-inventory -i inventories/private/hosts.yml --host k8s-cp-01
```

This is important: **a YAML variable existing on disk does not prove Ansible resolved it for a host**.

## 15. Connectivity test

```bash
# RUN ON: WORKSTATION
ansible all -i inventories/private/hosts.yml -m ping
```

Fix unreachable hosts before applying roles.

---

# Part E — Ansible: converge the operating systems

## 16. Understand Ansible's ownership

Ansible answers:

> **How should the Linux machines and bootstrap infrastructure services be configured?**

For the student POC it owns things such as common packages, time synchronization, administrator/SSH state, edge host networking services, container runtime/Kubernetes prerequisites in Week 2, and HAProxy.

Long-lived Kubernetes applications later cross the GitOps boundary and belong to Argo CD instead.

## 17. Syntax-check first

```bash
# RUN ON: WORKSTATION
ansible-playbook -i inventories/private/hosts.yml playbooks/bootstrap.yml --syntax-check
ansible-playbook -i inventories/private/hosts.yml playbooks/edge.yml --syntax-check
ansible-playbook -i inventories/private/hosts.yml playbooks/api-lb.yml --syntax-check
```

A syntax check is not a dry-run guarantee, but it catches cheap mistakes before touching hosts.

## 18. Base bootstrap all five hosts

The student `bootstrap.yml` should focus on Week-1 host fundamentals: base packages, time synchronization/timezone, SSH/admin user and required OS settings. Security agents can be introduced deliberately in Week 3.

```bash
# RUN ON: WORKSTATION
ansible-playbook -i inventories/private/hosts.yml playbooks/bootstrap.yml
```

Validate time and basic service state from Ansible:

```bash
# RUN ON: WORKSTATION
ansible all -i inventories/private/hosts.yml -b -m shell \
  -a 'hostname; timedatectl show -p Timezone --value; chronyc tracking | head -n 4'
```

Timezone and clock synchronization are separate things. `Africa/Johannesburg` changes presentation; Chrony keeps the clock correct. Correct timestamps become critical for Week-3 incident correlation.

## 19. Re-run the bootstrap

```bash
# RUN ON: WORKSTATION
ansible-playbook -i inventories/private/hosts.yml playbooks/bootstrap.yml
```

A mature idempotent playbook should trend toward `changed=0` when no desired state has changed. Investigate tasks that report changes every run.

---

# Part F — Edge access/DNS/firewall

## 20. Configure the Week-1 edge subset

Week 1 needs the access path and infrastructure DNS/firewall. Wazuh Manager and Suricata are introduced and validated in Week 3 rather than making Week 1 depend on the full security stack.

```bash
# RUN ON: WORKSTATION
ansible-playbook -i inventories/private/hosts.yml playbooks/edge.yml \
  --tags wireguard,pihole,firewall
```

If your supplied student playbook uses a separate `edge-base.yml`, use that instead. Preserve the conceptual boundary.

## 21. Validate edge services

```bash
# RUN ON: edge-01
sudo wg show
sudo nft list ruleset
sudo ss -lntup
systemctl --no-pager --type=service --state=failed
```

Validate DNS from a private host or via the VPN path:

```bash
# RUN ON: k8s-cp-01 (after private access is available)
getent hosts edge-01
cat /etc/resolv.conf
```

Use explicit registries for system-launched container images; the upstream platform learned this after a non-interactive Podman service could not resolve an ambiguous short image name.

## 22. Prove WireGuard before closing bootstrap SSH

The server private key stays on `edge-01`. The client private key stays on the client. Only public keys are exchanged.

After receiving/generating the approved client configuration:

```bash
# RUN ON: WORKSTATION
sudo wg-quick up <team-interface>
sudo wg show
```

Then test private access:

```bash
# RUN ON: WORKSTATION
ssh <admin-user>@<k8s-cp-private-ip>
ssh <admin-user>@<k8s-worker1-private-ip>
```

Only after the team has a proven VPN/recovery path should Terraform remove/restrict temporary public SSH exposure.

Run a plan, review the security-group change, and apply it through Terraform rather than manually editing security groups in Horizon.

---

# Part G — Stable Kubernetes API load-balancer

## 23. Configure HAProxy

```bash
# RUN ON: WORKSTATION
ansible-playbook -i inventories/private/hosts.yml playbooks/api-lb.yml
```

For the student single-control-plane POC, HAProxy ultimately has one Kubernetes API backend: `k8s-cp-01:6443`. Keeping a stable front-end endpoint still teaches the right abstraction and allows later control-plane expansion without changing every client.

## 24. Validate HAProxy itself

```bash
# RUN ON: api-lb-01
sudo haproxy -c -f /etc/haproxy/haproxy.cfg
sudo systemctl status haproxy --no-pager
sudo ss -lntp | grep ':6443' || true
getenforce
```

Before kubeadm runs in Week 2, the HAProxy **listener can be healthy while its backend is DOWN**. That is expected.

If config validation passes but the process cannot bind, inspect SELinux before disabling it. The upstream deployment required the persistent `haproxy_connect_any` boolean on Rocky/RHEL-family systems.

---

# Part H — Week-1 acceptance ladder

Do not call Week 1 complete until every row passes.

| Layer | Evidence | Expected result |
| --- | --- | --- |
| Git | branch/PR model | work on feature branch from `dev` |
| OpenStack auth | `openstack token issue` | succeeds |
| Quota | `openstack quota show` | enough headroom |
| Terraform | `fmt`, `validate`, reviewed plan | clean |
| Terraform drift | second `terraform plan` | no unexpected changes |
| Nova/Neutron | server/port/router/SG lists | match diagram |
| Public exposure | floating IP list | only intended edge path |
| SSH | edge/private access | works through intended path |
| Ansible inventory | `--graph`, `--host` | correct grouping/vars |
| Ansible convergence | second bootstrap run | no unexplained recurring changes |
| WireGuard | private SSH | works before public SSH removal |
| HAProxy | syntax/service/listener | healthy; backend may be DOWN until Week 2 |
| GitHub | Week-1 PR | reviewed and merged into `dev` |

## Failure isolation table

| Symptom | Check first |
| --- | --- |
| OpenStack CLI 401/403 | credentials/project/role, not Terraform |
| Terraform cannot find flavor/image | provider ID/name and region |
| VM ACTIVE but SSH timeout | FIP → SG → route → nftables → sshd |
| Ansible variable missing | `ansible-inventory --host` |
| HAProxy config valid but service fails | journal + SELinux + bind address/port |
| Private host unreachable after VPN | WireGuard route + OpenStack router return route + SG |

---

# Week-1 evidence and PR

Create a small `evidence/week1/` index or issue/PR checklist pointing to sanitized evidence. Recommended evidence:

- architecture/trust-boundary diagram;
- Terraform provider/version lock and Git SHA;
- sanitised plan summary;
- OpenStack resource summary;
- Ansible inventory graph;
- first and second bootstrap recap;
- WireGuard/private-access proof with secrets omitted;
- HAProxy validation;
- short troubleshooting note for at least one real problem encountered.

Before pushing:

```bash
# RUN ON: WORKSTATION
git status
git diff --check
git diff --cached
```

Never commit `terraform.tfstate`, `clouds.yaml`, RC files, SSH/WireGuard private keys, application credentials or raw secret manifests.

Then:

```bash
# RUN ON: WORKSTATION
git add <reviewed-files>
git commit -m "week1: provision and bootstrap student platform"
git push -u origin feature/week1-foundation
```

Open a PR into **`dev`**.

## Week-1 exit gate

```text
Terraform can rebuild the five-node OpenStack topology.
Ansible can reach and converge all five hosts.
The edge provides a verified private administration path.
HAProxy provides the stable API endpoint and is ready for kubeadm.
The team can explain every boundary above without relying on the instructor to diagnose it.
```

Do not start Kubernetes on an unstable foundation.
