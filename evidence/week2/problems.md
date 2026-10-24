# Week 2: problems we ran into

Short notes on what broke, why, and how we fixed it. Useful for the Week 6 rebuild and the paper.

---

## The cloud was wiped

Our VMs on the old Sebowa cloud were deleted by mistake. We rebuilt everything on
`pta.sebowa.nicis.ac.za` from the repo. It worked, but a few things needed changing: new
credentials, new flavor names (e.g. `C4.small`), a new public IP (`154.114.52.124`), and
`enable_bootstrap_ssh` set back to `true` for the first login.

## Ansible cut its own connection

Restarting SSH on all machines at once broke the connections that hop through `edge-01`.
Fix: restart the two machines that missed it by hand. Prevention: `throttle: 1` on the
restart handler, so machines restart one at a time.

## Cilium couldn't connect

Cilium's tests were blocked by our firewall. Nodes couldn't ping each other (ping was only allowed
from the management network) and NodePorts were closed. Fix: allowed ping and ports 30000–32767
between the Kubernetes nodes.

## kubectl didn't work for team accounts

`kubectl` said `localhost:8080 refused` because only the person who built the cluster had the
admin config file. Fix: copied `/etc/kubernetes/admin.conf` to `~/.kube/config` for each user.

## Argo CD looked stuck

After merging, our apps didn't appear and the root app showed `Unknown`. Nothing was broken:
Argo CD only checks GitHub every few minutes. Fix: wait, or force a refresh with
`kubectl -n argocd annotate application root argocd.argoproj.io/refresh=hard --overwrite`.

## Storage test stuck on Pending

The test PVC said `no storage class is set`, because Cinder wasn't deployed yet. Two more
problems behind it: the sealed OpenStack credential was still on an unmerged branch, and its name
(`cloud-config`) didn't match what the Cinder app expected (`cinder-csi-cloud-config`).
Fix: merged the secret and pointed the app at `cloud-config`.

## Traefik unreachable from HAProxy

Three problems in a row:

1. **Wrong chart version.** `1.0.1` doesn't exist. We pinned `41.5.0`.
2. **hostPorts didn't open.** With our Cilium setup (kube-proxy kept), `hostPort` doesn't create
   real open ports. We switched to fixed NodePorts (30080 / 30443) and pointed HAProxy at them.
3. **Service type ignored.** Chart 41.x reads it from `service.spec.type`, not `service.type`.

Proved with `curl -k -I https://10.151.0.100/` returning `HTTP/2 404` from Traefik.