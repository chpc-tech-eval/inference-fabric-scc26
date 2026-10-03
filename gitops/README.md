# GitOps in the team repository

A separate student GitOps repository is **not required**. Argo CD may watch this repository directly.

Suggested structure:

```text
gitops/
├── bootstrap/
│   └── root-application.yaml
├── applications/
│   ├── monitoring.yaml
│   ├── wazuh.yaml
│   ├── student-platform.yaml
│   └── agent-control-plane.yaml
└── resources/
    ├── monitoring/
    ├── wazuh/
    ├── student-platform/
    └── agent-control-plane/
```

Bootstrap is performed from `k8s-cp-01`. Steady-state changes are made through Git/PRs and reconciled by Argo CD.

Rules:

- no secrets in plaintext;
- pin assessed images/tags/digests;
- do not use `kubectl edit` as a permanent deployment method;
- Argo health is evidence, not the entire acceptance test;
- document dependencies/order where one application requires another.
