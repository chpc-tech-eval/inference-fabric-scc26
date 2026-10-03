# Experiment and Run Provenance Contract

This student programme adopts a core principle from `quantum-workflows`:

> **Provenance is part of the result.**

A benchmark, security exercise, agent run or performance figure is not reproducible if you cannot identify the exact source, software environment, parameters, placement and timestamps that produced it.

## Minimum manifest

Use JSON or YAML. Keep it machine-readable.

```yaml
schema_version: '1.0'
run_id: <uuid-or-unique-id>
project: <team-slug>
experiment: <human-readable-name>
status: running|completed|failed
started_at: <UTC RFC3339>
finished_at: <UTC RFC3339>
source:
  repository: <url>
  commit: <full-git-sha>
  dirty: false
software:
  images:
    - name: <logical-name>
      ref: <immutable-tag-or-digest>
execution:
  location: sebowa-kubernetes|a100|h200|other-approved-target
  host_class: <logical-class>
  namespace: <if applicable>
  requested_resources: {}
parameters: {}
metrics: {}
artifacts:
  - path: <relative path or durable result reference>
    sha256: <digest where retained>
notes: <short limitations/conditions>
```

## What never goes in a manifest

Never dump `os.environ` or the full process environment. Never record:

- API keys/tokens;
- SSH/WireGuard private keys;
- OpenStack credentials;
- kubeconfigs;
- Discord bot tokens;
- raw confidential research/user data;
- database passwords.

Use an **allowlist** of safe metadata.

## Immutable software references

During active integration, a branch tag can move. For accepted experimental evidence, prefer an immutable image digest or immutable `sha-<commit>` tag and record the Git commit that built it.

## Results versus observability

Prometheus/Grafana is live operational evidence. Your run manifest/result directory is the durable experimental record. Do not encode unique run IDs as unbounded Prometheus labels; keep them in logs/manifests and use bounded labels for dashboards.

## Failure is a valid result

Record failed runs with:

- failure type;
- sanitized message;
- timestamps;
- already-produced evidence/artifacts;
- exact configuration used.

Deleting failed runs destroys useful engineering evidence.
