# Provenance: run records

Every significant demo or experiment gets a small run record, so any result can be traced back
exactly to the code, images and place it ran. Week 5 benchmarks use the same format.

## Where records live

- `evidence/weekN/run-manifest.yaml` for the accepted deployment of each week
- one file per benchmark run from Week 5, named by `run_id`

## Format

| Field | Meaning |
| --- | --- |
| `schema_version` | format version, currently `'1.0'` |
| `run_id` | UTC timestamp, e.g. `20261027T101500Z` |
| `project` | `inference-fabric-scc26` |
| `started_at`, `finished_at` | UTC times of the run |
| `source.repository` | the Git repository URL |
| `source.commit` | full commit SHA that was deployed or run |
| `source.dirty` | `false` only if nothing uncommitted was used |
| `software.images.<name>` | container image digest (`sha256:...`), never a mutable tag |
| `execution.location` | where it ran, e.g. `sebowa-kubernetes` |

## Rules

1. Record the image digest, not `latest` or a branch tag. Tags can be re-pointed; digests cannot.
2. `dirty: true` means the result is not reproducible. Commit first, then run.
3. Times are UTC, ISO 8601.
4. No secrets, tokens or private IPs in a record.
5. Someone else must be able to rerun from the record alone.

## How to fill in the fields

source.commit:

    git rev-parse HEAD

source.dirty (empty output means false):

    git status --porcelain

image reference in the Deployment:

    kubectl -n student-platform get deploy student-platform -o jsonpath='{.spec.template.spec.containers[0].image}'

digest of the image actually running:

    kubectl -n student-platform get pod -l app=student-platform -o jsonpath='{.items[0].status.containerStatuses[0].imageID}'
