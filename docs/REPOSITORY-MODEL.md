# One repository is enough

Your team works from **this repository**. You do not need a second Argo CD/GitOps repository for this six-week project.

The intended layout is:

```text
<team-repository>/
├── README.md
├── CONTRIBUTING.md
├── week1/ ... week4/
├── infrastructure/
│   ├── terraform/
│   └── ansible/
├── platform/
│   └── Student Project Platform source/configuration
├── gitops/
│   ├── bootstrap/
│   ├── applications/
│   └── resources/
├── project/
│   └── Week-5 team-specific work
├── paper/
├── poster/
└── .github/
    └── workflows/
```

Argo CD watches the `gitops/` path in this same repository. GitHub Actions can build project/Student Platform images and publish them to GHCR. This keeps the learning path visible in one place.

## You do not clone Quantum Platform

The production `nyameko/quantum-platform` repository is **reference architecture only** for this programme. It is larger than the student exercise and includes identity/programme/access functionality you do not need.

Instead, you deploy a deliberately small **Student Project Platform** from this repository:

```text
browser
   ↓
Student Project Platform
   ├── Astro frontend
   ├── small authenticated backend/API
   └── PostgreSQL
          ↓
      persistent Cinder PVC
```

By Week 4 it gains one bounded agent interface:

```text
Student Project Platform
        ↓ authenticated server-side request
Agent Control Plane
        ↓
PostgreSQL task/run history
        ↓
Hermes worker
        ↓
approved A100/H200 model endpoint
```

Students also do **not** need to clone `agent-control-plane` merely to operate it. Deploy the instructor-approved, immutable upstream ACP/Hermes images through your repository's GitOps configuration. Clone/fork ACP only if your project later makes a genuine source contribution.

The same principle applies to `infra-hpc-qc-k8s`: it remains the instructor/reference implementation. The student-sized Terraform, Ansible and GitOps material needed for this project belongs here, already distilled to the five-node POC.


# Git workflow and branch protection

This repository uses a small version of the same release discipline used by the larger platform projects.

```text
                  main
            protected / release
                   ▲
                   │ PR at release/consolidation
                   │
                  dev
       protected integration branch
                   ▲
        ┌──────────┼──────────┐
        │          │          │
   feature/*     fix/*      docs/*
```

## Branch roles

- `main` is the protected, demonstrable/released state. Students do **not** push directly to it.
- `dev` is the protected integration branch for the active project.
- normal work begins from `dev` on short-lived branches such as `feature/week2-cinder`, `fix/edge-dns` or `docs/week3-evidence`;
- pull requests normally target `dev`;
- during the final release/consolidation, the mentor/team opens a reviewed `dev → main` pull request.

If `dev` does not yet exist, the instructor/maintainer can create it from the prepared baseline before student work begins:

```bash
# RUN ON: WORKSTATION (maintainer only during initial setup)
git switch main
git pull --ff-only
git switch -c dev
git push -u origin dev
```

## Recommended GitHub protection / ruleset

Protect **both `main` and `dev`**. At minimum:

- require changes through pull requests;
- require at least one approving review (the instructor may require more for `main`);
- require conversation resolution before merge;
- require configured CI/status checks to pass once those workflows exist;
- block force pushes;
- block branch deletion;
- keep bypass permissions limited to maintainers/instructors;
- do not allow students to merge secrets, generated credentials, kubeconfigs or private environment files.

For `main`, use the stricter rule: normal student feature PRs should **not** target `main`; release only from a reviewed `dev` state.

## Student branch workflow

```bash
# RUN ON: WORKSTATION
git switch dev
git pull --ff-only
git switch -c feature/<short-description>

# work, test, commit
git add <files>
git diff --cached
git commit -m "<type>: <what changed and why>"
git push -u origin feature/<short-description>
```

Then open a GitHub pull request into `dev`, describe the evidence used to validate the change, and request review.

Good commits are small enough to understand and revert. Git history is part of your engineering evidence.
