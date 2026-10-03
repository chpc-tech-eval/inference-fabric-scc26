## What changed?

<!-- Briefly describe the change and why it is needed. -->

## Layer / owner

- [ ] OpenStack / Terraform
- [ ] Ansible / host configuration
- [ ] Kubernetes / Cilium / Cinder
- [ ] GitOps / Argo CD / ingress
- [ ] Observability / security
- [ ] Student Project Platform
- [ ] Agent Control Plane / Hermes
- [ ] Project-specific work
- [ ] Documentation / paper / poster

## Validation evidence

<!-- Commands/tests/results used. Redact secrets and unnecessary private topology. -->

## Risk / rollback

<!-- Ports, privileges, data/storage, secrets, public exposure, destructive changes? How can it be rolled back? -->

## Checklist

- [ ] I branched from `dev` and this PR targets `dev` (unless this is the reviewed release PR).
- [ ] No plaintext credentials, kubeconfigs, private keys or Terraform state are committed.
- [ ] Permanent Kubernetes desired-state changes are in Git rather than `kubectl edit`.
- [ ] CI/status checks pass where configured.
- [ ] Documentation/evidence was updated when behaviour changed.
