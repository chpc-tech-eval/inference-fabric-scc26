# Week 4 security checklist

Captured: 2026-11-15T19:41:15Z (UTC). Raw output: `security-checklist-capture.txt`.

The agent (the ACP API and the Hermes worker) must hold no powerful keys, expose nothing, and talk only to the services it needs. Each row is a "must NOT have" and how it was checked.

| # | Must NOT have | How it was checked | Observed | Result |
| --- | --- | --- | --- | --- |
| 1 | A Kubernetes token | `automountServiceAccountToken` on every pod; RoleBindings in the namespace; token directory inside the worker pod | `automount=false` on all four pods (API, migration job, Hermes worker, PostgreSQL); no RoleBindings; `/var/run/secrets/kubernetes.io/serviceaccount` does not exist in the worker | Pass |
| 2 | A public route | Ingress and IngressRoute in `agent-control-plane` and `inference` | None in either namespace | Pass |
| 3 | An open model server | An unauthenticated chat request from the worker to `llm-cpu` | HTTP 401 | Pass |
| 4 | Plaintext secrets in Git | `git grep -l "^kind: Secret$" -- gitops/` on `dev` | `gitops/templates/cinder-csi-secret.example.yaml` | Pass |
| 5 | Access beyond the allow-list | From the worker pod, a TCP connection to `kubernetes.default.svc:443` | Blocked (TimeoutError after 5 s) | Pass |
| 6 | The website's private signing key outside the website | `kubectl get secret -A` filtered for `acp-signing` | Exists only in `student-platform` (1 key); not present in `agent-control-plane` | Pass |

## Supporting evidence: network policies in place

`agent-control-plane` (8 policies, 26 h old at capture): default deny for ingress and egress on all pods, DNS, website to API, API/worker/migration to PostgreSQL (ingress and egress), worker to Prometheus, worker to `llm-cpu`.

`inference` (3 policies): default deny for ingress, then `llm-cpu` reachable only from the Hermes worker and from Prometheus. Egress is intentionally open in `inference` so the model server can download its model file.

## Notes

- Check 5 shows the connection timing out (packets dropped), which is the behaviour of a network policy drop.
- Control test: a temporary pod in the `default` namespace (no network policies) ran `nc -zv -w 5 kubernetes.default.svc 443` and the result was `kubernetes.default.svc (<redacted-ip>:443) open`. The same address is reachable from an unfenced pod and blocked from the worker, so the block comes from the network policy and not from the API being unreachable.
- A request to `llm-cpu` without the key is refused by the server itself (401); the key is held in `llm-cpu-key` (namespace `inference`) and `acp-model` (namespace `agent-control-plane`), both sealed in Git.
- No Ingress, IngressRoute or RoleBinding exists in `agent-control-plane` or `inference`, and no new firewall rules were needed.
