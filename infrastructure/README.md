# Student POC infrastructure

This directory contains the **student-sized derivative** of the larger reference platform. Students should be able to deploy the common five-node environment without cloning or editing the full `infra-hpc-qc-k8s` repository.

Ownership:

```text
infrastructure/terraform → OpenStack desired state
infrastructure/ansible   → host configuration/bootstrap
```

The common POC intentionally omits the reference platform's Slurm fabric, dedicated NFS research storage, three-control-plane HA, dedicated Jupyter/agent worker pools and out-of-band Hermes VM. Those may be introduced only when a project has a justified need.

Private environment inputs/inventories belong outside public Git or in an instructor-approved encrypted/private mechanism. Commit examples/templates, not credentials.
