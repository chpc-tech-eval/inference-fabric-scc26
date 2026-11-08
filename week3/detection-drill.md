# Week 3 detection drill

A fresh, harmless event was generated and traced through the host-level (Wazuh), network-level (Suricata) and platform-health (Grafana) views. Private IP addresses are replaced with `<redacted-ip>` because the repository is public.

## What we did

From `edge-01`, three SSH login attempts were made to `k8s-cp-01` as a username that does not exist (`nosuchuser`). Each was rejected. This is the instructor-approved style of action: harmless, no real account involved, and only three attempts.

```bash
date -u +"START %Y-%m-%dT%H:%M:%SZ"
for i in 1 2 3; do
  ssh -o BatchMode=yes -o ConnectTimeout=5 nosuchuser@k8s-cp-01
done
date -u +"END   %Y-%m-%dT%H:%M:%SZ"
```

## When

| | Time (UTC) |
| --- | --- |
| START | 2026-10-31T11:13:21Z |
| END | 2026-10-31T11:13:22Z |

All three attempts returned `Permission denied (publickey,gssapi-keyex,gssapi-with-mic)`.

## What Suricata saw (network)

Suricata on `edge-01` (IDS mode, EVE JSON) logged three SSH sessions from `edge-01` to `k8s-cp-01` port 22. Suricata timestamps are in local time (+0200); converted to UTC they fall inside the drill window.

| Source port | Suricata timestamp (+0200) | UTC | Client |
| --- | --- | --- | --- |
| 46268 | 13:13:21.928 | 11:13:21.928Z | OpenSSH_8.7 |
| 46274 | 13:13:22.416 | 11:13:22.416Z | OpenSSH_8.7 |
| 46288 | 13:13:22.533 | 11:13:22.533Z | OpenSSH_8.7 |

These are protocol events (`event_type: ssh`), not IDS alerts: this traffic is expected and not malicious, so Suricata recorded it without alerting. Raw records: `drill-suricata.txt`.

## What Wazuh recorded (host)

`k8s-cp-01`'s sshd logged each attempt as an invalid user, and the Wazuh agent forwarded it to the manager on `edge-01`. The source ports match Suricata's, so both tools saw the same three connections.

| Source port | Log time (UTC) | Message |
| --- | --- | --- |
| 46268 | 11:13:22 | Invalid user nosuchuser from `<redacted-ip>` |
| 46274 | 11:13:22 | Invalid user nosuchuser from `<redacted-ip>` |
| 46288 | 11:13:22 | Invalid user nosuchuser from `<redacted-ip>` |

Raw records: `drill-wazuh.txt`, `drill-wazuh-alert.txt`.

**Wazuh rule that fired:** rule 5710, level 5, "sshd: Attempt to login using a non-existent user" (groups include `authentication_failed` and `invalid_login`). Three alerts were raised, one per attempt:

| Alert ID | Source port | Alert time (manager local, +0200) |
| --- | --- | --- |
| 1793445202.3573579 | 46268 | 13:13:22 |
| 1793445204.3574129 | 46274 | 13:13:24 |
| 1793445204.3574679 | 46288 | 13:13:24 |

Each alert embeds the original sshd log line from `k8s-cp-01` (timestamped 11:13:22Z), so the underlying events fall inside the drill window; the alerts themselves were stamped up to two seconds later, which is Wazuh's processing delay.
**Wazuh dashboard:** evidence of the alerts on wazuh is in wazuh-dashboard-home.png

## Platform health at that moment (Grafana)

nodes Ready, platform pod Running, no restarts, no targets down apart.

Raw Records:  `grafana-dashboard-drill-1.png`,  `grafana-dashboard-drill-2.png`, `grafana-dashboard-drill-3.png`

## How someone else can reconstruct it

1. Run the commands above from `edge-01` and record the START and END times.
2. Wait 2-3 minutes so Suricata writes its records.
3. On `edge-01`, Suricata events:
   `sudo grep '"event_type":"ssh"' /var/log/suricata/eve.json | grep '<date-and-hour-of-drill>'`
4. On `edge-01`, Wazuh alerts:
   `sudo grep -B6 -i nosuchuser /var/ossec/logs/alerts/alerts.log`
5. In Grafana, open Platform Overview with the time range set to the drill window (UTC).

Source ports are the key to matching a Suricata event to its Wazuh record.

## Notes

- Only a fresh event counts; the earlier 24 Oct files were replaced by this run.
- Suricata uses local time (+0200) and Wazuh logs use UTC. Convert before comparing.
- Earlier SSH sessions by team members passing through the edge (different client version, OpenSSH 9.6) were filtered out of the evidence files.
