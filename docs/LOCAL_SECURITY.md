# Local security controls and container verification

These application controls were deployed to the existing HF Space on 2026-10-29 at revision `77216ec63ad9a93d782d8bc9af80f5000eced9cc`. Hosting-level Docker resource flags remain distinct from application controls.

## URL downloads

- Only HTTPS on port 443, maximum 2048 characters. No credentials, fragments,
  whitespace/control characters, backslashes or IPv6 zone identifiers.
- DNS is resolved once. Every answer must be a global unicast address;
  private, loopback, link-local, multicast, reserved, mapped and transition
  addresses are rejected, including mixed public/private answers.
- The connection is pinned to a validated IP. The original hostname is used
  for TLS certificate validation, SNI and the HTTP Host header.
- Environment proxies, retries and redirects are disabled. Redirect links
  must be replaced with the final public HTTPS image URL.
- Only HTTP 200 image responses with identity content encoding are accepted.
  Declared length and streamed bytes are bounded at 8 MiB.
- Each URL download runs in a small child process without importing the model.
  The parent kills and reaps it after 12 seconds, including DNS resolution,
  TLS, headers and body transfer. Connect/read timeouts are also 3 seconds.
- The three exact `/ui/covers/{HollowKnight,Stardew,moncage}.jpg` values read
  bundled files directly. No arbitrary path or same-origin/Host-header bypass.
- The browser does not load external URL previews, so it cannot bypass the
  server's destination/redirect checks. Uploads and bundled covers retain previews.

## Resource budgets (one application worker)

| Resource | Limit |
| --- | --- |
| Active prediction requests, including upload/download | 2; excess gets 503 + Retry-After |
| Simultaneous model inference | 1; excess gets 503 + Retry-After |
| Torch CPU threads | 2 |
| JSON request body | 4096 bytes |
| Multipart body, counted before parsing | 8 MiB + 64 KiB |
| Upload body absolute deadline | 15 seconds; timeout gets 408 |
| Multipart items | 1 file, 0 text fields |
| Encoded image | 8 MiB |
| Decoded image | 12 million pixels, longest side 8192 |
| Image formats | Single-frame JPEG, PNG, WebP |
| Uvicorn connection/task limit | 16; backlog 32; keep-alive 5 seconds |

Oversized inputs return 413, unsupported images/encoding return 415, blocked
URLs return 400, network failure returns 502 and download timeout returns 504.
Health/static routes do not consume prediction slots. Inference has bounded
input and concurrency, but is not forcibly interrupted by a wall-clock timer.
These limits are per process: keep one Uvicorn worker. Deployment-level rate
limits, ingress limits and infrastructure isolation still need review on the
chosen host; these controls are not a general DDoS protection service.

## Docker setup and verification

The Dockerfile has separate `verification` and final `production` targets.
Production uses UID 1000, explicit COPY entries, model hash verification at
build time, a health check and one worker. The build context is allowlisted.
Tests and Git metadata are not copied into production.

When Docker Desktop's Linux engine is available, run from PowerShell:

```powershell
./scripts/verify_docker.ps1
```

The script builds the verification image, runs the real-model/security tests,
builds production and starts a temporary local-only container. It verifies health,
real inference, non-root identity and absent Git/test files, then removes only
its uniquely named test container. Test images remain available locally.

Runtime checks use a read-only filesystem, a 64 MiB `/tmp` tmpfs, 1 GiB memory,
2 CPUs, 64 PIDs, dropped capabilities and no-new-privileges. These settings passed the local Linux verification and production inference checks; production traffic still needs deployment-specific load testing.

**Current evidence:** 74 Windows tests passed; a real public HTTPS cover
download returned the expected `platform` prediction. JavaScript syntax,
Python compilation, dependency consistency and PowerShell script parsing passed.
After user authorization, WSL 2.7.14.0 and Docker Desktop 4.97.0 were installed.
The verification and production images built successfully. **All 74 tests passed
in Linux Python 3.11 (4.69 seconds)** under the stated container resource limits.
Production health, real model inference, UID 1000 and exclusion of Git/tests
were verified. Temporary test containers were removed; local images remain.
The complete output is in `artifacts/docker-verification.log`.

References used for implementation review:

- [Starlette request parsing](https://starlette.dev/requests/): multipart
  field/file counts; file bytes also need an independent request-body bound.
- [Docker Desktop Windows prerequisites](https://docs.docker.com/desktop/setup/install/windows-install/).

Hosted validation: 11 smoke checks and a separate public HTTPS image download passed; see `artifacts/deployment-check.json` and `artifacts/hf-public-url-check.json`.
