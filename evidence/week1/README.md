# Week 1 evidence

Proof that the five-node platform was built with Terraform, configured with Ansible,
and is reachable over the VPN.

## Files

| File | Shows |
| --- | --- |
| `terraform-plan-nochanges.txt` | A second `terraform plan` finds no changes |
| `openstack-servers.txt` | All five machines are `ACTIVE` |
| `floating-ips.txt` | Only one public IP, on `edge-01` |
| `security-rules.txt` | The cloud firewall rules |
| `inventory-graph.txt` | Ansible sees all five machines |
| `bootstrap-recaps.txt` | The second bootstrap run had `changed=0` |
| `wireguard.txt` | The VPN server is running (public keys only) |
| `vpn-test.txt` | SSH to a private machine over the VPN works |
| `haproxy.txt` | HAProxy is valid and listening on `:6443` |

## Problem we hit

**Floating IP failed to attach.** The first `terraform apply` failed with
`ExternalGatewayForFloatingIPNotFound` because Terraform attached the public IP before the router was connected. We added `depends_on` to the floating IP
attachment in `main.tf` so it always waits for the router. The next apply worked and a second plan showed no changes.

**The Ansible inventory wouldn't parse.** `inventory.yml` had no line break at the end, so the appended `edge_nodes:` line was joined onto the comment above it. We split the line back out and turned on "insert final newline" in VS Code.

**Windows line endings.** Some files were saved with Windows line endings, which add a hidden `\r` character to the end of every line. Linux tools read that `\r` as part of the text, which created errors. We converted the files to Linux line endings, set `git config --global core.autocrlf input`, and set VS Code to save new files with LF.