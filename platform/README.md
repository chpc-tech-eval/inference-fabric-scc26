# Student Project Platform

The Student Project Platform is the deliberately small web application used by all SCC26 student teams in Weeks 3–4. It replaces the need to clone or understand the full production `quantum-platform` repository.

## Goals

Teach, with the least unnecessary code:

- an Astro-based user-facing frontend;
- a small authenticated backend/API;
- PostgreSQL-backed persistent application state;
- container images built by GitHub Actions and published to GHCR;
- deployment through this repository's GitOps path;
- health/readiness probes and Prometheus-friendly telemetry;
- a server-side Agent Control Plane client added in Week 4.

## Non-goals

Do not reproduce production research-programme management, PI workflows, SSH/WireGuard registration, JupyterHub integration, full MFA/account administration or the wider Quantum Platform data model.

## Minimal Week-3 product

```text
User
 ├── username/email
 └── display name

Team
 ├── name
 └── project slug
```

A team landing/dashboard page should prove authentication and persistence. Keep the UI polished but small.

## Week-4 extension

Add a server-side ACP client and a simple Agent Control Plane panel. The browser talks to the Student Platform; the Student Platform authenticates/authorises and talks privately to ACP.

Never place ACP signing keys, model credentials or database passwords in frontend JavaScript/localStorage/URLs.

## Suggested source layout

```text
platform/
├── frontend/        # Astro
├── api/             # small backend/auth/API
├── tests/
└── README.md
```

Exact starter implementation may evolve before the programme baseline is frozen. Preserve the contract even if framework details are adjusted.
