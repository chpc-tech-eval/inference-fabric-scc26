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

# Pull request evidence

Every meaningful PR should answer:

1. What problem/change does this PR address?
2. Which layer owns it?
3. How was it validated?
4. What evidence or commands prove the acceptance criterion?
5. Does it change secrets, ports, privileges, storage or public exposure?
6. How can it be rolled back?

Do not paste sensitive logs/credentials into PRs. Redact environment-specific information that is not required to review the engineering change.


## Week-by-week path

Follow `week1/` through `week7/` in order. Weeks 1–4 are acceptance-gated; do not skip a failed layer. Normal student PRs target protected `dev`; the final reviewed release is `dev` → `main`.
