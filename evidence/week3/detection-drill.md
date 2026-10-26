# Week 3 detection drill

## What we did
Tried to log into `k8s-cp-01` three times as a user that doesn't exist (`nosuchuser`), over the VPN.
Harmless: each attempt was rejected.

**When:** 2026-10-24, 07:55:03–07:55:04 UTC

## What we saw
- **Suricata (network):** three SSH connections to `10.151.0.11:22` (`drill-suricata.txt`).
- **Wazuh (host):** three alerts, Rule 5710 "login with a non-existent user", from `k8s-cp-01` (`drill-wazuh.txt`).

The source ports match in both, so they recorded the same three connections.
Wazuh's headers show local time (UTC+2); the log lines are UTC.

**Platform health:** all nodes Ready, all pods Running.

## Problem we hit
On the first try, Suricata logged nothing: its log folder was owned by root. We fixed the ownership
in `edge.yml` and repeated the drill.