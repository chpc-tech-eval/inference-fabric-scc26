# Week 7 — Consolidation, Handover & Release

Week 7 turns six weeks of work into a clean engineering handover.

## 1. Fix what the rebuild exposed

Review Week-6 notes and convert undocumented manual steps into:

- automation;
- documentation;
- explicit prerequisite;
- or a tracked known limitation.

Do not leave “we just remembered to run this command” as part of the final platform.

## 2. Repository hygiene

```bash
# RUN ON: WORKSTATION
git switch dev
git pull --ff-only
git status
git grep -nE '(password|token|secret|BEGIN .*PRIVATE KEY)' -- . ':!paper/*' || true
```

Use an appropriate secret scanner if supplied by the instructor. Manual grep is not a complete secret audit.

Remove stale binaries, generated results that do not belong in Git, abandoned manifests and dead documentation links.

## 3. Close/triage issues and PRs

Every open issue should be:

- completed;
- explicitly deferred with rationale;
- or converted into an upstream contribution proposal.

Do not merge experimental code merely to make the issue list shorter.

## 4. Upstream boundary review

Ask where each reusable improvement belongs:

```text
OpenStack/Ansible/Kubernetes deployment improvement → infra-hpc-qc-k8s candidate
scientific runner/result-contract idea             → quantum-workflows candidate
ACP policy/runtime capability                       → agent-control-plane candidate
student-only experiment/tutorial                    → this repository
```

Prepare small focused upstream PRs/issues rather than copying your entire student tree.

## 5. Release `dev` → `main`

`main` and `dev` stay protected. Final release is a reviewed PR from `dev` to `main` after CI/documentation checks pass.

Create a release note containing:

- final Git SHA;
- architecture summary;
- accepted image digests;
- accepted experiment/run IDs;
- known limitations;
- how to rebuild;
- how to clean up resources.

## 6. Resource cleanup

If instructed to remove the environment, destroy it through the same declarative path used to build it. Verify OpenStack resources/volumes/floating IPs afterward so quotas are not leaked.

## Final handover test

A person outside your team should be able to answer from the repository alone:

1. What problem did you solve?
2. What infrastructure exists and why?
3. How is it rebuilt?
4. Where are secrets supposed to live?
5. What exact software/result versions support the paper claims?
6. What failed or remains incomplete?
7. Where would a future contributor start?
