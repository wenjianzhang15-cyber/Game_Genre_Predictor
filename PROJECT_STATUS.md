# Project status — 2026-10-29

## Current workspace

- Local Windows checkout in `game genre predictor`, branch `chore/local-handoff`.
- Verified fork and origin: https://github.com/wenjianzhang15-cyber/Game_Genre_Predictor
- Upstream: https://github.com/Cjmcd23/CSSE_Local_Demo (push URL disabled).
- Original history retained from `fdc02654782ade7e428a9417f5aeb8badc53f534`.
- Cloud commits were not transferred as Git objects. Their source changes were reconstructed from recorded patches and the pinned HF snapshot. The restored backend, frontend and requirements hashes matched the prior cloud records before the new UI changes.
- Removed 31,224 tracked environment files and the stale model pointer in a local cleanup commit. Historical files remain in Git history.
- GitHub publication authorized and completed: `main` and `chore/local-handoff` contain the verified release. HF upload is awaiting account login; the previous public HF revision is still running.

## Completed locally

- Restored backend fixes, restricted static routes, tests, setup documentation and verified model downloader.
- Created independent Python 3.12.14 Windows virtual environment; installed Torch 2.3.0+cpu, torchvision 0.18.0+cpu and NumPy 1.26.4.
- Downloaded model from pinned HF revision `085eedcd43b9076a80c1e88e3e2e085a76950aec`; verified 94,387,665 bytes and SHA-256 `5d4b774fa6514e1aba92ede0ad2fba43386141fdbfebfa54b299ef8229e4f3f0`.
- Preserved deployed class order, preprocessing and model weights.
- Added three clickable cover examples, Top-3 score bars, visible keyboard focus, reduced-motion support, mobile CSS and object-URL preview cleanup.
- Retained team attribution and clarified uncalibrated model scores and temporary upload processing.

## Verification

- Windows: **29 tests passed**, one upstream Starlette/AnyIO deprecation warning. Actual local run: `artifacts/windows-regression.xml`.
- Browser clicks: Hollow Knight → platform, Stardew Valley → indie, Moncage → puzzle; each displayed three score rows.
- Browser upload flow passed with HollowKnight.jpg; displayed platform and three scores. No browser console errors observed. At 390px viewport, no horizontal overflow; restored default viewport afterward. Screenshot: `artifacts/local-preview.jpg`.
- Local preview binds only to `127.0.0.1:7860`; logs and PID are under ignored `artifacts/`.
- Original cloud reported 29 passing tests separately; these are not deployment results.

## Remaining before publication

1. URL restrictions and resource budgets are implemented; review hosting-specific ingress/rate limits before publication.
2. Local Docker build/run is verified. Hosted ingress settings and hosted cold start remain to be checked before publication.
3. Complete full keyboard interaction review and confirm final team names and publication wording.
4. User explicitly authorized GitHub push and HF deployment. GitHub push completed; finish HF login, source upload and post-deployment smoke checks.

## Links

- Local preview: http://127.0.0.1:7860/ui/index.html
- Existing public app: https://legend0908-game-genre-demo.hf.space/ui/index.html
- HF Space: https://huggingface.co/spaces/Legend0908/game-genre-demo

## Local hardening update

- HTTPS/public-IP-only URL retrieval, DNS pinning with TLS hostname checks, no redirects/proxies/retries, and a 12-second kill/reap deadline.
- Exact bundled-cover paths preserve examples without loopback requests. External URLs are not fetched again by the browser for preview.
- Pre-parser body bytes/deadline and admission control; single-file multipart; pixel/dimension/frame restrictions; one concurrent inference and two CPU threads.
- **74 tests passed** on Windows, including actual child-process deadline/reaping, private/mixed DNS rejection, redirect rejection, streaming size limits, upload timeout and admission/inference slot behavior. Evidence: `artifacts/security-regression.xml`.
- Actual public HTTPS download from the fork's raw HollowKnight cover succeeded and predicted platform.
- Dockerfile now uses explicit files, UID 1000, build-time model verification, healthcheck and test/production targets. Verification script prepared and PowerShell syntax checked, but no actual Docker build/run has occurred.
- At the hardening checkpoint Docker/WSL were absent. Installation was subsequently authorized and completed; see the container verification update below.
- No remote pushes or deployment updates.

## Docker verification completed locally

- User explicitly authorized Docker and WSL installation.
- Installed Microsoft WSL 2.7.14.0 (kernel 6.18.33.2-2) and Docker Desktop 4.97.0 (244584), per-user installation. Engine 29.9.2 reports linux/amd64. No reboot was needed.
- Fixed PowerShell argument splitting by quoting the comma-separated tmpfs mount options.
- `scripts/verify_docker.ps1` completed successfully. Linux Python 3.11: **74 passed, 1 upstream deprecation warning in 4.69 seconds**.
- Production image `game-genre-predictor:local` built successfully; image ID `sha256:18da8ead7fdbddbcda903d338d9babeff72e3e1885a5ee0524d8ae4cca3d7aed`.
- Verified real inference (Hollow Knight -> platform), HTTP health, UID 1000, and absence of `/app/.git` and `/app/tests`.
- Test and production containers ran with read-only filesystem, 64 MiB tmpfs, 1 GiB memory, 2 CPUs, 64 PIDs, all capabilities dropped and no-new-privileges. Production test port bound only to 127.0.0.1.
- Temporary verification containers were removed. Built images and Docker Desktop remain installed locally.
- Complete build/test output: `artifacts/docker-verification.log`.
- No remote pushes, HF deployment changes or public ports created.
