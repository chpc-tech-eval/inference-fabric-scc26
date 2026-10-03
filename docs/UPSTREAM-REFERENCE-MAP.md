# Upstream Reference Map

The student repositories are deliberately smaller than the production/research repositories. Use upstream material to understand design decisions; do not blindly copy the full topology.

## `nyameko/infra-hpc-qc-k8s`

Current reference baseline reviewed for this pack: `c493703da5fca804463db444e871c6b64b3141b9`.

Useful reading by week:

| Student week | Upstream reference |
| --- | --- |
| 1 | `docs/tutorials/02-networking-and-security.md`, `03-deployment-terraform-ansible.md`, `terraform/README.md`, `ansible/README.md` |
| 2 | `04-kubernetes-platform-revised.md`, `04a-cinder-csi-and-the-ansible-to-gitops-boundary.md`, `04b-argocd-gitops-secrets-ksops.md`, `argocd/README.md` |
| 3 | `wazuh-suricata-deployment.md`, `wazuh-suricata-operational-drills.md`, Prometheus/Grafana GitOps resources |
| 4 | `10-agent-control-plane-phase1.md` plus ACP GitOps resources |

Important: the upstream repo documents a larger reference platform. Student teams use one control plane, two workers and no Slurm/NFS/Jupyter baseline unless their later project explicitly introduces it.

## `nyameko/quantum-workflows`

Current reference baseline reviewed for this pack: `db43399cc4dcb8ed2c02b5dd9241d106e3d6715d`.

The student projects borrow its engineering discipline even when they are not quantum projects:

- immutable runner/container images;
- credential-free CI/smoke tests where possible;
- explicit control-plane vs compute-plane separation;
- structured result directories/manifests;
- Git SHA + software versions + execution placement + parameters + timings;
- credentials never baked into images/results;
- failed runs retained as evidence;
- resource-intensive stages allocate/release resources only when needed.

This is especially relevant to Inference Fabric and Cloud HPL, but every team uses the same provenance contract.
