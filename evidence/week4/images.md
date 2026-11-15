# Week 4 images and model (pinned)

Captured: 2026-11-14T16:48:54Z

Digests below are what the cluster is actually running (`kubectl get pods ... imageID`), cross-checked against the manifests in `gitops/resources/`.

## Agent Control Plane

| Component | Image | Digest | Pinned in manifest? |
| --- | --- | --- | --- |
| ACP API | `ghcr.io/nyameko/agent-control-plane` | `sha256:750b0ceb03fc3d09ef71063b5424716f14944df7be082485689dba6f2ff68f1c` | yes (digest) |
| ACP migration job | same image as the API | `sha256:750b0ceb03fc3d09ef71063b5424716f14944df7be082485689dba6f2ff68f1c` | yes (digest) |
| Hermes worker | `ghcr.io/nyameko/agent-control-plane-hermes` | `sha256:6ec37a755e57ef868a2fcce6052535588d14742bc85df75ab973dae811f1bdda` | yes (digest) |
| ACP PostgreSQL | `postgres:15-alpine` | `sha256:aae6554de426ae1990f1a939ff183a0299146cf7142a6f4c379c3357af9cc2d8` | **no** (floating tag) |

Approval: TODO (record who at the instructor's end confirmed these two digests, and when).

Version	Checksum
1	f12108f32e6e525e630ea328a93ef7a1c0a370a3ac44bb0147c7f66e0af0ab57
2	18186ac6c76efaa0d9b0805ab22327a4350b6e58067a1953309e77830ba6fb4d
3	6b5f00726a84126a9119cc1dfbc9a63ec6728ca1e2a8856d4e63283223685d76
4	b4a214001f04aea3ded0a42150c982b743180d7d461bbb2f5b1a3b49ca90f1c5
5	5c07e6cba400c470deb586369ea80aabb7ad0f3628e49a5d456eab1c6d211bf8
6	51dedadcf2e9aab94d111a7b6b7f25793bdb994e0a8c5a2afae13cc00d4a0375
7	b0c92547bcc514d6a96bddb8e97a203bff7269a7e3499b2ce41527a74876808d
8	90058ee5dc0fcf0be855be4be56721ca94be0eb6aeefbb938ba3b5a3c8cdef6e

Migration job acp-db-migration: Complete (1/1, 8 s), run 5 days 21 hours before capture; its log is empty (nothing printed on success). API /ready returned {"status":"ready"} on 2026-11-14.
## CPU model server

| Item | Value |
| --- | --- |
| llama.cpp server image | `ghcr.io/ggml-org/llama.cpp@sha256:e3032ea0712da96dec820c770626385de4322dd06619fb5829256a504bbc9375` (pinned) |
| Download init container | `curlimages/curl:8.10.1` (version tag, not a digest) |
| Model | Qwen2.5-1.5B-Instruct, Q4_K_M |
| Model file | `qwen2.5-1.5b-instruct-q4_k_m.gguf` |
| Model file sha256 | `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e` (`sha256sum` of `/models/qwen2.5-1.5b-instruct-q4_k_m.gguf` in the running `llama-server` container) |
| Server alias / model ID used by the ACP | `qwen2.5-1.5b-instruct` |
| Base URL (not secret) | `http://llm-cpu.inference.svc.cluster.local:8080/v1` |

## Student Platform

| Item | Value |
| --- | --- |
| Image | `ghcr.io/chpc-tech-eval/inference-fabric-scc26/student-platform` |
| Tag in manifest | `sha-99b889b5cb1b6eb5e4808bbe0f50238b7e3d031e` |
| Running digest | `sha256:f69d7ec54ac96bb16ebf25b63ce4492aa77f8ede7d41c11914f2d43b3b8f02ed` |
| Cross-check | TODO (confirm this digest against the Actions run summary for that commit) |
| PostgreSQL | `postgres:15-alpine`, running `sha256:54e0dd8e8cddcdbb9156c2486eed5a43eccb7214d7c6828097d41ce049fb3984` |

The package is private; the cluster pulls it with a pull secret.

## Findings

- `postgres:15-alpine` is an unpinned tag in two manifests, and the two databases are running **different** digests of it (`aae6554d...` for the ACP, `54e0dd8e...` for the platform), because they pulled at different times. Recommend pinning both by digest.
- The download init container uses a version tag rather than a digest.
- The platform image changed since Week 3 (the Week 3 digest was `d2bd815c...`); this is the Week 4 deployment.
