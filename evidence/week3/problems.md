# Week 3: problems we hit

## Security (Wazuh + Suricata)

- **Suricata was running but logged nothing.**
  Its log folder belonged to root, but Suricata runs as its own user, so it couldn't write.
  Fixed the folder ownership in edge.yml.

- **The Wazuh indexer kept refusing connections.**
  The new Cinder disk was owned by root and the indexer runs as a normal user.
  Adding `fsGroup: 1000` to the StatefulSet sorted it out (same kind of problem as Suricata).

- **The indexer needed a kernel setting to start.**
  OpenSearch wants `vm.max_map_count=262144` on the workers. The default is 65530.
  Added it to bootstrap.yml.

- **The Wazuh app wasn't deploying at all.**
  Its Argo app said `targetRevision: HEAD`, which means `main`, and main didn't have the files.
  Changed it to `dev` like all our other apps.

- **The indexer answered 503 "Security not initialized".**
  Nobody had loaded its users yet. We ran `securityadmin` once with our own passwords,
  and deleted the six demo users that come with default passwords.
  This is a manual step for now. It should become a Job before the rebuild.

- **A "cert" mount was actually mounting the password secret.**
  It did nothing useful (and in 4.14 it would have hidden the real certs), so we removed it.

- **The dashboard couldn't find the indexer.**
  It was looking for `wazuh.indexer`, which is the Docker name, not ours.
  We gave it its own settings file (a ConfigMap) pointing at our indexer Service.

- **The dashboard gave 502 in the browser.**
  The dashboard only speaks HTTPS, but Traefik was talking plain HTTP to it.
  Fixed with a Traefik annotation and a ServersTransport.

- **Version mismatch.**
  The 4.x repo gave us the newest Wazuh manager (4.14.9), but the cluster images were 4.7.0,
  and the dashboard refuses to talk to a different API version.
  Upgraded the images to 4.14.9 and pinned the version in Ansible so it can't drift again.

- **The dashboard said "application not found".**
  Wazuh 4.9+ moved the home page from `/app/wazuh` to `/app/wz-home`. Updated the setting.

- **The 4.14 indexer keeps its files somewhere else.**
  Certs and security files moved under `/usr/share/wazuh-indexer/config/`.
  Our old commands pointed at the 4.7 paths and failed until we found the new ones.

- **The manager API still had its default passwords** (`wazuh` / `wazuh`).
  Changed both through the API. Old ones now give 401.

- **Filebeat's Ansible password lookup failed.**
  A regex didn't work on our Ansible version, so we read the secret file as YAML instead.

## Networking

- **HAProxy kept losing its Week 3 ports.**
  `api-lb.yml` rewrites the whole config, so running it from an older branch wiped 8404 and 9200.
  Lesson: only run it from an up-to-date dev.

- **The indexer path needed a NodePort too.**
  Same as the web traffic: hostPorts don't work with our Cilium setup.
  Traefik listens for the indexer on NodePort 30920 and HAProxy points at it.

- **The nodes ignored the new DNS server, even after rebooting.**
  cloud-init had told NetworkManager `dns = none` on first boot.
  Removed that line in bootstrap.yml, then rebooted the nodes one at a time.

- **Pods resolving our private names.**
  Added a CoreDNS rule that sends `*.inference-fabric.scc26.internal` straight to Pi-hole.

## Database / platform

- **PostgreSQL crash-looped (200+ restarts).**
  A brand-new disk has a `lost+found` folder, and PostgreSQL wants an empty folder.
  Pointing `PGDATA` at a subfolder fixed it.

- **The platform image build failed in GitHub Actions.**
  The test command was `node --test tests/`, which Node 22 reads as a single file.
  Changed it to `node --test`.

## Team / process

- **Two teammates lost their WireGuard tunnels** while adding the DNS line
  (probably the Delete key or the remove button). Their private keys went with them,
  so they got new keys and we updated the VPN server.
  Everyone should now keep an exported backup of their tunnel.

- **Committed on dev by accident** once, then pushed an empty feature branch.
  Lesson: check the first line of `git status` before committing.

## Known issues (not fixed yet)

- Argo shows the apps with a website (Grafana, platform, Wazuh) as "Progressing" forever.
  Their Ingresses never get an address, because Traefik sits behind HAProxy on NodePorts.
  Everything works; it's only the label. Fix is ready on `fix/traefik-ingress-address`.
- Filebeat doesn't verify the indexer's certificate yet (still encrypted, just not checked).
- We're still using the images' demo certificates instead of our own.
